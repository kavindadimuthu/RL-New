"""S8 preregistered descriptive fit residuals, overlap and bootstrap checks."""
import hashlib
import json
import math
from pathlib import Path
import sys
import numpy as np

STUDY=Path(__file__).resolve().parents[1]


def errors(rows,weights):
    if not rows:
        return dict(count=0,rmse=None,maximum_absolute_error=None)
    matrix=np.asarray([r['features'] for r in rows]); targets=np.asarray([r['return_target'] for r in rows])
    residual=matrix@np.asarray(weights)-targets
    return dict(count=len(rows),rmse=float(np.sqrt(np.mean(residual**2))),maximum_absolute_error=float(np.abs(residual).max()))


def collisions(rows,field):
    groups={}
    for r in rows:
        groups.setdefault(r[field],[]).append(r['return_target'])
    conflicts=[max(v)-min(v) for v in groups.values() if max(v)-min(v)>1e-8]
    return dict(unique=len(groups),conflicting_groups=len(conflicts),maximum_target_range=max(conflicts,default=0))


def analyse(directory):
    load=lambda p:json.loads(p.read_text())
    manifest=load(directory/'manifest.json')
    checksums={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(directory.iterdir()) if p.is_file()}
    if manifest['status']!='completed':
        return dict(status='incomplete',manifest=manifest,checksums=checksums)
    assert manifest['completed_trajectories']==3 and manifest['frozen_models_unchanged'] and manifest['sleep_scope_exited']
    assert not manifest['working_tree_status'].strip()
    cfg=load(directory/'config.json')
    oldcfg=load(STUDY/'evidence/S6-linear-stability-run01/EXP-004-S6-L-seed2034-run01/config.json')
    ignored={'data_dir','results_dir'}
    assert {k:v for k,v in cfg.items() if k not in ignored}=={k:v for k,v in oldcfg.items() if k not in ignored}
    inputs=load(directory/'source-input-sha256.json')
    oldinputs=load(STUDY/'evidence/S6-linear-stability-run01/EXP-004-S6-L-seed2034-run01/source-input-sha256.json')
    assert {k:v for k,v in inputs.items() if k.endswith('.csv')}=={k:v for k,v in oldinputs.items() if k.endswith('.csv')}
    all_rows=[]; trajectories=[]
    for name in ('empty','train_route','heldout_route'):
        value=load(directory/f'{name}.json'); rows=value['rows']; hours=value['hours']
        assert len(hours)==24 and [h['hour'] for h in hours]==list(range(1,25))
        assert rows[-1]['done'] and sum(r['done'] for r in rows)==1
        assert sum(h['actions'] for h in hours)==len(rows)
        assert all(h['actions']<=60 and h['fleet_used']+h['fleet_remaining']==99 for h in hours)
        assert math.isclose(sum(h['served_passengers'] for h in hours),value['daily']['served_passengers'],abs_tol=1e-8)
        assert all(math.isclose(h['served_passengers']+h['no_eligible_path_unserved']+h['capacity_constrained_unserved'],h['total_demand'],abs_tol=1e-8) for h in hours)
        total=0
        for row in reversed(rows):
            total+=row['reward']
            assert math.isclose(total,row['return_target'],abs_tol=1e-9)
            assert len(row['features'])==256 and np.isclose(np.linalg.norm(row['features']),1)
            for audit in row['frozen_audit'].values():
                assert math.isclose(audit['bootstrap_target'],row['reward']+audit['next_max'],abs_tol=1e-12)
                assert math.isclose(audit['td_error'],audit['bootstrap_target']-audit['q'],abs_tol=1e-12)
                assert math.isclose(audit['one_update_prediction'],audit['q']+.001*audit['td_error'],abs_tol=1e-12)
                if row['done']:
                    assert audit['next_max']==0
        assert math.isclose(total,value['daily']['daily_plan_reward'],abs_tol=1e-9)
        if name in ('empty','train_route'):
            prior=load(STUDY/f'evidence/S7-stopping-run01/{"empty" if name=="empty" else "first_reference_route"}.json')
            assert prior['daily']==value['daily']
        trajectories.append(dict(name=name,route=value['route'],steps=len(rows),served_ratio=value['daily']['served_demand_ratio'],reward=total))
        all_rows.extend(rows)
    train=[r for r in all_rows if r['split']=='train']; held=[r for r in all_rows if r['split']=='heldout']
    train_keys={r['raw_state_action_sha256'] for r in train}; train_features={r['feature_sha256'] for r in train}
    disjoint=[r for r in held if r['raw_state_action_sha256'] not in train_keys]
    novel_features=[r for r in held if r['feature_sha256'] not in train_features]
    fits=load(directory/'fits.json'); summaries={}
    for subset,models in fits.items():
        selected=train if subset=='train' else [r for r in all_rows if r['trajectory']==subset]
        summaries[subset]={}
        matrix=np.asarray([r['features'] for r in selected]); targets=np.asarray([r['return_target'] for r in selected])
        for method,fit in models.items():
            weights=np.asarray(fit['weights'])
            assert weights.shape==(256,) and np.all(np.isfinite(weights))
            # Check normal equations independently, including the registered regularizer.
            assert np.linalg.norm(matrix.T@(matrix@weights-targets)+fit['ridge']*weights)<1e-5
            summaries[subset][method]=dict(training=errors(selected,weights),heldout=errors(held,weights),
                heldout_raw_disjoint=errors(disjoint,weights),heldout_feature_disjoint=errors(novel_features,weights),
                rank=fit['rank'],weight_norm=fit['norm'])
    initial=[r for r in all_rows if r['index']==0]
    probes=[]
    for r in initial:
        x=np.asarray(r['features'])
        probes.append(dict(trajectory=r['trajectory'],action=r['action'],return_target=r['return_target'],
            frozen=r['frozen_audit'],fitted_train={m:float(x@np.asarray(f['weights'])) for m,f in fits['train'].items()}))
    return dict(status='verified',execution_commit=manifest['code_commit'],elapsed_seconds=manifest['elapsed_seconds'],
        hourly_records_verified=72,trajectories=trajectories,fit_results=summaries,initial_probes=probes,
        train_raw_conflicts=collisions(train,'raw_state_action_sha256'),train_feature_conflicts=collisions(train,'feature_sha256'),
        combined_raw_conflicts=collisions(all_rows,'raw_state_action_sha256'),combined_feature_conflicts=collisions(all_rows,'feature_sha256'),
        train_count=len(train),heldout_count=len(held),heldout_raw_disjoint_count=len(disjoint),heldout_feature_disjoint_count=len(novel_features),
        zero_predictor_train=errors(train,np.zeros(256)),checksums=checksums,
        limitation='Fixed-continuation labels differ across controllers; overlapping prefixes are not independent unseen examples. No online policy or optimal Q learned. Oracle self-fits use heldout labels and are in-sample capacity diagnostics only.')


if __name__=='__main__':
    value=analyse(Path(sys.argv[1]))
    with Path(sys.argv[2]).open('x') as stream:
        json.dump(value,stream,indent=2)
        stream.write('\n')
