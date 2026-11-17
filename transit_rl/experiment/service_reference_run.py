"""Registered EXP-004 S2 deterministic feasible-reference run, no training."""
import argparse
from dataclasses import asdict, replace
from datetime import datetime, timezone
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

from ..config import ExperimentConfig
from ..data.network import load_network_from_csv
from ..data.od_loader import load_od_matrices
from ..environment.transit_environment import TransitEnvironment
from ..utils.awake import keep_awake
from .evaluation_comparison import memory_mb
from .service_diagnostics import DiagnosticEnvironment
from .service_reference import ReferencePlanner, shortest_path_candidates
from .service_preflight import write
from .trainer import summarise_day

ROOT = Path(__file__).resolve().parents[2]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', action='store_true')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if not args.run:
        parser.error('--run required')
    status = subprocess.check_output(['git', 'status', '--porcelain'], cwd=ROOT, text=True)
    if status.strip():
        raise RuntimeError('Requires clean isolated execution worktree')
    commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    args.output.mkdir(parents=True, exist_ok=False)
    start, cpu = time.perf_counter(), time.process_time()
    manifest = dict(study='EXP-004', stage='S2-reference', status='running', code_commit=commit,
        working_tree_status=status, started_at=datetime.now(timezone.utc).isoformat(),
        command=sys.argv, cwd=str(ROOT), python=sys.version, executable=sys.executable,
        numpy=np.__version__, scipy=scipy.__version__, platform=platform.platform(),
        logical_cpus=os.cpu_count(), workers=1, numeric_threads=1, gpu=False,
        deterministic=True, rng='not_used', max_search_requests_per_hour=2000,
        max_accepted_edits_per_hour=120, replacement_rounds=3,
        qtable='not_applicable', checkpoint='not_applicable', completed_hours=0)
    write(args.output / 'manifest.json', manifest)
    try:
        cfg = replace(ExperimentConfig(), num_episodes=300, reward_mode='dense',
                      make_plots=False, copy_best_qtable=False)
        cfg.validate()
        write(args.output / 'config.json', asdict(cfg))
        source_files = [cfg.links_path, *sorted(cfg.od_dir.glob('*.csv')),
                        *sorted((ROOT / 'transit_rl').rglob('*.py'))]
        write(args.output / 'source-input-sha256.json', {
            p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in source_files})
        (args.output / 'requirements-lock.txt').write_text(
            subprocess.check_output([sys.executable, '-m', 'pip', 'freeze'], text=True), encoding='utf-8')
        try:
            manifest['power_scheme'] = subprocess.check_output(['powercfg', '/getactivescheme'], text=True).strip()
        except Exception as error:
            manifest['power_scheme'] = 'unavailable: ' + repr(error)
        working, free = memory_mb()
        manifest['initial_memory_mb'] = dict(working=working, free=free)
        if free is not None and free < 4096:
            raise RuntimeError('Less than4GiB free memory')
        net = load_network_from_csv(cfg.links_path, cfg.num_stops, cfg.links_are_bidirectional, cfg.input_stop_id_base)
        od = load_od_matrices(cfg.od_dir, cfg.od_filename_pattern, cfg.num_hours, cfg.num_stops, cfg.od_file_numbers())
        with keep_awake() as awake:
            manifest['sleep_prevention'] = awake
            env = TransitEnvironment(net, od, cfg)
            tick = time.perf_counter()
            candidates = shortest_path_candidates(net, cfg)
            write(args.output / 'route-candidates.json', candidates)
            manifest['candidate_generation_seconds'] = time.perf_counter()-tick
            planner = ReferencePlanner(env, candidates)
            previous, planned, queries = env.initial_plan, [], 0
            tick, proc = time.perf_counter(), time.process_time()
            with (args.output / 'search-hours.jsonl').open('w', encoding='utf-8') as file:
                for hour in range(1, cfg.num_hours+1):
                    ht = time.perf_counter()
                    result = planner.plan_hour(hour, previous)
                    planned.append(result)
                    previous = result['plan']
                    queries += result['requests']
                    working, free = memory_mb()
                    value = dict(hour=hour, clock_hour=cfg.od_file_number(hour),
                        routes=[list(r.route) for r in previous], frequencies=[r.frequency for r in previous],
                        original_score=result['evaluation'].reward['total_reward'],
                        served=result['evaluation'].assignment.served_passengers,
                        fleet_used=result['evaluation'].fleet_used,
                        requests=result['requests'], edits=result['edits'], accepted=result['accepted'],
                        actions=[dict(type=a.type, arg=a.arg) for a in result['actions']],
                        action_count=len(result['actions']), within_original_60_actions=len(result['actions']) <= cfg.max_steps_per_hour,
                        evaluation_budget_reached=result['evaluation_budget_reached'], edit_budget_reached=result['edit_budget_reached'],
                        elapsed_seconds=time.perf_counter()-ht, working_mb=working, free_mb=free)
                    file.write(json.dumps(value, separators=(',', ':'))+'\n')
                    file.flush()
                    manifest['completed_hours'] = hour
                    print(f'Hour {hour}/24: served {value["served"]:.1f}, fleet {value["fleet_used"]}, requests {value["requests"]}, actions {value["action_count"]}', flush=True)
                    if time.perf_counter()-start > 600 or (working is not None and working > 1536) or (free is not None and free < 4096):
                        raise RuntimeError('Reference time/memory guard; preserve incomplete run')
            manifest.update(search_seconds=time.perf_counter()-tick, search_cpu_seconds=time.process_time()-proc,
                search_evaluation_requests=queries, search_assignment_cache_hits=env.assigner.cache_hits,
                search_assignment_cache_misses=env.assigner.cache_misses)
            # Replay all accepted moves through the original action masks and reward
            # implementation. Raise deadline only if trace exceeds original60steps.
            replay_limit = max(cfg.max_steps_per_hour, max(len(r['actions']) for r in planned))
            replay = DiagnosticEnvironment(net, od, replace(cfg, max_steps_per_hour=replay_limit))
            total_reward, tick = 0.0, time.perf_counter()
            for hour, result in enumerate(planned, 1):
                for action in result['actions']:
                    step = replay.step(action)
                    total_reward += step.reward
                assert replay.hourly_plans[hour] == result['plan']
                actual = replay.hourly_records[-1]
                expected = result['evaluation']
                assert abs(actual['served_passengers'] - expected.assignment.served_passengers) < 1e-6
                assert abs(actual['total_reward'] - expected.reward['total_reward']) < 1e-9
                assert not actual['forced_finish']
            assert replay.done
            daily = summarise_day(replay.hourly_records)
            assert abs(total_reward - daily['daily_plan_reward']) < 1e-8
            write(args.output / 'service-plan.json', dict(daily=daily, hours=replay.hourly_records,
                diagnostics=replay.diagnostics, replay_action_limit=replay_limit,
                original_action_limit=cfg.max_steps_per_hour,
                hours_exceeding_original_action_limit=[i for i, r in enumerate(planned, 1) if len(r['actions']) > cfg.max_steps_per_hour],
                no_learner=True, actions=sum(len(r['actions']) for r in planned)))
            manifest.update(replay_seconds=time.perf_counter()-tick, replay_verified=True)
        manifest.update(status='completed', sleep_scope_exited=True)
    except BaseException as error:
        manifest.update(status='failed', error=repr(error))
        raise
    finally:
        manifest.update(finished_at=datetime.now(timezone.utc).isoformat(),
            total_elapsed_seconds=time.perf_counter()-start, total_cpu_seconds=time.process_time()-cpu)
        write(args.output / 'manifest.json', manifest)
    print(json.dumps(dict(status=manifest['status'], total_seconds=manifest['total_elapsed_seconds'])), flush=True)


if __name__ == '__main__':
    main()
