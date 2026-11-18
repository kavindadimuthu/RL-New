"""EXP-004 S8 fixed-return linear fits and frozen bootstrap-target audit."""
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

for name in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'):
    os.environ[name]='1'

import numpy as np
from ..config import ExperimentConfig
from ..data.network import load_network_from_csv
from ..data.od_loader import load_od_matrices
from ..environment.actions import Action, ADD_STOP, END_ROUTE, FINISH_PLAN, ACTION_TYPES
from .remaining_action_state import RemainingActionEnvironment
from .linear_q import LinearQAgent, FEATURE_NAMES
from .stopping_diagnostic import returns_to_go
from .service_preflight import write
from .trainer import summarise_day
from .evaluation_comparison import memory_mb
from ..utils.awake import keep_awake

ROOT=Path(__file__).resolve().parents[2]
STUDY=ROOT/'experiments/EXP-004-service-quality-diagnosis'


def design_vector(agent,key,action):
    row=np.zeros((len(ACTION_TYPES),len(FEATURE_NAMES)),dtype=np.float64)
    row[agent.encoder.type_index[action.type]]=agent.encoder.features(key,action)
    return row.ravel()


def fit_linear(matrix,targets,ridge=0.0):
    # Fixed SVD least squares; ridge is augmented least squares, no optimizer sweep.
    if ridge:
        matrix=np.vstack([matrix,np.sqrt(ridge)*np.eye(matrix.shape[1])])
        targets=np.concatenate([targets,np.zeros(matrix.shape[1])])
    weights,_,rank,singular=np.linalg.lstsq(matrix,targets,rcond=1e-10)
    assert np.all(np.isfinite(weights))
    return dict(weights=weights.tolist(),rank=int(rank),singular_values=singular.tolist(),
                norm=float(np.linalg.norm(weights)),ridge=ridge)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run',action='store_true')
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    if not args.run:
        parser.error('--run required')
    status=subprocess.check_output(['git','status','--porcelain'],cwd=ROOT,text=True)
    if status.strip():
        raise RuntimeError('Clean execution checkout required')
    args.output.mkdir(parents=True,exist_ok=False)
    start=time.perf_counter()
    manifest=dict(study='EXP-004',stage='S8-return-fit',status='running',
        code_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        working_tree_status=status,started_at=datetime.now(timezone.utc).isoformat(),
        command=sys.argv,python=sys.version,numpy=np.__version__,workers=1,numeric_threads=1,gpu=False,
        online_training='none',fit_method='float64 SVD rcond1e-10; OLS and fixed ridge .001',completed_trajectories=0)
    write(args.output/'manifest.json',manifest)
    try:
        cfg=replace(ExperimentConfig(),num_episodes=300,reward_mode='dense',learning_rate=.001,
                    make_plots=False,copy_best_qtable=False)
        cfg.validate()
        write(args.output/'config.json',asdict(cfg))
        net=load_network_from_csv(cfg.links_path,cfg.num_stops,cfg.links_are_bidirectional,cfg.input_stop_id_base)
        od=load_od_matrices(cfg.od_dir,cfg.od_filename_pattern,cfg.num_hours,cfg.num_stops,cfg.od_file_numbers())
        reference=STUDY/'evidence/S3-reference60-run01/search-hours.jsonl'
        routes=json.loads(reference.read_text().splitlines()[0])['routes']
        selected=routes[:2]
        assert selected[0]!=selected[1]
        def single(route):
            return [Action(ADD_STOP,s) for s in route]+[Action(END_ROUTE)]+[Action(FINISH_PLAN)]*24
        traces=dict(empty=[Action(FINISH_PLAN)]*24,train_route=single(selected[0]),heldout_route=single(selected[1]))
        prior=STUDY/'evidence/S6-linear-stability-run01/EXP-004-S6-L-seed2034-run01'
        files=[reference,*[prior/f'weights-{n:03d}.json' for n in (0,100,300)],
               cfg.links_path,*sorted(cfg.od_dir.glob('*.csv')),*sorted((ROOT/'transit_rl').rglob('*.py'))]
        write(args.output/'source-input-sha256.json',{p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in files})
        (args.output/'requirements-lock.txt').write_text(subprocess.check_output([sys.executable,'-m','pip','freeze'],text=True))
        models={}
        for n in (0,100,300):
            agent=LinearQAgent(cfg,0,net)
            snapshot=json.loads((prior/f'weights-{n:03d}.json').read_text())
            assert snapshot['feature_names']==list(FEATURE_NAMES)
            agent.weights[:]=snapshot['weights']
            models[n]=agent
        before={n:a.weights.tobytes() for n,a in models.items()}
        all_rows=[]
        with keep_awake() as awake:
            manifest['sleep_prevention']=awake
            for name,actions in traces.items():
                env=RemainingActionEnvironment(net,od,cfg)
                env.reset()
                records=[]
                for i,action in enumerate(actions):
                    key=env.learning_key(env.state)
                    assert action in env.valid_actions()
                    x=design_vector(models[0],key,action)
                    result=env.step(action)
                    audits={}
                    for n,agent in models.items():
                        q=agent.q_value(key,action)
                        next_max=0.0 if result.done else agent.max_q(env.learning_key(result.next_state),env.valid_actions())
                        target=result.reward+cfg.discount_factor*next_max
                        # Algebraic check of the actual normalized semi-gradient update.
                        phi=agent.encoder.features(key,action)
                        proposed=agent.weights[agent.encoder.type_index[action.type]]+agent.alpha*(target-q)*phi
                        predicted_after=float(np.dot(proposed,phi))
                        assert np.isclose(predicted_after,q+agent.alpha*(target-q),atol=1e-12)
                        audits[str(n)]=dict(q=q,next_max=next_max,bootstrap_target=target,
                            td_error=target-q,one_update_prediction=predicted_after)
                    records.append(dict(index=i,trajectory=name,split='heldout' if name=='heldout_route' else 'train',
                        hour=key[0],remaining_actions=key[-1],action=action._asdict(),
                        raw_state_action_sha256=hashlib.sha256(repr((key,action)).encode()).hexdigest(),
                        feature_sha256=hashlib.sha256(x.tobytes()).hexdigest(),features=x.tolist(),
                        reward=result.reward,done=result.done,frozen_audit=audits))
                    working,free=memory_mb()
                    if time.perf_counter()-start>180 or (working and working>1536) or (free and free<4096):
                        raise RuntimeError('Registered S8 resource guard')
                assert env.done
                for row,target in zip(records,returns_to_go([r['reward'] for r in records])):
                    row['return_target']=target
                daily=summarise_day(env.hourly_records)
                assert np.isclose(sum(r['reward'] for r in records),daily['daily_plan_reward'])
                write(args.output/f'{name}.json',dict(route=selected[1 if name=='heldout_route' else 0] if name!='empty' else [],
                    daily=daily,hours=env.diagnostics,rows=records))
                all_rows.extend(records)
                manifest['completed_trajectories']+=1
            fitted={}
            for subset in ('train','empty','train_route','heldout_route'):
                rows=[r for r in all_rows if r['split']=='train'] if subset=='train' else [r for r in all_rows if r['trajectory']==subset]
                matrix=np.asarray([r['features'] for r in rows]); targets=np.asarray([r['return_target'] for r in rows])
                fitted[subset]={name:fit_linear(matrix,targets,ridge) for name,ridge in (('ols',0.0),('ridge',.001))}
            write(args.output/'fits.json',fitted)
            assert all(a.weights.tobytes()==before[n] and not a.q and not a.visits for n,a in models.items())
            manifest['frozen_models_unchanged']=True
        manifest.update(status='completed',sleep_scope_exited=True)
    except BaseException as error:
        manifest.update(status='failed',error=repr(error))
        raise
    finally:
        manifest.update(finished_at=datetime.now(timezone.utc).isoformat(),elapsed_seconds=time.perf_counter()-start)
        write(args.output/'manifest.json',manifest)


if __name__=='__main__':
    main()
