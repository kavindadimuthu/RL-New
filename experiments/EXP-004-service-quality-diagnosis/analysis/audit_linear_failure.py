"""Post-execution S5 failure audit; no planning/training or invented trigger value."""
import argparse
import gzip
import hashlib
import json
import math
from pathlib import Path
import runpy

STUDY = Path(__file__).resolve().parents[1]


def analyse(directory):
    validate = runpy.run_path(str(STUDY / 'analysis/summarise_baseline.py'))['validate_hours']
    parent = json.loads((directory / 'study-manifest.json').read_text())
    assert parent['status'] == 'failed' and len(parent['waves']) == 1
    e = directory / 'EXP-004-S5-E-seed2034-run01'
    l = directory / 'EXP-004-S5-L-seed2034-run01'
    manifests = {m: json.loads((p / 'manifest.json').read_text()) for m, p in [('E', e), ('L', l)]}
    assert manifests['E']['status'] == 'completed' and manifests['E']['episodes_completed'] == 300
    assert manifests['L']['status'] == 'failed' and manifests['L']['episodes_completed'] == 48
    assert 'linear Q stability guard' in manifests['L']['error']
    assert all(m['code_commit'] == parent['code_commit'] and not m['working_tree_status'].strip() for m in manifests.values())
    assert json.loads((e / 'config.json').read_text()) == json.loads((l / 'config.json').read_text())
    assert (e / 'source-input-sha256.json').read_bytes() == (l / 'source-input-sha256.json').read_bytes()
    metrics, hours_count = {}, 0
    for method, folder, checkpoints in [('E', e, (0, 100, 300)), ('L', l, (0,))]:
        rows = [json.loads(line) for line in (folder / 'episodes.jsonl').read_text().splitlines()]
        assert len(rows) == manifests[method]['episodes_completed']
        assert [r['episode'] for r in rows] == list(range(1, len(rows)+1))
        metrics[method] = rows
        with gzip.open(folder / 'training-hours.jsonl.gz', 'rt', encoding='utf-8') as file:
            count = 0
            for line, row in zip(file, rows):
                item = json.loads(line)
                assert item['episode'] == row['episode']
                validate(item['hours'], row, row['steps'], row['unseen'])
                hours_count += 24
                count += 1
            assert count == len(rows) and file.readline() == ''
        for episode in checkpoints:
            checkpoint = json.loads((folder / f'evaluation-{episode:03d}.json').read_text())
            assert checkpoint['episode'] == episode and checkpoint['learner_unchanged']
            assert [v['seed'] for v in checkpoint['evaluations']] == [7100, 7101, 7102]
            for value in checkpoint['evaluations']:
                validate(value['hours'], value['daily'], value['steps'], value['unseen'])
                hours_count += 24
    old = STUDY / 'evidence/S4-remaining-actions-run01/EXP-004-S4-B-seed2034-run01'
    old_metrics = [json.loads(line) for line in (old / 'episodes.jsonl').read_text().splitlines()]
    keys = ('reward', 'steps', 'unseen', 'served_demand_ratio', 'q_states', 'q_pairs', 'hourly_rewards')
    assert all(all(a[k] == b[k] for k in keys) for a, b in zip(metrics['E'], old_metrics))
    for episode in (0, 100, 300):
        current = json.loads((e / f'evaluation-{episode:03d}.json').read_text())
        prior = json.loads((old / f'evaluation-{episode:03d}.json').read_text())
        assert [v['daily'] for v in current['evaluations']] == [v['daily'] for v in prior['evaluations']]
    physics = ('reward', 'steps', 'served_demand_ratio', 'hourly_rewards')
    assert all(metrics['E'][0][k] == metrics['L'][0][k] for k in physics)
    assert [v['daily'] for v in json.loads((e/'evaluation-000.json').read_text())['evaluations']] == [
        v['daily'] for v in json.loads((l/'evaluation-000.json').read_text())['evaluations']]
    assert not (l/'evaluation-100.json').exists() and not (l/'evaluation-300.json').exists()
    snapshot = json.loads((l / 'weights-final.json').read_text())
    assert snapshot['parameter_count'] == 256
    assert all(math.isfinite(w) for row in snapshot['weights'] for w in row)
    return dict(status='verified_partial_evidence', analysis_type='post-execution failure audit',
        execution_commit=parent['code_commit'], completed_episodes={m: len(r) for m, r in metrics.items()},
        failed_episode_inferred=49, hourly_records_verified=hours_count,
        historical_E_reproduced=True, first_random_physics_and_empty_evaluation_match=True,
        weight_norm_history=[dict(episode=r['episode'], norm=r['weight_norm']) for r in metrics['L'] if r['episode'] in (1, 10, 25, 48)],
        final_weight_norm=math.sqrt(sum(w*w for row in snapshot['weights'] for w in row)),
        final_maximum_weight_row_norm=max(math.sqrt(sum(w*w for w in row)) for row in snapshot['weights']),
        failure=manifests['L']['error'], full_quality_comparison='not_available',
        critical_path_seconds=parent['total_elapsed_seconds'],
        limitations=['Episode49 partial trajectory and exact offending Q/state were not saved.',
            'Threshold breach is recorded; no exact trigger magnitude is invented.',
            'L failure manifest lacks explicit sleep_scope_exited flag; scoped finally restoration is implemented/tested, not retroactively added to raw metadata.',
            'Cannot infer generalization or DQN performance from this unstable linear variant.'],
        checksums={p.relative_to(directory).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                   for p in sorted(directory.rglob('*')) if p.is_file()})


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = analyse(args.directory)
    with args.output.open('x', encoding='utf-8') as file:
        json.dump(result, file, indent=2)
        file.write('\n')
    print(json.dumps({k: v for k, v in result.items() if k != 'checksums'}, indent=2))
