"""EXP-004 stage-1 preflight only: two training episodes, three evaluations."""
import argparse
import copy
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
from ..agent.q_learning_agent import QLearningAgent
from ..data.network import load_network_from_csv
from ..data.od_loader import load_od_matrices
from ..utils.awake import keep_awake
from .service_diagnostics import DiagnosticEnvironment
from .trainer import run_episode, summarise_day
from .evaluation_comparison import memory_mb

ROOT = Path(__file__).resolve().parents[2]


def write(path, value):
    path.write_text(json.dumps(value, indent=2, default=str) + '\n', encoding='utf-8')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', action='store_true')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if not args.run:
        parser.error('Execution requires --run; this command never runs 300 episodes.')
    status = subprocess.check_output(['git', 'status', '--porcelain'], cwd=ROOT, text=True)
    allowed = {'README.md', 'docs/RL_TRAINING_AND_USE_GUIDE.md'}
    unexpected = [line for line in status.splitlines() if line[3:] not in allowed]
    if unexpected:
        raise RuntimeError('Experiment/input worktree must be clean: ' + repr(unexpected))
    commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    args.output.mkdir(parents=True, exist_ok=False)
    start, cpu = time.perf_counter(), time.process_time()
    manifest = dict(study='EXP-004', stage='S1-preflight', status='running',
                    started_at=datetime.now(timezone.utc).isoformat(), code_commit=commit,
                    working_tree_status=status, command=sys.argv, training_seed=2034,
                    evaluation_seeds=[7100, 7101, 7102], python=sys.version,
                    executable=sys.executable, platform=platform.platform(),
                    numpy=np.__version__, scipy=scipy.__version__, cpu_count=os.cpu_count(),
                    numerical_threads=1, workers=1, gpu_used=False,
                    qtable='not_saved', checkpoint='not_saved')
    write(args.output / 'manifest.json', manifest)
    try:
        cfg = replace(ExperimentConfig(), num_episodes=300, make_plots=False, copy_best_qtable=False)
        cfg.validate()
        write(args.output / 'config.json', asdict(cfg))
        sources = [cfg.links_path, *sorted(cfg.od_dir.glob('*.csv')),
                   *sorted((ROOT / 'transit_rl').rglob('*.py'))]
        write(args.output / 'input_source_sha256.json', {
            p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in sources})
        working, free = memory_mb()
        manifest['initial_memory_mb'] = dict(working=working, free=free)
        if free is not None and free < 4096:
            raise RuntimeError('Less than 4 GiB free memory')
        net = load_network_from_csv(cfg.links_path, cfg.num_stops, cfg.links_are_bidirectional,
                                    cfg.input_stop_id_base)
        od = load_od_matrices(cfg.od_dir, cfg.od_filename_pattern, cfg.num_hours,
                             cfg.num_stops, cfg.od_file_numbers())
        with keep_awake() as awake:
            manifest['sleep_prevention'] = awake
            agent = QLearningAgent(cfg, 2034)
            env = DiagnosticEnvironment(net, od, cfg)
            env.observer_agent = agent
            with (args.output / 'episodes.jsonl').open('w', encoding='utf-8') as log:
                for episode in (1, 2):
                    tick, proc = time.perf_counter(), time.process_time()
                    reward, records, steps, unseen = run_episode(env, agent, True)
                    agent.decay_epsilon()
                    working, free = memory_mb()
                    row = dict(episode=episode, reward=reward, steps=steps, unseen=unseen,
                               elapsed_seconds=time.perf_counter()-tick,
                               cpu_seconds=time.process_time()-proc, working_mb=working,
                               **summarise_day(records))
                    log.write(json.dumps(row) + '\n')
                    log.flush()
                    write(args.output / f'training-{episode}-hours.json', env.diagnostics)
                    if (working is not None and working > 1536) or time.perf_counter()-start > 120:
                        raise RuntimeError('Preflight memory/time guard exceeded')
            evaluations = []
            rng_before, pairs_before = agent.rng.getstate(), agent.num_state_action_pairs
            q_before, visits_before = copy.deepcopy(agent.q), copy.deepcopy(agent.visits)
            for seed in (7100, 7101, 7102):
                observer = QLearningAgent(cfg, seed)
                observer.q, observer.visits = agent.q, agent.visits
                evaluation = DiagnosticEnvironment(net, od, cfg)
                evaluation.observer_agent = observer
                tick = time.perf_counter()
                reward, records, steps, unseen = run_episode(evaluation, observer, False)
                evaluations.append(dict(seed=seed, reward=reward, steps=steps, unseen=unseen,
                                        elapsed_seconds=time.perf_counter()-tick,
                                        **summarise_day(records)))
                write(args.output / f'evaluation-{seed}-hours.json', evaluation.diagnostics)
            assert agent.rng.getstate() == rng_before and agent.num_state_action_pairs == pairs_before
            assert agent.q == q_before and agent.visits == visits_before
            manifest['evaluation_learner_unchanged'] = True
            write(args.output / 'evaluations.json', evaluations)
        manifest.update(status='completed', sleep_scope_exited=True)
    except BaseException as error:
        manifest.update(status='failed', error=repr(error))
        raise
    finally:
        manifest.update(finished_at=datetime.now(timezone.utc).isoformat(),
                        elapsed_seconds=time.perf_counter()-start, cpu_seconds=time.process_time()-cpu)
        write(args.output / 'manifest.json', manifest)
    print(json.dumps({k: manifest[k] for k in ('status', 'code_commit', 'elapsed_seconds')}))


if __name__ == '__main__':
    main()
