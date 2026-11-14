"""Verify/archive C01 evidence and regenerate its tables without training."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import sys

STUDY=Path(__file__).resolve().parents[1]
ROOT=STUDY.parents[1]
sys.path.insert(0,str(ROOT))
from transit_rl.experiment.assignment_c01_trial import summarize


def read(path):
    return json.loads(path.read_text())


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def dates(record):
    start,end=[datetime.fromisoformat(record[key]) for key in ['started_at','finished_at']]
    assert start.tzinfo and end.tzinfo and end>=start


def validate(root):
    meta=read(root/'manifest.json')
    assert meta['status']=='completed' and meta['git_status']==''
    assert meta['run_id']=='EXP-003-C01-paired-run01'
    assert meta['sleep_request']['requested'] and meta['sleep_request_restored']
    dates(meta)
    assert meta['workload_sha256']==digest(STUDY/'evidence/stage1/workload.json')
    verification=read(root/'verification.json')
    assert verification['status']=='passed' and verification['tolerance']=='none'
    assert verification['fixture_comparisons']==67
    assert verification['real_output_hashes_verified']==6119
    pairs=verification['training_seed_episodes']
    assert {(p['seed'],p['episode']) for p in pairs}=={(s,e) for s in [2032,2033] for e in [1,2,3]}
    assert all(p['q_visits_rng_equal'] and len(p['action_reward_sha256'])==64 for p in pairs)
    rows=read(root/'measurements.json')
    expected=[]
    for scenario in ['miss_stream','training_stream','warm_hits']:
        for repeat in range(1,6):
            for backend in (['baseline','candidate'] if repeat%2 else ['candidate','baseline']):
                expected.append((scenario,repeat,backend))
    assert [(r['scenario'],r['repeat'],r['backend']) for r in rows]==expected
    assert len({r['pid'] for r in rows})==30
    for row in rows:
        dates(row)
        assert row['workload_sha256']==meta['workload_sha256']
        assert row['calls']==row['cache_hits']+row['cache_misses']
        assert row['elapsed_seconds']>0 and row['peak_worker_memory_mib']<=1536
        if row['scenario']=='miss_stream':
            assert row['cache_misses']==row['calls']==512
        if row['scenario']=='warm_hits':
            assert row['cache_hits']==row['calls']==2048
    return meta


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input',type=Path,required=True)
    parser.add_argument('--verify-only',action='store_true')
    args=parser.parse_args()
    source=args.input.resolve()
    meta=validate(source)
    archive=STUDY/'evidence/C01-paired-run01'
    if not args.verify_only:
        if archive.exists():
            raise FileExistsError('Archive already exists')
        candidate=ROOT/'transit_rl/experiment/assignment_candidate_c01.py'
        assert digest(candidate)==meta['candidate_sha256']
        shutil.copytree(source,archive)
        shutil.copyfile(candidate,archive/'candidate_source.py')
        hashes={str(p.relative_to(archive)):digest(p) for p in archive.rglob('*') if p.is_file()}
        assert all(digest(archive/p.relative_to(source))==digest(p) for p in source.rglob('*') if p.is_file())
        (STUDY/'C01-checksums.json').write_text(json.dumps(hashes,indent=2)+'\n')
    else:
        hashes=read(STUDY/'C01-checksums.json')
        assert all(digest(source/key)==value for key,value in hashes.items())
        assert digest(source/'candidate_source.py')==meta['candidate_sha256']
        archive=source
    before={name:digest(archive/name) for name in ['comparison.json','REPORT.md']}
    comparison=summarize(archive)
    assert all(digest(archive/name)==value for name,value in before.items())
    checks=dict(verified_at_utc=datetime.now(timezone.utc).isoformat(),execution_commit=meta['execution_commit'],
                exact_archive_hashes_verified=True,source_snapshot_matches_recorded_hash=True,
                completed_timed_blocks=30,fresh_worker_processes=30,strict_real_replay_outputs=6119,
                matching_seed_episode_pairs=6,report_and_comparison_regenerated_identically=True,
                timing_qualified=meta['timing_qualified'],advance_to_training_speed_trial=comparison['advance_to_training_speed_trial'],
                primary_analysis_version='committed before timing',archive_validator_version='post-execution verification')
    (STUDY/'C01-verification.json').write_text(json.dumps(checks,indent=2)+'\n')
    print(json.dumps(checks,indent=2))


if __name__=='__main__':
    main()
