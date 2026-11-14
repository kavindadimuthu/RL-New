"""Prepare/run an isolated comparison. No training starts without --run.

python -m transit_rl.experiment.evaluation_comparison
python -m transit_rl.experiment.evaluation_comparison --run
"""
from __future__ import annotations

import argparse
from concurrent.futures import ProcessPoolExecutor
import ctypes
from datetime import datetime, timezone
from dataclasses import asdict, replace
import hashlib
import json
import multiprocessing
import os
from pathlib import Path
import platform
import random
import shutil
import statistics
import subprocess
import sys
import time

# Set before NumPy/SciPy import, including in Windows-spawned workers.
for _name in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS",
              "NUMEXPR_NUM_THREADS", "VECLIB_MAXIMUM_THREADS"):
    os.environ[_name] = "1"

import numpy as np
import scipy

from ..agent.q_learning_agent import QLearningAgent
from ..config import ExperimentConfig
from ..data.network import load_network_from_csv
from ..data.od_loader import load_od_matrices
from ..environment.transit_environment import TransitEnvironment
from .trainer import run_episode, summarise_day

MODES = {"A_dense": "dense", "B_committed": "committed", "C_hour_end": "terminal"}
ROOT = Path(__file__).resolve().parents[2]


def utc_now():
    return datetime.now(timezone.utc).isoformat()


class CountedEnvironment(TransitEnvironment):
    def __init__(self, *args, **kwargs):
        self.evaluation_requests = 0
        super().__init__(*args, **kwargs)

    def evaluate_plan(self, plan):
        self.evaluation_requests += 1
        return super().evaluate_plan(plan)


def make_config(mode, **overrides):
    cfg = replace(ExperimentConfig(), reward_mode=MODES[mode],
                  evaluate_after_each_change=False,
                  assign_after_route_construction_steps=False,
                  make_plots=False, copy_best_qtable=False, **overrides)
    cfg.validate()
    return cfg


def memory_mb():
    """Working set and free physical RAM on Windows; unavailable elsewhere."""
    if os.name != "nt":
        return None, None

    class Counters(ctypes.Structure):
        _fields_ = [("cb", ctypes.c_ulong), ("faults", ctypes.c_ulong)] + [
            (n, ctypes.c_size_t) for n in ("peak", "working", "peak_paged", "paged",
                                         "peak_nonpaged", "nonpaged", "pagefile", "peak_pagefile")]

    class Status(ctypes.Structure):
        _fields_ = [("length", ctypes.c_ulong), ("load", ctypes.c_ulong)] + [
            (n, ctypes.c_ulonglong) for n in ("total", "free", "total_page", "free_page",
                                            "total_virtual", "free_virtual", "extended")]

    kernel = ctypes.WinDLL("kernel32")
    kernel.GetCurrentProcess.restype = ctypes.c_void_p
    fn = ctypes.WinDLL("psapi").GetProcessMemoryInfo
    fn.argtypes = [ctypes.c_void_p, ctypes.POINTER(Counters), ctypes.c_ulong]
    counters, status = Counters(), Status()
    counters.cb, status.length = ctypes.sizeof(counters), ctypes.sizeof(status)
    if not fn(kernel.GetCurrentProcess(), ctypes.byref(counters), counters.cb):
        raise ctypes.WinError()
    if not kernel.GlobalMemoryStatusEx(ctypes.byref(status)):
        raise ctypes.WinError()
    return counters.working / 2**20, status.free / 2**20


def epsilon_at_fraction(cfg, fraction):
    fraction = min(1.0, max(0.0, fraction / cfg.epsilon_decay_fraction))
    return cfg.initial_epsilon * (cfg.min_epsilon / cfg.initial_epsilon) ** fraction


def evaluate(agent, cfg, network, od, seeds):
    """Fresh environments and independent RNGs; learner/RNG/caches untouched."""
    results = []
    eval_cfg = replace(cfg, reward_mode="terminal", evaluate_after_each_change=False,
                       assign_after_route_construction_steps=False)
    for seed in seeds:
        env = CountedEnvironment(network, od, eval_cfg)
        observer = QLearningAgent(eval_cfg, seed)
        observer.q = agent.q  # read-only use: run_episode(train=False)
        reward, records, steps, unseen = run_episode(env, observer, train=False)
        results.append(dict(seed=seed, reward=reward, steps=steps,
                            unseen_fraction=unseen / steps, **summarise_day(records)))
    return results


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, default=str), encoding="utf-8")


def run_job(job):
    """Persist provenance and failure status even if a worker raises."""
    out = Path(job['output'])
    out.mkdir(parents=True, exist_ok=False)
    manifest = dict(study_id=job['study_id'], run_id=job['run_id'], stage=job['phase'],
                    treatment=job['mode'], training_seed=job['seed'],
                    evaluation_seeds=job['evaluation_seeds'], status='running',
                    started_at=utc_now(), timezone='UTC', code_commit=job['code_commit'],
                    working_tree_dirty=False, command=job['command'],
                    environment_reference='../../environment.json',
                    hardware_reference='../../machine.json', resolved_config='config.json',
                    large_artifacts=dict(q_table='not_saved', checkpoint='not_saved'),
                    artifact_reason='Compact metrics/evaluations retained; regeneration is a new run.')
    write_json(out/'manifest.json', manifest)
    try:
        result = _run_job_impl(job)
    except BaseException as error:
        manifest.update(status='failed', finished_at=utc_now(), error=repr(error))
        write_json(out/'manifest.json', manifest)
        raise
    manifest.update(status=result['stop_reason'], finished_at=utc_now(),
                    episodes_completed=result['episodes'], training_seconds=result['training_seconds'],
                    evaluation_seconds=result['evaluation_seconds'])
    write_json(out/'manifest.json', manifest)
    return result


def _run_job_impl(job):
    out = Path(job["output"])
    phase = job["phase"]
    base = ExperimentConfig()
    # Timing reproduces early default training. Learning uses a documented,
    # shorter schedule; every variant has exactly the same schedule per phase.
    cfg = make_config(job["mode"], num_episodes=job["episodes"],
                      epsilon_decay=base.resolved_epsilon_decay() if phase == "timing" else None)
    network = load_network_from_csv(cfg.links_path, cfg.num_stops, cfg.links_are_bidirectional,
                                    cfg.input_stop_id_base)
    od = load_od_matrices(cfg.od_dir, cfg.od_filename_pattern, cfg.num_hours,
                          cfg.num_stops, cfg.od_file_numbers())
    env = CountedEnvironment(network, od, cfg)
    agent = QLearningAgent(cfg, job["seed"])
    write_json(out / "config.json", asdict(cfg))
    learning = phase != "timing"
    limit = job["seconds"] if phase == "equal_time" else job["episodes"]
    checkpoints = [limit / 3, 2 * limit / 3, limit] if learning else []
    checkpoints = iter(checkpoints)
    next_checkpoint = next(checkpoints, None)
    rows, evaluations = [], []
    elapsed = cpu_elapsed = evaluation_seconds = 0.0
    stop_reason = "completed"
    started = time.perf_counter()
    with (out / "episodes.jsonl").open("w", encoding="utf-8") as log:
        while True:
            episode = len(rows) + 1
            progress = elapsed if phase == "equal_time" else len(rows)
            if progress >= limit:
                break
            if phase == "equal_time":
                agent.epsilon = epsilon_at_fraction(cfg, elapsed / limit)
            hits, misses = env.assigner.cache_hits, env.assigner.cache_misses
            requests = env.evaluation_requests
            epsilon = agent.epsilon
            t, cpu_t = time.perf_counter(), time.process_time()
            reward, records, steps, _ = run_episode(env, agent, train=True)
            if phase != "equal_time":
                agent.decay_epsilon()
            duration, cpu_duration = time.perf_counter() - t, time.process_time() - cpu_t
            elapsed += duration
            cpu_elapsed += cpu_duration
            day = summarise_day(records)
            if not np.isclose(reward, day["daily_plan_reward"], rtol=1e-10, atol=1e-9):
                raise AssertionError("Daily reward objective was not conserved")
            mem, free = memory_mb()
            row = dict(episode=episode, timestamp=utc_now(), training_seconds=elapsed, episode_seconds=duration,
                       cpu_seconds=cpu_duration, epsilon=epsilon, reward=reward, steps=steps,
                       served_demand_ratio=day["served_demand_ratio"], states=agent.num_states,
                       pairs=agent.num_state_action_pairs, memory_mb=mem,
                       evaluation_requests=env.evaluation_requests - requests,
                       cache_hits=env.assigner.cache_hits - hits,
                       cache_misses=env.assigner.cache_misses - misses,
                       forced_finishes=day["forced_hour_finishes"])
            rows.append(row)
            log.write(json.dumps(row) + "\n")
            log.flush()
            progress = elapsed if phase == "equal_time" else episode
            if next_checkpoint is not None and progress >= next_checkpoint:
                evaluation_started = utc_now()
                evaluation_t0 = time.perf_counter()
                evaluated = evaluate(agent, cfg, network, od, job['evaluation_seeds'])
                duration_evaluation = time.perf_counter() - evaluation_t0
                evaluation_seconds += duration_evaluation
                evaluations.append(dict(episode=episode, training_seconds=elapsed,
                                        started_at=evaluation_started, finished_at=utc_now(),
                                        evaluation_seconds=duration_evaluation, evaluations=evaluated))
                write_json(out / "evaluations.json", evaluations)
                while next_checkpoint is not None and progress >= next_checkpoint:
                    next_checkpoint = next(checkpoints, None)
            if episode % 25 == 0:
                print(f"{phase} {job['mode']} seed={job['seed']} ep={episode} train={elapsed:.1f}s", flush=True)
            if (mem is not None and mem > 1536) or (free is not None and free < 4096):
                stop_reason = "memory_guard_incomplete"
                break
            if learning and (episode >= 5000 or elapsed >= 1200):
                stop_reason = "safety_limit_incomplete"
                break
    result = dict(job=job, stop_reason=stop_reason, episodes=len(rows), evaluation_seconds=evaluation_seconds,
                  training_seconds=elapsed, training_cpu_seconds=cpu_elapsed,
                  mean_episode_seconds=statistics.mean(r["episode_seconds"] for r in rows),
                  steps=sum(r["steps"] for r in rows),
                  evaluation_requests=sum(r["evaluation_requests"] for r in rows),
                  cache_hits=sum(r["cache_hits"] for r in rows),
                  assignment_cache_misses=sum(r["cache_misses"] for r in rows),
                  final_memory_mb=rows[-1]["memory_mb"],
                  process_wall_seconds_including_evaluation=time.perf_counter() - started,
                  evaluations=evaluations)
    write_json(out / "summary.json", result)
    return result


def build_plan():
    modes = list(MODES)
    return dict(version=2, modes=MODES, workers=3, training_seeds=[2027, 2028, 2029],
                evaluation_seeds=[7000, 7001, 7002], timing_episodes=100,
                learning_episodes=300, equal_time_seconds=120,
                numerical_threads_per_worker=1, gpu=False,
                constraints=dict(worker_memory_mib=1536, minimum_free_memory_mib=4096,
                                 maximum_learning_episodes=5000, maximum_training_seconds_per_job=1200),
                timing_order=random.Random(20261113).sample(modes, len(modes)),
                learning_waves=[[dict(mode=modes[(i + wave) % 3], seed=2027 + wave)
                                 for i in range(3)] for wave in range(3)],
                notes=["Timing jobs run serially, 100 episodes, original 10000-episode epsilon schedule.",
                       "Equal-episode learning: 300 episodes, shared decay reaching min epsilon at episode 240.",
                       "Equal-time learning: 120 training seconds, shared time-based decay reaching min at 96 seconds.",
                       "Time budgets include training only; stop at episode boundary and record overshoot.",
                       "Common greedy evaluator at thirds and endpoint, three independent tie-breaking seeds.",
                       "Fresh learner per job; no Q-table exports, plotting, or shared caches.",
                       "Three workers per wave, one mode each, same training seed; new processes each wave.",
                       "Preliminary learning comparison: three seeds and short horizon cannot establish convergence."])


def evaluate_untrained(seeds):
    cfg = make_config('C_hour_end')
    network = load_network_from_csv(cfg.links_path,cfg.num_stops,cfg.links_are_bidirectional,cfg.input_stop_id_base)
    od = load_od_matrices(cfg.od_dir,cfg.od_filename_pattern,cfg.num_hours,cfg.num_stops,cfg.od_file_numbers())
    agent = QLearningAgent(cfg, 2027)
    started, t0 = utc_now(), time.perf_counter()
    values = evaluate(agent,cfg,network,od,seeds)
    assert not agent.q and not agent.visits
    return dict(status='completed', started_at=started, finished_at=utc_now(),
                evaluation_seconds=time.perf_counter()-t0, evaluations=values,
                note='Prespecified empty-Q-table diagnostic; no training; not an independent trained seed.')


def preflight_worker(mode):
    """Check real inputs/dependencies in a spawned process, without learning."""
    cfg = make_config(mode)
    network = load_network_from_csv(cfg.links_path, cfg.num_stops, cfg.links_are_bidirectional,
                                    cfg.input_stop_id_base)
    od = load_od_matrices(cfg.od_dir, cfg.od_filename_pattern, cfg.num_hours,
                          cfg.num_stops, cfg.od_file_numbers())
    working, free = memory_mb()
    return dict(pid=os.getpid(), mode=mode, stops=network.num_stops, hourly_matrices=len(od),
                numpy=np.__version__, scipy=scipy.__version__, working_set_mib=working,
                free_memory_mib=free, numerical_threads={key: os.environ[key] for key in
                ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS")})


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", action="store_true", help="explicitly start all experiment phases")
    parser.add_argument("--stage", choices=("all", "timing", "equal_episodes", "equal_time"),
                        default="all", help="run only the selected stage")
    parser.add_argument('--study-id', default='EXP-002')
    parser.add_argument("--output", type=Path,
                        default=ROOT / "transit_rl/results/EXP-002-repeat")
    args = parser.parse_args(argv)
    plan = build_plan()
    args.output.mkdir(parents=True, exist_ok=True)
    if (args.output / "manifest.json").exists():
        raise FileExistsError("Existing experiment manifest: choose a new --output")
    write_json(args.output / "plan.json", plan)
    if not args.run:
        with ProcessPoolExecutor(max_workers=3, max_tasks_per_child=1,
                                 mp_context=multiprocessing.get_context("spawn")) as pool:
            futures = [pool.submit(preflight_worker, mode) for mode in MODES]
            write_json(args.output / "preflight.json", [future.result() for future in futures])
        print(f"Prepared plan only; no training started. {args.output / 'plan.json'}")
        return 0
    git_status = subprocess.check_output(['git', 'status', '--porcelain'], cwd=ROOT, text=True)
    if git_status.strip():
        raise RuntimeError('Commit code/protocol/analysis and start with a clean worktree before research runs')
    _, free = memory_mb()
    if free is not None and free < 8192:
        raise RuntimeError("Need at least 8 GiB free RAM before starting three workers")
    files = [*ROOT.glob("transit_rl/**/*.py"), *ExperimentConfig().data_dir.rglob("*.csv")]
    files = [p for p in files if "results" not in p.relative_to(ROOT).parts]
    code_commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    command = subprocess.list2cmdline([sys.executable, '-m', 'transit_rl.experiment.evaluation_comparison', *sys.argv[1:]])
    packages = subprocess.check_output([sys.executable, '-m', 'pip', 'freeze', '--all'], text=True)
    write_json(args.output/'environment.json', dict(python=sys.version, executable=sys.executable,
               platform=platform.platform(), packages=packages.splitlines(), numerical_threads=1))
    (args.output/'requirements-lock.txt').write_text(packages, encoding='utf-8')
    hardware_script = "$ErrorActionPreference='Stop'; [ordered]@{cpu=@(Get-CimInstance Win32_Processor | Select-Object Name,NumberOfCores,NumberOfLogicalProcessors); memory=(Get-CimInstance Win32_OperatingSystem | Select-Object TotalVisibleMemorySize,FreePhysicalMemory); gpu=@(Get-CimInstance Win32_VideoController | Select-Object Name,AdapterRAM); battery=@(Get-CimInstance Win32_Battery | Select-Object BatteryStatus,EstimatedChargeRemaining); power_scheme=(powercfg /getactivescheme)} | ConvertTo-Json -Depth 5"
    machine = json.loads(subprocess.check_output(['powershell.exe','-NoProfile','-Command', hardware_script], text=True))
    write_json(args.output/'machine.json', machine)
    manifest = dict(study_id=args.study_id, started_at=utc_now(), finished_at=None, status='running',
                    command=command, plan=plan, selected_stage=args.stage, python=sys.version, numpy=np.__version__, scipy=scipy.__version__,
                    platform=platform.platform(), cpu_count=os.cpu_count(), free_memory_mib=free,
                    commit=code_commit, git_status=git_status,
                    source_and_input_sha256={str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                                             for p in files})
    write_json(args.output / "manifest.json", manifest)
    for path in files:
        snapshot = args.output / "snapshot" / path.relative_to(ROOT)
        snapshot.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, snapshot)
    (args.output / "source.patch").write_text(subprocess.check_output(
        ["git", "diff", "HEAD"], cwd=ROOT, text=True), encoding="utf-8")
    results = []

    def job(phase, mode, seed):
        stage = {'timing':'S1', 'equal_episodes':'S2', 'equal_time':'S3'}[phase]
        run_id = f"{args.study_id}-{stage}-{mode[0]}-seed{seed}-run01"
        return dict(study_id=args.study_id,run_id=run_id,code_commit=code_commit,command=command,
                    phase=phase, mode=mode, seed=seed,
                    episodes=plan["timing_episodes"] if phase == "timing" else plan["learning_episodes"],
                    seconds=plan["equal_time_seconds"], evaluation_seeds=plan["evaluation_seeds"],
                    output=str(args.output / phase / run_id))

    def collect(result):
        results.append(result)
        write_json(args.output / "results.json", results)
        if result["stop_reason"] != "completed":
            manifest.update(status='incomplete', finished_at=utc_now(), completed_runs=len(results))
            write_json(args.output/'manifest.json', manifest)
            raise RuntimeError("Incomplete job: experiment stopped; inspect results before comparing")

    def resolve(future):
        try:
            return future.result()
        except BaseException as error:
            manifest.update(status='failed', finished_at=utc_now(), error=repr(error))
            write_json(args.output/'manifest.json', manifest)
            raise

    context = multiprocessing.get_context("spawn")
    with ProcessPoolExecutor(max_workers=1, mp_context=context) as pool:
        baseline = resolve(pool.submit(evaluate_untrained, plan['evaluation_seeds']))
        baseline.update(study_id=args.study_id,run_id=f'{args.study_id}-B0-untrained-run01',code_commit=code_commit)
        write_json(args.output/'untrained_evaluation.json', baseline)
    for mode in plan["timing_order"] if args.stage in ("all", "timing") else []:
        # Fresh single process isolates memory and makes timings comparable.
        with ProcessPoolExecutor(max_workers=1, mp_context=context) as pool:
            collect(resolve(pool.submit(run_job, job("timing", mode, plan['training_seeds'][0]))))
    for phase in ("equal_episodes", "equal_time"):
        if args.stage not in ("all", phase):
            continue
        for wave in plan["learning_waves"]:
            with ProcessPoolExecutor(max_workers=3, mp_context=context) as pool:
                futures = [pool.submit(run_job, job(phase, item["mode"], item["seed"])) for item in wave]
                for future in futures:
                    collect(resolve(future))
    manifest.update(status='completed', finished_at=utc_now(), completed_runs=len(results))
    write_json(args.output/'manifest.json', manifest)
    print(f"Completed {len(results)} jobs. Raw results: {args.output / 'results.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
