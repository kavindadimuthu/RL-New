"""Registered S7 fixed-continuation validation and descriptive probes."""
import hashlib
import json
import math
from pathlib import Path
import sys

STUDY=Path(__file__).resolve().parents[1]


def analyse(directory):
    load=lambda p:json.loads(p.read_text())
    manifest=load(directory/'manifest.json')
    checksums={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(directory.iterdir()) if p.is_file()}
    if manifest['status']!='completed':
        return dict(status='incomplete',manifest=manifest,checksums=checksums)
    assert manifest['completed_trajectories']==3 and manifest['model_weights_unchanged'] and manifest['sleep_scope_exited']
    assert not manifest['working_tree_status'].strip()
    summaries=[]
    for name in ('empty','first_reference_route','full_reference'):
        value=load(directory/f'{name}.json')
        transitions=value['transitions']
        assert transitions[-1]['done'] and sum(t['done'] for t in transitions)==1
        hours=value['hours']
        assert len(hours)==24 and [h['hour'] for h in hours]==list(range(1,25))
        assert sum(h['actions'] for h in hours)==len(transitions)
        assert math.isclose(sum(h['served_passengers'] for h in hours),value['daily']['served_passengers'],abs_tol=1e-8)
        for h in hours:
            assert h['actions']==sum(h['action_counts'].values())
            assert h['fleet_used']+h['fleet_remaining']==99
            assert math.isclose(h['served_passengers']+h['no_eligible_path_unserved']+h['capacity_constrained_unserved'],h['total_demand'],abs_tol=1e-8)
            assert all(math.isfinite(h[k]) and h[k]>=0 for k in ('served_passengers','no_eligible_path_unserved','capacity_constrained_unserved'))
            assert all(0<=x<=1+1e-8 for x in h['route_peak_capacity_ratios'])
        assert all(h['actions']<=60 for h in value['hours'])
        total=0
        probes=[]
        for t in reversed(transitions):
            total+=t['reward']
            assert math.isclose(total,t['fixed_continuation_return'],abs_tol=1e-9)
            assert all(math.isfinite(v['q']) for p in t['predictions'].values() for v in p['values'])
        assert math.isclose(total,value['daily']['daily_plan_reward'],abs_tol=1e-9)
        for t in transitions:
            if t['stop_rest_of_day'] is not None:
                probes.append(dict(index=t['index'],hour=t['hour'],action=t['action'],
                    fixed_continuation_return=t['fixed_continuation_return'],stop_rest_of_day=t['stop_rest_of_day']['remaining_return'],
                    predictions={n:dict(chosen=p['chosen'],finish=next(v['q'] for v in p['values'] if v['action']['type']=='FINISH_PLAN'),best=p['best']) for n,p in t['predictions'].items()}))
        if name=='full_reference':
            expected=load(STUDY/'evidence/S3-reference60-run01/service-plan.json')['daily']
            assert value['daily']==expected
        if name=='empty':
            old=load(STUDY/'evidence/S6-linear-stability-run01/EXP-004-S6-L-seed2034-run01/evaluation-300.json')
            assert all(value['daily']==v['daily'] for v in old['evaluations'])
        summaries.append(dict(trajectory=name,steps=len(transitions),served_ratio=value['daily']['served_demand_ratio'],reward=total,minimum_immediate_reward=min(t['reward'] for t in transitions),maximum_immediate_reward=max(t['reward'] for t in transitions),probes=probes))
    return dict(status='verified',execution_commit=manifest['code_commit'],elapsed_seconds=manifest['elapsed_seconds'],hourly_records_verified=72,trajectories=summaries,checksums=checksums,limitation='Fixed-continuation returns are not exact optimal action values; no causal attribution or independent quality comparison.')


if __name__=='__main__':
    result=analyse(Path(sys.argv[1]))
    with Path(sys.argv[2]).open('x') as file:
        json.dump(result,file,indent=2)
        file.write('\n')
