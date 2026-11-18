"""EXP-004 S7 frozen-policy predictions and fixed-continuation returns; no training."""
import argparse
from dataclasses import asdict, replace
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

for name in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS', 'NUMEXPR_NUM_THREADS'):
    os.environ[name] = '1'

import numpy as np
from ..config import ExperimentConfig
from ..data.network import load_network_from_csv
from ..data.od_loader import load_od_matrices
from ..environment.actions import Action, FINISH_PLAN, END_ROUTE
from .remaining_action_state import RemainingActionEnvironment
from .linear_q import LinearQAgent, FEATURE_NAMES
from .service_preflight import write
from .trainer import summarise_day
from .evaluation_comparison import memory_mb
from ..utils.awake import keep_awake

ROOT = Path(__file__).resolve().parents[2]
STUDY = ROOT / 'experiments/EXP-004-service-quality-diagnosis'


def returns_to_go(rewards):
    result, total = [], 0.0
    for reward in reversed(rewards):
        total += reward
        result.append(total)
    return list(reversed(result))


def replay(env, actions):
    env.reset()
    rewards = []
    for action in actions:
        assert not env.done and action in env.valid_actions(), action
        rewards.append(env.step(action).reward)
    return rewards


def stop_continuation(env, prefix):
    replay(env, prefix)
    rewards = []
    while not env.done:
        action = Action(FINISH_PLAN)
        assert action in env.valid_actions()
        rewards.append(env.step(action).reward)
    return dict(remaining_return=sum(rewards), daily=summarise_day(env.hourly_records))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', action='store_true')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if not args.run:
        parser.error('--run required')
    status = subprocess.check_output(['git','status','--porcelain'], cwd=ROOT, text=True)
    if status.strip():
        raise RuntimeError('Clean execution checkout required')
    args.output.mkdir(parents=True, exist_ok=False)
    start = time.perf_counter()
    manifest = dict(study='EXP-004', stage='S7-stopping-diagnostic', status='running',
        code_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        working_tree_status=status, started_at=datetime.now(timezone.utc).isoformat(),
        command=sys.argv, python=sys.version, workers=1, numeric_threads=1, gpu=False,
        training='none', completed_trajectories=0)
    write(args.output/'manifest.json',manifest)
    try:
        cfg = replace(ExperimentConfig(),num_episodes=300,reward_mode='dense',
            learning_rate=.001,make_plots=False,copy_best_qtable=False)
        cfg.validate()
        write(args.output/'config.json',asdict(cfg))
        net = load_network_from_csv(cfg.links_path,cfg.num_stops,cfg.links_are_bidirectional,cfg.input_stop_id_base)
        od = load_od_matrices(cfg.od_dir,cfg.od_filename_pattern,cfg.num_hours,cfg.num_stops,cfg.od_file_numbers())
        reference = STUDY/'evidence/S3-reference60-run01/search-hours.jsonl'
        prior = STUDY/'evidence/S6-linear-stability-run01/EXP-004-S6-L-seed2034-run01'
        rows = [json.loads(line) for line in reference.read_text().splitlines()]
        full = [Action(a['type'],a['arg']) for row in rows for a in row['actions']]
        first = full[:next(i+1 for i,a in enumerate(full) if a.type==END_ROUTE)]
        traces = dict(empty=[Action(FINISH_PLAN)]*24,
            first_reference_route=first+[Action(FINISH_PLAN)]*24, full_reference=full)
        files = [reference,*[prior/f'weights-{n:03d}.json' for n in (0,100,300)],
                 cfg.links_path,*sorted(cfg.od_dir.glob('*.csv')),*sorted((ROOT/'transit_rl').rglob('*.py'))]
        write(args.output/'source-input-sha256.json',{p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in files})
        (args.output/'requirements-lock.txt').write_text(subprocess.check_output([sys.executable,'-m','pip','freeze'],text=True))
        models = {}
        for n in (0,100,300):
            snapshot=json.loads((prior/f'weights-{n:03d}.json').read_text())
            agent=LinearQAgent(cfg,0,net)
            agent.weights[:]=np.asarray(snapshot['weights'])
            assert snapshot['feature_names']==list(FEATURE_NAMES)
            models[n]=agent
        digests={n:hashlib.sha256(a.weights.tobytes()).hexdigest() for n,a in models.items()}
        def environment():
            return RemainingActionEnvironment(net,od,cfg)
        with keep_awake() as awake:
            manifest['sleep_prevention']=awake
            for name,actions in traces.items():
                env=environment()
                env.reset()
                records=[]
                for i,action in enumerate(actions):
                    valid=env.valid_actions()
                    assert action in valid and not env.done
                    key=env.learning_key(env.state)
                    predictions={str(n):dict(chosen=a.q_value(key,action),
                        best=float(a.values(key,valid).max()),
                        values=[dict(action=x._asdict(),q=float(q)) for x,q in zip(valid,a.values(key,valid))]) for n,a in models.items()}
                    stop=None
                    # Fixed probes: initial state, first route completion, second-hour start.
                    probe=(i==0 or (i>0 and actions[i-1].type==END_ROUTE and sum(x.type==END_ROUTE for x in actions[:i])==1) or (env.hour==2 and env.steps_in_hour==0))
                    if probe and Action(FINISH_PLAN) in valid:
                        stop=stop_continuation(environment(),actions[:i])
                    result=env.step(action)
                    records.append(dict(index=i,hour=key[0],remaining_actions=key[-1],
                        partial_route=list(key[2]),plan=[r._asdict() for r in key[3]],
                        action=action._asdict(),reward=result.reward,done=result.done,
                        predictions=predictions,stop_rest_of_day=stop))
                    working,free=memory_mb()
                    if time.perf_counter()-start>180 or (working and working>1536) or (free and free<4096):
                        raise RuntimeError('Registered diagnostic resource guard')
                assert env.done
                for record,value in zip(records,returns_to_go([r['reward'] for r in records])):
                    record['fixed_continuation_return']=value
                daily=summarise_day(env.hourly_records)
                assert abs(sum(r['reward'] for r in records)-daily['daily_plan_reward'])<1e-8
                write(args.output/f'{name}.json',dict(trajectory=name,daily=daily,hours=env.diagnostics,transitions=records))
                manifest['completed_trajectories']+=1
                write(args.output/'manifest.json',manifest)
            assert all(hashlib.sha256(a.weights.tobytes()).hexdigest()==digests[n] and not a.q and not a.visits for n,a in models.items())
            manifest['model_weights_unchanged']=True
        manifest.update(status='completed',sleep_scope_exited=True)
    except BaseException as error:
        manifest.update(status='failed',error=repr(error))
        raise
    finally:
        manifest.update(finished_at=datetime.now(timezone.utc).isoformat(),elapsed_seconds=time.perf_counter()-start)
        write(args.output/'manifest.json',manifest)


if __name__=='__main__':
    main()
