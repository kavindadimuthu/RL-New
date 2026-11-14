"""Validate/archive EXP-002 and regenerate tables without training.

Run with --input <scratch-output>, or --input <study>/evidence --verify-only.
"""
import argparse
import csv
from datetime import datetime
import hashlib
import json
import math
from pathlib import Path
import shutil
import statistics as stats

STUDY = Path(__file__).resolve().parents[1]
MODES = ['A_dense', 'B_committed', 'C_hour_end']
SEEDS = [2027, 2028, 2029]
EVAL_SEEDS = [7000, 7001, 7002]


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def dates(value):
    start, end = [datetime.fromisoformat(value[key]) for key in ('started_at','finished_at')]
    assert start.tzinfo and end.tzinfo and end >= start


def validate(root):
    manifest = read(root/'manifest.json')
    assert manifest['study_id']=='EXP-002' and manifest['status']=='completed'
    assert manifest['git_status']=='' and len(manifest['commit'])==40
    dates(manifest)
    assert (root/'requirements-lock.txt').read_text().splitlines()==(STUDY/'requirements-lock.txt').read_text().splitlines()
    assert read(root/'machine.json')['cpu']
    for relative, expected in manifest['source_and_input_sha256'].items():
        assert digest(root/'snapshot'/relative)==expected, relative
    runs=read(root/'results.json')
    assert len(runs)==21 and len({r['job']['run_id'] for r in runs})==21
    expected={(phase,mode,seed) for phase in ['equal_episodes','equal_time'] for mode in MODES for seed in SEEDS}
    expected.update({('timing',mode,2027) for mode in MODES})
    assert {(r['job']['phase'],r['job']['mode'],r['job']['seed']) for r in runs}==expected
    for run in runs:
        job=run['job']
        folder=root/job['phase']/job['run_id']
        meta=read(folder/'manifest.json')
        assert meta['status']==run['stop_reason']=='completed'
        assert meta['code_commit']==job['code_commit']==manifest['commit']
        assert meta['run_id']==job['run_id'] and meta['working_tree_dirty'] is False
        assert meta['large_artifacts']=={'q_table':'not_saved','checkpoint':'not_saved'}
        assert (folder/meta['environment_reference']).is_file()
        assert (folder/meta['hardware_reference']).is_file()
        dates(meta)
        config=read(folder/'config.json')
        assert config['reward_mode']=={'A_dense':'dense','B_committed':'committed','C_hour_end':'terminal'}[job['mode']]
        assert config['discount_factor']==1 and job['evaluation_seeds']==EVAL_SEEDS
        rows=[json.loads(line) for line in (folder/'episodes.jsonl').read_text().splitlines()]
        assert len(rows)==run['episodes']
        assert [row['episode'] for row in rows]==list(range(1,len(rows)+1))
        for row in rows:
            assert datetime.fromisoformat(row['timestamp']).tzinfo
            assert all(math.isfinite(row[key]) for key in ['reward','training_seconds','episode_seconds','epsilon'])
        assert math.isclose(sum(row['episode_seconds'] for row in rows),run['training_seconds'],abs_tol=1e-7)
        assert sum(row['steps'] for row in rows)==run['steps']
        assert sum(row['cache_misses'] for row in rows)==run['assignment_cache_misses']
        if job['phase']=='timing':
            assert len(rows)==100 and not run['evaluations']
        else:
            assert len(run['evaluations'])==3
            if job['phase']=='equal_episodes':
                assert len(rows)==300 and [p['episode'] for p in run['evaluations']]==[100,200,300]
            else:
                assert run['training_seconds']>=120
                assert run['training_seconds']<120+rows[-1]['episode_seconds']+1e-7
                assert all(p['training_seconds']>=threshold for p,threshold in zip(run['evaluations'],[40,80,120]))
            assert math.isclose(rows[-1]['epsilon'],.05,abs_tol=1e-12)
            for point in run['evaluations']:
                dates(point)
                assert [v['seed'] for v in point['evaluations']]==EVAL_SEEDS
                assert all(math.isclose(v['reward'],v['daily_plan_reward'],abs_tol=1e-8) for v in point['evaluations'])
            assert math.isclose(sum(p['evaluation_seconds'] for p in run['evaluations']),run['evaluation_seconds'],abs_tol=1e-7)
        run['_max_memory_mib']=max(row['memory_mb'] for row in rows)
    baseline=read(root/'untrained_evaluation.json')
    dates(baseline)
    assert baseline['code_commit']==manifest['commit'] and baseline['status']=='completed'
    return manifest,runs,baseline


def summarize(runs):
    per_seed=[]
    checkpoints=[]
    keys=['reward','served_demand_ratio','unseen_fraction','average_fleet_used','steps',
          'total_operator_penalty','total_transition_component','forced_hour_finishes']
    for run in runs:
        job=run['job']
        base=dict(phase=job['phase'],mode=job['mode'],seed=job['seed'],run_id=job['run_id'],
                  training_seconds=run['training_seconds'],cpu_seconds=run['training_cpu_seconds'],
                  evaluation_seconds=run['evaluation_seconds'],episodes=run['episodes'],
                  training_steps=run['steps'],assignments=run['assignment_cache_misses'],
                  evaluation_requests=run['evaluation_requests'],max_memory_mib=run['_max_memory_mib'])
        for i,point in enumerate(run['evaluations']):
            checkpoints.append(dict(phase=job['phase'],mode=job['mode'],seed=job['seed'],checkpoint=i+1,
                episode=point['episode'],training_seconds=point['training_seconds'],
                **{key:stats.mean(v[key] for v in point['evaluations']) for key in keys}))
        if run['evaluations']:
            base.update({key:stats.mean(v[key] for v in run['evaluations'][-1]['evaluations']) for key in keys})
        per_seed.append(base)
    aggregated=[]
    paired=[]
    for phase in ['timing','equal_episodes','equal_time']:
        for mode in MODES:
            group=[r for r in per_seed if r['phase']==phase and r['mode']==mode]
            fields=['training_seconds','cpu_seconds','evaluation_seconds','episodes','training_steps','assignments','evaluation_requests']
            if phase!='timing':
                fields+=keys
            item=dict(phase=phase,mode=mode,independent_training_seeds=len(group),
                      **{key:stats.mean(r[key] for r in group) for key in fields},
                      max_memory_mib=max(r['max_memory_mib'] for r in group))
            if phase!='timing':
                item.update(reward_std=stats.stdev(r['reward'] for r in group),
                            reward_min=min(r['reward'] for r in group),reward_max=max(r['reward'] for r in group))
                if mode!='A_dense':
                    for row in group:
                        a=next(r for r in per_seed if r['phase']==phase and r['mode']=='A_dense' and r['seed']==row['seed'])
                        paired.append(dict(phase=phase,mode=mode,seed=row['seed'],
                                           reward_difference_vs_A=row['reward']-a['reward']))
            aggregated.append(item)
    return dict(aggregated=aggregated,per_seed=per_seed,paired=paired,checkpoints=checkpoints)


def emit(root,manifest,runs,baseline):
    summary=summarize(runs)
    summary['code_commit']=manifest['commit']
    summary['untrained_reward']=stats.mean(v['reward'] for v in baseline['evaluations'])
    destination=STUDY/'summaries'
    destination.mkdir(exist_ok=True)
    (destination/'comparison.json').write_text(json.dumps(summary,indent=2)+'\n',encoding='utf-8')
    for phase in ['timing','equal_episodes','equal_time']:
        rows=[r for r in summary['aggregated'] if r['phase']==phase]
        with (destination/f'{phase}.csv').open('w',newline='',encoding='utf-8') as fh:
            writer=csv.DictWriter(fh,fieldnames=list(rows[0]))
            writer.writeheader();writer.writerows(rows)
    lines=['# EXP-002 results: prospective evaluation-frequency repeat','',
           f"Execution code commit: `{manifest['commit']}`. Status: all 21 trained runs and the prespecified untrained diagnostic completed. All verification assertions passed.",'',
           'Legacy findings were known. These observations are a separate repeat using training seeds 2027–2029 and evaluation seeds 7000–7002; no legacy results were pooled. Each learning-stage mean averages evaluation seeds within models, then the three independent trained models.','',
           '| Stage | Method | Training seconds | Episodes | Final daily reward | Demand served | Unseen evaluation states |',
           '|---|---|---:|---:|---:|---:|---:|']
    for r in summary['aggregated']:
        reward=f"{r['reward']:.4f}" if 'reward' in r else 'not assessed'
        served=f"{100*r['served_demand_ratio']:.2f}%" if 'reward' in r else '—'
        unseen=f"{100*r['unseen_fraction']:.2f}%" if 'reward' in r else '—'
        lines.append(f"| {r['phase']} | {r['mode']} | {r['training_seconds']:.2f} | {r['episodes']:.1f} | {reward} | {served} | {unseen} |")
    lines+=['','## Independent seed results','','| Stage | Method | Seed | Final daily reward |','|---|---|---:|---:|']
    for r in summary['per_seed']:
        if 'reward' in r:
            lines.append(f"| {r['phase']} | {r['mode']} | {r['seed']} | {r['reward']:.4f} |")
    lines+=['','## Interpretation and limits','',f"The prespecified untrained reference averaged {summary['untrained_reward']:.4f}. It is a no-learning diagnostic, not an additional independent training sample.",'']
    for phase in ['equal_episodes','equal_time']:
        group=[r for r in summary['aggregated'] if r['phase']==phase]
        winner=max(group,key=lambda r:r['reward'])
        lines.append(f"Highest observed mean reward in {phase}: **{winner['mode']}**, {winner['reward']:.4f}. This is a short-budget observation from three training seeds, not a significance or convergence claim.")
    lines+=['','Interpret runtime alongside service quality and state coverage. High unseen-state fractions mean most evaluation states have no learned exact-state action ranking. Low unseen fractions on a very short, low-service trajectory do not imply broad coverage. Speed alone does not establish an improvement. The stages intentionally use different exploration schedules, so comparisons between stages are not isolated schedule-frequency effects.','',
            'All demand is the same fixed problem used in training, not a held-out generalization test. CPU/elapsed timings depend on laptop load and thermal scheduling. Time limits stop at complete-episode boundaries; exact overshoot is in run metrics. Rerunning time-scheduled jobs may produce different episode counts and models.','',
            '## Evidence, artifacts and backup','',
            'Original manifests, configuration, UTC timestamps, environment locks, machine data, source/input hashes, episode logs and evaluation checkpoints are retained under evidence/. SHA-256 inventory is in archive_checksums.json. No final Q-table/checkpoint or PDF was generated. Analysis regeneration requires no training.','',
            'Evidence is committed locally after execution; the evidence commit is distinct from the execution commit above. Off-machine backup has not been verified and no remote push/publication is implied. Retain scratch files until backup is verified.','',
            '## Deviations and verification','',
            'No automatic exclusions or reruns are performed by this analysis. Any failed/incomplete run prevents a normal completed-study report. Validation checks identity, status, expected budgets/counts, timestamps, common evaluation seeds, numerical finiteness, daily objective consistency, timing totals, provenance hashes, and archive copy integrity. Review verification.md for test/preflight outcomes and any subsequent deviations.']
    (STUDY/'report.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    return summary


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input',type=Path,required=True)
    parser.add_argument('--verify-only',action='store_true')
    args=parser.parse_args()
    source=args.input.resolve()
    manifest,runs,baseline=validate(source)
    target=STUDY/'evidence'
    if not args.verify_only:
        if target.exists():
            raise FileExistsError('Evidence archive exists; use --verify-only to regenerate summaries')
        shutil.copytree(source,target)
        hashes={str(path.relative_to(source)):digest(path) for path in source.rglob('*') if path.is_file()}
        assert all(digest(target/key)==value for key,value in hashes.items())
        (STUDY/'archive_checksums.json').write_text(json.dumps(hashes,indent=2)+'\n',encoding='utf-8')
    else:
        hashes=read(STUDY/'archive_checksums.json')
        assert all(digest(source/key)==value for key,value in hashes.items())
    summary=emit(source,manifest,runs,baseline)
    print(json.dumps(summary['aggregated'],indent=2))
    print('Validated 21 runs; numerical report regenerated without training.')


if __name__=='__main__':
    main()
