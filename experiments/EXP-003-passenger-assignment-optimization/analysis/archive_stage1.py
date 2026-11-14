"""Archive/verify the stage-1 baseline evidence; no training or speed trial."""
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
from transit_rl.experiment.assignment_profile import (
    ExperimentConfig, load_network_from_csv, load_od_matrices, reference_class,
    prepare_assigner, replay, REPEAT_ORDER, summarize,
)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate(root):
    manifest=json.loads((root/'manifest.json').read_text())
    assert manifest['status']=='completed' and manifest['git_status']==''
    assert manifest['run_id']=='EXP-003-S1-baseline-profile-run01'
    assert manifest['sleep_request']['requested'] and manifest['sleep_request_restored']
    assert manifest['seeds']==[2030,2031]
    assert manifest['repetition_order']==REPEAT_ORDER
    assert digest(root/'workload.json')==manifest['workload_sha256']
    for relative,expected in manifest['input_and_source_sha256'].items():
        # Future candidates may change production code. The baseline replay
        # uses the preserved original, not whatever candidate is checked out.
        path=STUDY/'reference/passenger_assignment.py' if Path(relative).as_posix()=='transit_rl/environment/passenger_assignment.py' else ROOT/relative
        assert digest(path)==expected,relative
    trace=json.loads((root/'workload.json').read_text())
    assert len(trace['queries'])==manifest['assignment_requests']
    assert len(trace['miss_sample'])==manifest['miss_sample_size']
    assert {(row['seed'],row['episode']) for row in trace['episodes']}=={(s,e) for s in [2030,2031] for e in [1,2]}
    assert sum(row['steps'] for row in trace['episodes'])==len(trace['actions'])
    rows=json.loads((root/'baseline_measurements.json').read_text())
    assert [(r['repeat'],r['scenario']) for r in rows]==[(i,s) for i,order in enumerate(REPEAT_ORDER,1) for s in order]
    for row in rows:
        assert row['elapsed_seconds']>0 and row['cpu_seconds']>=0
        assert row['calls']==row['cache_hits']+row['cache_misses']
        if row['scenario']=='warm_hits':
            assert row['cache_misses']==0 and row['calls']==4*manifest['miss_sample_size']
        if row['scenario']=='miss_stream':
            assert row['cache_hits']==0 and row['calls']==manifest['miss_sample_size']
    values=manifest['config'].copy()
    values['data_dir']=ROOT/'transit_rl/data/input'
    values['results_dir']=ROOT/'transit_rl/results'
    values['initial_service_plan']=tuple(values['initial_service_plan'])
    cfg=ExperimentConfig(**values)
    cfg.validate()
    network=load_network_from_csv(cfg.links_path,cfg.num_stops,cfg.links_are_bidirectional,cfg.input_stop_id_base)
    od=load_od_matrices(cfg.od_dir,cfg.od_filename_pattern,cfg.num_hours,cfg.num_stops,cfg.od_file_numbers())
    verified=0
    for scenario in REPEAT_ORDER[0]:
        assigner,queries,plans=prepare_assigner(scenario,cfg,network,od,reference_class(),trace,trace['miss_sample'])
        replay(assigner,queries,plans,verify=True)
        verified+=len(queries)
    return dict(verified_at_utc=datetime.now(timezone.utc).isoformat(),
                validation_type='post_run_archive_and_replay',execution_commit=manifest['code_commit'],
                replay_output_hashes_verified=verified,workload_hash_verified=True,
                input_and_source_hashes_verified=True,sleep_request_restored=True,
                timing_qualified=manifest['timing_qualified'],performance_improvement_claim=False)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input',type=Path,required=True)
    parser.add_argument('--verify-only',action='store_true')
    args=parser.parse_args()
    source=args.input.resolve()
    audit=validate(source)
    inventory={str(p.relative_to(source)):digest(p) for p in source.rglob('*') if p.is_file()}
    archive=STUDY/'evidence/stage1'
    if args.verify_only:
        expected=json.loads((STUDY/'stage1-checksums.json').read_text())
        assert expected==inventory
    else:
        if archive.exists():
            raise FileExistsError('Archive exists; use --verify-only')
        archive.parent.mkdir(exist_ok=True)
        shutil.copytree(source,archive)
        assert all(digest(archive/path)==sha for path,sha in inventory.items())
        (STUDY/'stage1-checksums.json').write_text(json.dumps(inventory,indent=2)+'\n')
    report=source/'REPORT.md'
    before=digest(report)
    summarize(source)
    assert digest(report)==before,'Derived report did not regenerate identically'
    audit['report_regenerated_identically']=True
    (STUDY/'stage1-verification.json').write_text(json.dumps(audit,indent=2)+'\n')
    print(json.dumps(audit,indent=2))


if __name__=='__main__':
    main()
