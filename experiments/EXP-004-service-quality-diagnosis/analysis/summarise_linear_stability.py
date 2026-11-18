"""Registered S6 single-seed stability accounting; no superiority test."""
import gzip
import hashlib
import json
import math
from pathlib import Path
import runpy
import statistics
import sys

STUDY = Path(__file__).resolve().parents[1]


def analyse(run):
    load = lambda p: json.loads(p.read_text())
    manifest = load(run / 'manifest.json')
    assert manifest['stage'] == 'S6-linear-stability'
    assert not manifest['working_tree_status'].strip()
    cfg = load(run / 'config.json')
    old = STUDY / 'evidence/S5-function-approx-run01/EXP-004-S5-L-seed2034-run01'
    prior = load(old / 'config.json')
    assert cfg['learning_rate'] == .001 and prior['learning_rate'] == .1
    assert {k:v for k,v in cfg.items() if k != 'learning_rate'} == {k:v for k,v in prior.items() if k != 'learning_rate'}
    inputs = load(run / 'source-input-sha256.json')
    old_inputs = load(old / 'source-input-sha256.json')
    assert {k:v for k,v in inputs.items() if k.endswith('.csv')} == {k:v for k,v in old_inputs.items() if k.endswith('.csv')}
    metrics = [json.loads(s) for s in (run / 'episodes.jsonl').read_text().splitlines()]
    assert [m['episode'] for m in metrics] == list(range(1, manifest['episodes_completed']+1))
    validate = runpy.run_path(str(STUDY / 'analysis/summarise_baseline.py'))['validate_hours']
    count = 0
    with gzip.open(run / 'training-hours.jsonl.gz', 'rt') as stream:
        for metric in metrics:
            row = json.loads(next(stream))
            assert row['episode'] == metric['episode']
            validate(row['hours'], metric, metric['steps'], metric['unseen'])
            assert math.isfinite(metric['weight_norm'])
            count += 24
        assert stream.read() == ''
    first = json.loads((old / 'episodes.jsonl').read_text().splitlines()[0])
    if metrics:
        assert all(metrics[0][k] == first[k] for k in ('reward','steps','served_demand_ratio','hourly_rewards'))
    checkpoints = []
    for path in sorted(run.glob('evaluation-*.json')):
        value = load(path)
        assert value['learner_unchanged']
        assert [v['seed'] for v in value['evaluations']] == [7100,7101,7102]
        for v in value['evaluations']:
            validate(v['hours'], v['daily'], v['steps'], v['unseen'])
            count += 24
        if value['episode'] == 0:
            previous = load(old / path.name)
            assert [v['daily'] for v in value['evaluations']] == [v['daily'] for v in previous['evaluations']]
        checkpoints.append(dict(episode=value['episode'], served_ratio=statistics.mean(v['diagnostics']['served_ratio'] for v in value['evaluations']), reward=statistics.mean(v['reward'] for v in value['evaluations'])))
    for path in run.glob('weights-*.json'):
        weights = load(path)['weights']
        assert len(weights) == 8 and all(len(row) == 32 for row in weights)
        assert all(math.isfinite(w) for row in weights for w in row)
    passed = manifest['status'] == 'completed' and len(metrics) == 300
    if passed:
        assert [v['episode'] for v in checkpoints] == [0,100,300]
        assert manifest['sleep_scope_exited']
    return dict(status='verified', operational_gate_passed=passed, run_status=manifest['status'], execution_commit=manifest['code_commit'], episodes_completed=len(metrics), hourly_records_verified=count, checkpoints=checkpoints, final_weight_norm=metrics[-1]['weight_norm'] if metrics else None, maximum_episode_weight_norm=max((m['weight_norm'] for m in metrics),default=None), training_seconds=manifest['training_seconds'], process_seconds=manifest['total_elapsed_seconds'], maximum_recorded_working_mb=max((m['working_mb'] for m in metrics),default=None), checksums={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(run.iterdir()) if p.is_file()}, interpretation='Single-seed visited-input stability only; no convergence or quality-superiority claim.')


if __name__ == '__main__':
    result = analyse(Path(sys.argv[1]))
    with Path(sys.argv[2]).open('x') as stream:
        json.dump(result, stream, indent=2)
        stream.write('\n')
