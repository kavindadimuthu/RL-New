"""EXP-004 S1: one registered 300-episode diagnostic baseline per process."""
import argparse
from dataclasses import asdict, replace
from datetime import datetime, timezone
import gzip
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import time

for name in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS', 'NUMEXPR_NUM_THREADS'):
    os.environ[name] = '1'

import numpy as np
import scipy

from ..agent.q_learning_agent import QLearningAgent
from ..config import ExperimentConfig
from ..data.network import load_network_from_csv
from ..data.od_loader import load_od_matrices
from ..utils.awake import keep_awake
from .evaluation_comparison import memory_mb
from .service_diagnostics import DiagnosticEnvironment
from .service_preflight import write
from .trainer import run_episode, summarise_day

ROOT = Path(__file__).resolve().parents[2]


def learner_digest(agent):
    digest = hashlib.sha256()
    for key, row in agent.q.items():
        digest.update(repr((key, row, agent.visits.get(key))).encode())
    digest.update(repr((len(agent.visits), agent.num_state_action_pairs,
                        agent.epsilon, agent.rng.getstate())).encode())
    return digest.hexdigest()


def diagnostic_summary(rows):
    demand = sum(r['total_demand'] for r in rows)
    steps = sum(r['actions'] for r in rows)
    def ratio(field):
        return sum(r[field] for r in rows) / demand if demand else 0.0
    summary = dict(served_ratio=ratio('served_passengers'),
        no_path_demand_share=ratio('no_eligible_path_unserved'),
        capacity_demand_share=ratio('capacity_constrained_unserved'),
        unseen_fraction=sum(r['unseen_decisions'] for r in rows)/steps if steps else 0,
        rare_state_fraction=sum(r['rare_state_decisions_lt5'] for r in rows)/steps if steps else 0,
        average_fleet=sum(r['fleet_used'] for r in rows)/len(rows),
        mean_route_count=sum(r['route_count'] for r in rows)/len(rows),
        forced_finishes=sum(r['forced_finish'] for r in rows),
        voluntary_finishes=sum(not r['forced_finish'] for r in rows),
        discarded_routes=sum(bool(r['discarded_unfinished_route']) for r in rows),
        total_demand=demand, actions=steps)
    for label, subset in [('forced', [r for r in rows if r['forced_finish']]),
                          ('voluntary', [r for r in rows if not r['forced_finish']]),
                          ('peak', [r for r in rows if r['clock_hour'] in (8, 9, 16, 17)]),
                          ('other', [r for r in rows if r['clock_hour'] not in (8, 9, 16, 17)])]:
        volume = sum(r['total_demand'] for r in subset)
        summary[label + '_served_ratio'] = sum(r['served_passengers'] for r in subset)/volume if volume else None
    return summary


def evaluate(agent, cfg, net, od, episode, directory):
    before = learner_digest(agent)
    results = []
    for seed in (7100, 7101, 7102):
        observer = QLearningAgent(cfg, seed)
        observer.q, observer.visits = agent.q, agent.visits
        env = DiagnosticEnvironment(net, od, cfg)
        env.observer_agent = observer
        tick, cpu = time.perf_counter(), time.process_time()
        reward, records, steps, unseen = run_episode(env, observer, False)
        results.append(dict(seed=seed, reward=reward, steps=steps, unseen=unseen,
                            elapsed_seconds=time.perf_counter()-tick,
                            cpu_seconds=time.process_time()-cpu,
                            daily=summarise_day(records), diagnostics=diagnostic_summary(env.diagnostics),
                            hours=env.diagnostics))
    assert learner_digest(agent) == before, 'Evaluation mutated learner'
    value = dict(episode=episode, learner_unchanged=True, evaluations=results)
    write(directory / f'evaluation-{episode:03d}.json', value)
    return value


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', action='store_true')
    parser.add_argument('--seed', type=int, choices=(2034, 2035, 2036), required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if not args.run:
        parser.error('--run required')
    status = subprocess.check_output(['git', 'status', '--porcelain'], cwd=ROOT, text=True)
    if status.strip():
        raise RuntimeError('Full baseline requires a clean isolated execution worktree')
    commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    args.output.mkdir(parents=True, exist_ok=False)
    start, proc_start = time.perf_counter(), time.process_time()
    manifest = dict(study='EXP-004', stage='S1-baseline', status='running',
        training_seed=args.seed, evaluation_seeds=[7100, 7101, 7102],
        checkpoints=[0, 100, 300], target_episodes=300, episodes_completed=0,
        code_commit=commit, working_tree_status=status, command=sys.argv, cwd=str(ROOT),
        started_at=datetime.now(timezone.utc).isoformat(), python=sys.version,
        executable=sys.executable, numpy=np.__version__, scipy=scipy.__version__,
        platform=platform.platform(), logical_cpus=os.cpu_count(), workers=1, numeric_threads=1,
        gpu=False, training_budget_seconds=600, qtable='not_saved', checkpoint='not_saved')
    write(args.output / 'manifest.json', manifest)
    training_time = training_cpu = 0.0
    try:
        cfg = replace(ExperimentConfig(), num_episodes=300, reward_mode='dense',
                      make_plots=False, copy_best_qtable=False)
        cfg.validate()
        write(args.output / 'config.json', asdict(cfg))
        files = [cfg.links_path, *sorted(cfg.od_dir.glob('*.csv')),
                 *sorted((ROOT / 'transit_rl').rglob('*.py'))]
        write(args.output / 'source-input-sha256.json', {
            p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in files})
        packages = subprocess.check_output([sys.executable, '-m', 'pip', 'freeze'], text=True)
        (args.output / 'requirements-lock.txt').write_text(packages, encoding='utf-8')
        # AC status and active scheme are observations, not global changes.
        for name, command in [('power', ['powercfg', '/getactivescheme']),
                              ('battery', ['powershell', '-NoProfile', '-Command',
                               'Get-CimInstance Win32_Battery | Select-Object BatteryStatus,EstimatedChargeRemaining | ConvertTo-Json'])]:
            try:
                manifest[name] = subprocess.check_output(command, text=True, timeout=15).strip()
            except Exception as error:
                manifest[name] = 'unavailable: ' + repr(error)
        working, free = memory_mb()
        manifest['initial_memory_mb'] = dict(working=working, free=free)
        if free is not None and free < 4096:
            raise RuntimeError('Free RAM below 4 GiB')
        net = load_network_from_csv(cfg.links_path, cfg.num_stops,
                                    cfg.links_are_bidirectional, cfg.input_stop_id_base)
        od = load_od_matrices(cfg.od_dir, cfg.od_filename_pattern, cfg.num_hours,
                             cfg.num_stops, cfg.od_file_numbers())
        with keep_awake() as awake:
            manifest['sleep_prevention'] = awake
            agent = QLearningAgent(cfg, args.seed)
            env = DiagnosticEnvironment(net, od, cfg)
            env.observer_agent = agent
            evaluate(agent, cfg, net, od, 0, args.output)
            with (args.output / 'episodes.jsonl').open('w', encoding='utf-8') as metrics, \
                 gzip.open(args.output / 'training-hours.jsonl.gz', 'wt', encoding='utf-8') as hours:
                for episode in range(1, 301):
                    tick, proc = time.perf_counter(), time.process_time()
                    reward, records, steps, unseen = run_episode(env, agent, True)
                    elapsed, cpu = time.perf_counter()-tick, time.process_time()-proc
                    training_time += elapsed
                    training_cpu += cpu
                    agent.decay_epsilon()
                    working, free = memory_mb()
                    row = dict(episode=episode, reward=reward, steps=steps, unseen=unseen,
                        elapsed_seconds=elapsed, cpu_seconds=cpu, training_seconds=training_time,
                        epsilon_next=agent.epsilon, working_mb=working, free_mb=free,
                        q_states=agent.num_states, q_pairs=agent.num_state_action_pairs,
                        **summarise_day(records), diagnostics=diagnostic_summary(env.diagnostics))
                    metrics.write(json.dumps(row, separators=(',', ':')) + '\n')
                    metrics.flush()
                    hours.write(json.dumps(dict(episode=episode, hours=env.diagnostics), separators=(',', ':'))+'\n')
                    hours.flush()
                    manifest['episodes_completed'] = episode
                    if episode % 25 == 0:
                        print(f'seed {args.seed}: {episode}/300, training {training_time:.1f}s, RAM {working:.0f}MiB', flush=True)
                        write(args.output / 'manifest.json', manifest)
                    if (working is not None and working > 1536) or (free is not None and free < 4096) or training_time > 600:
                        manifest['status'] = 'resource_guard_incomplete'
                        break
                    if episode in (100, 300):
                        evaluate(agent, cfg, net, od, episode, args.output)
            if manifest['status'] == 'running':
                manifest['status'] = 'completed'
        manifest['sleep_scope_exited'] = True
    except BaseException as error:
        manifest.update(status='failed', error=repr(error))
        raise
    finally:
        manifest.update(finished_at=datetime.now(timezone.utc).isoformat(),
                        total_elapsed_seconds=time.perf_counter()-start,
                        total_cpu_seconds=time.process_time()-proc_start,
                        training_seconds=training_time, training_cpu_seconds=training_cpu)
        write(args.output / 'manifest.json', manifest)
    print(json.dumps(manifest), flush=True)


if __name__ == '__main__':
    main()
