"""Registered S9 completion, suffix/update accounting and paired screen."""
from datetime import datetime
import gzip
import hashlib
import json
import math
from pathlib import Path
import runpy
import statistics
import sys

STUDY=Path(__file__).resolve().parents[1]


def analyse(directory):
    load=lambda p:json.loads(p.read_text())
    parent=load(directory/'study-manifest.json')
    checksums={p.relative_to(directory).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(directory.rglob('*')) if p.is_file()}
    if parent['status']!='completed':
        return dict(status='incomplete',study=parent,checksums=checksums,
            run_statuses={p.parent.name:load(p) for p in directory.glob('*/manifest.json')},
            decision='No normal final comparison; preserve incomplete wave without replacement.')
    preflight=parent['stage']=='S9P'
    episodes=25 if preflight else 300
    seeds=(2034,) if preflight else (2034,2035,2036)
    checkpoints=(0,25) if preflight else (0,100,300)
    validate=runpy.run_path(str(STUDY/'analysis/summarise_baseline.py'))['validate_hours']
    models=[];configs=[];inputs=[];count=0
    for seed in seeds:
        initial=[];first=[]
        for method in ('T','M'):
            run=directory/f'EXP-004-{parent["stage"]}-{method}-seed{seed}-run01'
            manifest=load(run/'manifest.json')
            assert manifest['status']=='completed' and manifest['episodes_completed']==episodes
            assert manifest['return_method']==method and manifest['sleep_scope_exited']
            assert manifest['code_commit']==parent['code_commit'] and not manifest['working_tree_status'].strip()
            assert manifest['target_episodes']==episodes and manifest['checkpoints']==list(checkpoints)
            cfg=load(run/'config.json');configs.append(cfg);inputs.append(load(run/'source-input-sha256.json'))
            assert cfg['learning_rate']==.001 and cfg['discount_factor']==1 and cfg['num_episodes']==300
            metrics=[json.loads(line) for line in (run/'episodes.jsonl').read_text().splitlines()]
            assert [m['episode'] for m in metrics]==list(range(1,episodes+1))
            assert math.isclose(sum(m['elapsed_seconds'] for m in metrics),manifest['training_seconds'],abs_tol=1e-6)
            first.append({k:metrics[0][k] for k in ('reward','steps','served_demand_ratio','hourly_rewards')})
            with gzip.open(run/'training-hours.jsonl.gz','rt',encoding='utf-8') as hours, gzip.open(run/'target-audit.jsonl.gz','rt',encoding='utf-8') as audits:
                for m in metrics:
                    h=json.loads(next(hours));a=json.loads(next(audits))
                    assert h['episode']==a['episode']==m['episode']
                    validate(h['hours'],m,m['steps'],m['unseen']);count+=24
                    updates=a['updates']
                    assert len(updates)==m['steps'] and [r['step'] for r in updates]==list(range(1,m['steps']+1))
                    assert updates[-1]['done'] and sum(r['done'] for r in updates)==1
                    assert math.isclose(sum(r['reward'] for r in updates),m['reward'],abs_tol=1e-8)
                    assert math.isclose(m['reward'],sum(m['hourly_rewards']),abs_tol=1e-8)
                    assert m['empty_hours']==sum(r['route_count']==0 for r in h['hours'])
                    for hour in range(1,25):
                        assert math.isclose(sum(r['reward'] for r in updates if r['hour']==hour),m['hourly_rewards'][hour-1],abs_tol=1e-8)
                    future=0.0
                    for r in reversed(updates):
                        future+=r['reward']
                        assert all(math.isfinite(r[k]) for k in ('reward','q_at_collection','q_before_update','target','td_error'))
                        assert math.isclose(r['target']-r['q_before_update'],r['td_error'],abs_tol=1e-9)
                        if method=='M':
                            assert math.isclose(future,r['target'],abs_tol=1e-8)
                        if r['done']:
                            assert math.isclose(r['target'],r['reward'],abs_tol=1e-8)
                    assert m['minimum_update_target']==min(r['target'] for r in updates)
                    assert m['maximum_update_target']==max(r['target'] for r in updates)
                assert hours.read()=='' and audits.read()==''
            if seed==2034 and method=='T':
                old=STUDY/'evidence/S6-linear-stability-run01/EXP-004-S6-L-seed2034-run01'
                prior=[json.loads(line) for line in (old/'episodes.jsonl').read_text().splitlines()][:episodes]
                keys=('reward','steps','unseen','served_demand_ratio','q_states','q_pairs','hourly_rewards','weight_norm')
                assert all(all(a[k]==b[k] for k in keys) for a,b in zip(metrics,prior))
            summaries=[]
            for checkpoint in checkpoints:
                value=load(run/f'evaluation-{checkpoint:03d}.json')
                assert value['learner_unchanged'] and value['episode']==checkpoint
                assert [v['seed'] for v in value['evaluations']]==[7100,7101,7102]
                for v in value['evaluations']:
                    validate(v['hours'],v['daily'],v['steps'],v['unseen']);count+=24
                    assert math.isclose(v['reward'],v['daily']['daily_plan_reward'],abs_tol=1e-8)
                values=value['evaluations']
                summaries.append(dict(episode=checkpoint,
                    served_ratio=statistics.mean(v['diagnostics']['served_ratio'] for v in values),
                    reward=statistics.mean(v['reward'] for v in values),
                    empty_hours=statistics.mean(sum(h['route_count']==0 for h in v['hours']) for v in values),
                    empty_days=sum(all(h['route_count']==0 for h in v['hours']) for v in values),
                    fleet=statistics.mean(v['diagnostics']['average_fleet'] for v in values),
                    forced_finishes=statistics.mean(v['diagnostics']['forced_finishes'] for v in values)))
                snapshot=load(run/f'weights-{checkpoint:03d}.json')
                assert len(snapshot['weights'])==8 and all(len(row)==32 for row in snapshot['weights'])
                assert all(math.isfinite(w) for row in snapshot['weights'] for w in row)
                if checkpoint==0:
                    initial.append([v['daily'] for v in values])
                if seed==2034 and method=='T' and checkpoint in (0,100,300):
                    previous=load(old/f'evaluation-{checkpoint:03d}.json')
                    assert [v['daily'] for v in values]==[v['daily'] for v in previous['evaluations']]
            utc=(datetime.fromisoformat(manifest['finished_at'])-datetime.fromisoformat(manifest['started_at'])).total_seconds()
            models.append(dict(seed=seed,method=method,checkpoints=summaries,training_seconds=manifest['training_seconds'],
                process_seconds=manifest['total_elapsed_seconds'],cpu_seconds=manifest['total_cpu_seconds'],
                clock_gap_seconds=utc-manifest['total_elapsed_seconds'],maximum_recorded_working_mb=max(m['working_mb'] for m in metrics),
                final_weight_norm=metrics[-1]['weight_norm'],minimum_update_target=min(m['minimum_update_target'] for m in metrics),
                maximum_update_target=max(m['maximum_update_target'] for m in metrics)))
        assert initial[0]==initial[1] and first[0]==first[1]
    assert all(cfg==configs[0] for cfg in configs) and all(item==inputs[0] for item in inputs)
    result=dict(status='verified',preflight=preflight,execution_commit=parent['code_commit'],models=models,
                hourly_records_verified=count,parent_elapsed_seconds=parent['total_elapsed_seconds'],checksums=checksums)
    if preflight:
        result['decision']='Operational gate passed; no quality ranking or tuning from preflight.'
    else:
        paired=[]
        for seed in seeds:
            t=next(m for m in models if m['seed']==seed and m['method']=='T')['checkpoints'][-1]
            m=next(m for m in models if m['seed']==seed and m['method']=='M')['checkpoints'][-1]
            paired.append(dict(seed=seed,T=t,M=m,served_difference=m['served_ratio']-t['served_ratio'],reward_difference=m['reward']-t['reward']))
        mean=statistics.mean(p['served_difference'] for p in paired)
        reward=statistics.mean(p['reward_difference'] for p in paired)
        result.update(paired=paired,mean_served_difference=mean,mean_reward_difference=reward,
            practical_advancement_passed=mean>=.02 and min(p['served_difference'] for p in paired)>=0 and reward>=0,
            limitations=['Three training seeds; average evaluation ties within learner.','Same training demand; no heldout or convergence claim.','MC also changes update timing and policy semantics; no isolated target-only causal claim.'])
    return result


if __name__=='__main__':
    result=analyse(Path(sys.argv[1]))
    with Path(sys.argv[2]).open('x') as file:
        json.dump(result,file,indent=2);file.write('\n')
