"""Registered S1 validation/aggregation. No model training or overwrites."""
import argparse
from datetime import datetime
import gzip
import hashlib
import json
import math
from pathlib import Path
import statistics


def validate_hours(rows, daily, steps, unseen):
    assert len(rows) == 24 and [r['hour'] for r in rows] == list(range(1, 25))
    assert sum(r['actions'] for r in rows) == steps
    assert sum(r['unseen_decisions'] for r in rows) == unseen
    assert sum(r['forced_finish'] for r in rows) == daily['forced_hour_finishes']
    assert math.isclose(sum(r['served_passengers'] for r in rows), daily['served_passengers'], abs_tol=1e-6)
    for r in rows:
        assert math.isclose(r['served_passengers'] + r['no_eligible_path_unserved']
                            + r['capacity_constrained_unserved'], r['total_demand'], abs_tol=1e-6)
        assert all(math.isfinite(r[k]) and r[k] >= -1e-7 for k in
                   ('served_passengers', 'no_eligible_path_unserved', 'capacity_constrained_unserved'))
        assert r['actions'] == sum(r['action_counts'].values())
        assert r['actions'] == len(r['state_visits_before_decision'])
        assert r['actions'] == len(r['selected_action_visits_before_decision'])
        assert r['fleet_used'] + r['fleet_remaining'] == 99
        assert all(0 <= x <= 1 + 1e-8 for x in r['route_peak_capacity_ratios'])


def analyse(directory):
    models, checksums, commits = [], {}, set()
    total_records = 0
    baseline_references = []
    for seed in (2034, 2035, 2036):
        run = directory / f'EXP-004-S1-baseline-seed{seed}-run01'
        manifest = json.loads((run / 'manifest.json').read_text())
        assert manifest['status'] == 'completed' and manifest['episodes_completed'] == 300
        assert manifest['training_seed'] == seed and not manifest['working_tree_status'].strip()
        assert manifest['sleep_scope_exited']
        commits.add(manifest['code_commit'])
        metrics = [json.loads(line) for line in (run / 'episodes.jsonl').read_text().splitlines()]
        assert [m['episode'] for m in metrics] == list(range(1, 301))
        assert math.isclose(sum(m['elapsed_seconds'] for m in metrics), manifest['training_seconds'], abs_tol=1e-6)
        with gzip.open(run / 'training-hours.jsonl.gz', 'rt', encoding='utf-8') as file:
            count = 0
            for line, metric in zip(file, metrics):
                value = json.loads(line)
                assert value['episode'] == metric['episode']
                validate_hours(value['hours'], metric, metric['steps'], metric['unseen'])
                total_records += 24
                count += 1
            assert count == 300 and file.readline() == ''
        checkpoints = []
        for episode in (0, 100, 300):
            checkpoint = json.loads((run / f'evaluation-{episode:03d}.json').read_text())
            assert checkpoint['episode'] == episode and checkpoint['learner_unchanged']
            values = checkpoint['evaluations']
            assert [v['seed'] for v in values] == [7100, 7101, 7102]
            for value in values:
                validate_hours(value['hours'], value['daily'], value['steps'], value['unseen'])
                total_records += 24
                d = value['diagnostics']
                assert math.isclose(d['served_ratio'], value['daily']['served_demand_ratio'], abs_tol=1e-12)
                assert math.isclose(d['served_ratio']+d['no_path_demand_share']+d['capacity_demand_share'], 1, abs_tol=1e-9)
            means = {k: statistics.mean(v['diagnostics'][k] for v in values)
                     for k in values[0]['diagnostics'] if all(v['diagnostics'][k] is not None for v in values)}
            means['reward'] = statistics.mean(v['reward'] for v in values)
            checkpoints.append(dict(episode=episode, means=means))
            if episode == 0:
                baseline_references.append(means)
        utc = (datetime.fromisoformat(manifest['finished_at']) -
               datetime.fromisoformat(manifest['started_at'])).total_seconds()
        models.append(dict(seed=seed, checkpoints=checkpoints,
            training_seconds=manifest['training_seconds'], total_elapsed_seconds=manifest['total_elapsed_seconds'],
            utc_span_seconds=utc, clock_gap_seconds=utc-manifest['total_elapsed_seconds'],
            max_recorded_working_mb=max(m['working_mb'] for m in metrics),
            final_q_states=metrics[-1]['q_states'], final_q_pairs=metrics[-1]['q_pairs']))
        for file in sorted(run.iterdir()):
            if file.is_file():
                checksums[file.relative_to(directory).as_posix()] = hashlib.sha256(file.read_bytes()).hexdigest()
    assert len(commits) == 1
    assert baseline_references[0] == baseline_references[1] == baseline_references[2]
    final = [m['checkpoints'][-1]['means'] for m in models]
    summary = {key: dict(mean=statistics.mean(v[key] for v in final),
                         minimum=min(v[key] for v in final), maximum=max(v[key] for v in final))
               for key in final[0] if all(key in v for v in final)}
    return dict(status='verified', execution_commit=next(iter(commits)), models=models,
        final_three_model_summary=summary, hourly_records_verified=total_records,
        total_training_seconds=sum(m['training_seconds'] for m in models),
        summed_process_elapsed_seconds=sum(m['total_elapsed_seconds'] for m in models),
        checksums=checksums,
        limitations=['Three training seeds; evaluation ties averaged within models.',
                     'Same fixed demand used for training and evaluation.',
                     'Diagnostic associations are not causal effects or a feasibility ceiling.',
                     'All runtime includes diagnostic overhead; serial CPU execution.',
                     'Ranges describe model means, not confidence intervals.'])


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = analyse(args.directory)
    with args.output.open('x', encoding='utf-8') as file:
        json.dump(result, file, indent=2)
        file.write('\n')
    print(json.dumps({k: v for k, v in result.items() if k not in ('models', 'checksums')}, indent=2))
