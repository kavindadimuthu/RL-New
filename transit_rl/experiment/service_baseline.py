"""EXP-004 S1: one registered 300-episode diagnostic baseline per process."""
import argparse
from contextlib import nullcontext
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
from .remaining_action_state import RemainingActionEnvironment, keyed_episode
from .linear_q import LinearQAgent, FEATURE_NAMES
from .return_control import ReturnAgent, comparison_episode

ROOT = Path(__file__).resolve().parents[2]


def learner_digest(agent):
    digest = hashlib.sha256()
    for key, row in agent.q.items():
        digest.update(repr((key, row, agent.visits.get(key))).encode())
    digest.update(repr((len(agent.visits), agent.num_state_action_pairs,
                        agent.epsilon, agent.rng.getstate())).encode())
    if isinstance(agent, LinearQAgent):
        digest.update(agent.weights.tobytes())
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


def evaluate(agent, cfg, net, od, episode, directory, env_type=DiagnosticEnvironment):
    before = learner_digest(agent)
    results = []
    for seed in (7100, 7101, 7102):
        observer = LinearQAgent(cfg, seed, net) if isinstance(agent, LinearQAgent) else QLearningAgent(cfg, seed)
        if isinstance(agent, LinearQAgent):
            observer.weights = agent.weights  # read-only use; digest verifies unchanged
        observer.q, observer.visits = agent.q, agent.visits
        env = env_type(net, od, cfg)
        env.observer_agent = observer
        tick, cpu = time.perf_counter(), time.process_time()
        reward, records, steps, unseen = keyed_episode(env, observer, False)
        results.append(dict(seed=seed, reward=reward, steps=steps, unseen=unseen,
                            elapsed_seconds=time.perf_counter()-tick,
                            cpu_seconds=time.process_time()-cpu,
                            daily=summarise_day(records), diagnostics=diagnostic_summary(env.diagnostics),
                            hours=env.diagnostics))
        if isinstance(observer, LinearQAgent):
            assert observer.greedy_audit['decisions'] == steps
            assert observer.greedy_audit['unseen_exact_key'] == unseen
            results[-1]['generalization_audit'] = dict(observer.greedy_audit)
    assert learner_digest(agent) == before, 'Evaluation mutated learner'
    value = dict(episode=episode, learner_unchanged=True, evaluations=results)
    write(directory / f'evaluation-{episode:03d}.json', value)
    if isinstance(agent, LinearQAgent):
        write(directory / f'weights-{episode:03d}.json', agent.snapshot())
    return value


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', action='store_true')
    parser.add_argument('--seed', type=int, choices=(2034, 2035, 2036), required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--method', choices=('A', 'B', 'E', 'L'), default=None,
                        help='A/B: S4; S5 E: deadline-aware exact table, L: normalized linear Q')
    parser.add_argument('--episodes', type=int, choices=(2, 25, 300), default=300,
                        help='2 only for registered S5 preflight; epsilon schedule remains300')
    parser.add_argument('--stability-revision', action='store_true', help='Registered S6: L only, fixed learning rate .001')
    parser.add_argument('--return-comparison', choices=('T', 'M'), help='S9: .001 linear TD or episodic return update')
    args = parser.parse_args()
    if args.return_comparison and (args.method != 'L' or args.stability_revision or args.episodes not in (25, 300)):
        parser.error('S9 requires L, 25/300 episodes, no S6 flag')
    if args.episodes == 25 and not args.return_comparison:
        parser.error('25 episodes reserved for S9 preflight')
    if args.stability_revision and (args.method != 'L' or args.episodes != 300):
        parser.error('S6 requires L and 300 episodes')
    if not args.run:
        parser.error('--run required')
    if args.episodes != 300 and args.method not in ('E', 'L'):
        parser.error('Short run allowed only for S5 preflight')
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
    if args.method:
        manifest.update(stage='S4-remaining-actions', method=args.method, paired_workers=2,
            observation='original_six_fields' if args.method == 'A' else 'original_six_fields_plus_remaining_actions')
    checkpoints = (0, 2) if args.episodes == 2 else (0, 100, 300)
    if args.method in ('E', 'L'):
        manifest.update(stage='S5-feature-preflight' if args.episodes == 2 else 'S5-function-approx',
            target_episodes=args.episodes, checkpoints=list(checkpoints),
            algorithm='exact_tabular_q' if args.method == 'E' else 'unit_feature_linear_semigradient_q',
            feature_count=len(FEATURE_NAMES), feature_normalization='L2_unit_per_action_for_L_only',
            stability_guards=dict(max_abs_q=1000, max_weight_row_norm=10000) if args.method == 'L' else None,
            training_budget_seconds=120 if args.episodes == 2 else 900)
    if args.stability_revision:
        manifest.update(stage='S6-linear-stability', paired_workers=1, learning_rate=.001)
    if args.return_comparison:
        checkpoints = (0, 25) if args.episodes == 25 else (0, 100, 300)
        manifest.update(stage='S9-preflight' if args.episodes == 25 else 'S9-return-comparison',
            return_method=args.return_comparison, target_episodes=args.episodes,
            checkpoints=list(checkpoints), learning_rate=.001,
            training_budget_seconds=300 if args.episodes == 25 else 900,
            algorithm='linear_q_online' if args.return_comparison == 'T' else 'linear_episodic_return_regression')
    write(args.output / 'manifest.json', manifest)
    training_time = training_cpu = 0.0
    agent = None
    try:
        cfg = replace(ExperimentConfig(), num_episodes=300, reward_mode='dense',
                      make_plots=False, copy_best_qtable=False)
        if args.stability_revision or args.return_comparison:
            cfg = replace(cfg, learning_rate=.001)
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
            agent = (ReturnAgent(cfg, args.seed, net) if args.return_comparison == 'M' else
                     LinearQAgent(cfg, args.seed, net) if args.method == 'L' else QLearningAgent(cfg, args.seed))
            env_type = RemainingActionEnvironment if args.method in ('B', 'E', 'L') else DiagnosticEnvironment
            env = env_type(net, od, cfg)
            env.observer_agent = agent
            evaluate(agent, cfg, net, od, 0, args.output, env_type)
            with (args.output / 'episodes.jsonl').open('w', encoding='utf-8') as metrics, \
                 gzip.open(args.output / 'training-hours.jsonl.gz', 'wt', encoding='utf-8') as hours, \
                 (gzip.open(args.output / 'target-audit.jsonl.gz', 'wt', encoding='utf-8') if args.return_comparison else nullcontext(None)) as targets:
                for episode in range(1, args.episodes+1):
                    tick, proc = time.perf_counter(), time.process_time()
                    if args.return_comparison:
                        reward, records, steps, unseen, audit = comparison_episode(env, agent, args.return_comparison == 'M')
                    else:
                        reward, records, steps, unseen = keyed_episode(env, agent, True)
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
                    if isinstance(agent, LinearQAgent):
                        row.update(weight_norm=float(np.linalg.norm(agent.weights)),
                                   parameter_count=int(agent.weights.size))
                    if args.return_comparison:
                        row.update(empty_hours=sum(h['route_count'] == 0 for h in env.diagnostics),
                            minimum_update_target=min(a['target'] for a in audit),
                            maximum_update_target=max(a['target'] for a in audit))
                        targets.write(json.dumps(dict(episode=episode, updates=audit), separators=(',', ':'))+'\n')
                        targets.flush()
                    metrics.write(json.dumps(row, separators=(',', ':')) + '\n')
                    metrics.flush()
                    hours.write(json.dumps(dict(episode=episode, hours=env.diagnostics), separators=(',', ':'))+'\n')
                    hours.flush()
                    manifest['episodes_completed'] = episode
                    if episode % 25 == 0:
                        print(f'method {args.method or "baseline"} seed {args.seed}: {episode}/{args.episodes}, training {training_time:.1f}s, RAM {working:.0f}MiB', flush=True)
                        write(args.output / 'manifest.json', manifest)
                    if (working is not None and working > 1536) or (free is not None and free < 4096) or training_time > manifest['training_budget_seconds']:
                        manifest['status'] = 'resource_guard_incomplete'
                        break
                    if episode in checkpoints:
                        evaluate(agent, cfg, net, od, episode, args.output, env_type)
            if manifest['status'] == 'running':
                manifest['status'] = 'completed'
        manifest['sleep_scope_exited'] = True
    except BaseException as error:
        manifest.update(status='failed', error=repr(error))
        raise
    finally:
        if isinstance(agent, LinearQAgent):
            write(args.output / 'weights-final.json', agent.snapshot())
        manifest.update(finished_at=datetime.now(timezone.utc).isoformat(),
                        total_elapsed_seconds=time.perf_counter()-start,
                        total_cpu_seconds=time.process_time()-proc_start,
                        training_seconds=training_time, training_cpu_seconds=training_cpu)
        write(args.output / 'manifest.json', manifest)
    print(json.dumps(manifest), flush=True)


if __name__ == '__main__':
    main()
