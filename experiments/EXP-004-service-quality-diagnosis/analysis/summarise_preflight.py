"""Post-execution preflight accounting/summary; never retrains a model."""
import argparse
from datetime import datetime
import hashlib
import json
import math
from pathlib import Path
import statistics


def analyse(directory):
    manifest = json.loads((directory / 'manifest.json').read_text())
    assert manifest['status'] == 'completed' and manifest['evaluation_learner_unchanged']
    assert manifest['sleep_scope_exited']
    episodes = [json.loads(x) for x in (directory / 'episodes.jsonl').read_text().splitlines()]
    assert [x['episode'] for x in episodes] == [1, 2]
    evaluations = json.loads((directory / 'evaluations.json').read_text())
    assert [x['seed'] for x in evaluations] == [7100, 7101, 7102]
    summaries = []
    files = [directory / f'training-{i}-hours.json' for i in (1, 2)]
    files += [directory / f'evaluation-{i}-hours.json' for i in (7100, 7101, 7102)]
    for path, daily in zip(files, episodes + evaluations):
        rows = json.loads(path.read_text())
        assert len(rows) == 24 and [r['hour'] for r in rows] == list(range(1, 25))
        for r in rows:
            assert math.isclose(r['served_passengers'] + r['no_eligible_path_unserved']
                                + r['capacity_constrained_unserved'], r['total_demand'], abs_tol=1e-6)
            assert r['actions'] == sum(r['action_counts'].values())
            assert len(r['state_visits_before_decision']) == r['actions']
            assert len(r['selected_action_visits_before_decision']) == r['actions']
            assert r['fleet_used'] + r['fleet_remaining'] == 99
            assert all(0 <= x <= 1 + 1e-8 for x in r['route_peak_capacity_ratios'])
        total = sum(r['total_demand'] for r in rows)
        served = sum(r['served_passengers'] for r in rows)
        assert math.isclose(served, daily['served_passengers'], abs_tol=1e-6)
        assert sum(r['actions'] for r in rows) == daily['steps']
        assert sum(r['unseen_decisions'] for r in rows) == daily['unseen']
        assert sum(r['forced_finish'] for r in rows) == daily['forced_hour_finishes']
        summaries.append(dict(file=path.name, served_ratio=served/total,
            no_path_share_of_total_demand=sum(r['no_eligible_path_unserved'] for r in rows)/total,
            capacity_share_of_total_demand=sum(r['capacity_constrained_unserved'] for r in rows)/total,
            unseen_fraction=daily['unseen']/daily['steps'],
            average_fleet=daily['average_fleet_used'], forced_finishes=daily['forced_hour_finishes'],
            discarded_routes=sum(bool(r['discarded_unfinished_route']) for r in rows)))
    elapsed = (datetime.fromisoformat(manifest['finished_at']) -
               datetime.fromisoformat(manifest['started_at'])).total_seconds()
    assert abs(elapsed - manifest['elapsed_seconds']) < 2
    return dict(status='verified', hourly_records=120, summaries=summaries,
        mean_of_three_evaluation_ties={k: statistics.mean(r[k] for r in summaries[2:])
            for k in ('served_ratio', 'no_path_share_of_total_demand',
                      'capacity_share_of_total_demand', 'unseen_fraction', 'average_fleet')},
        measured_instrumented_training_seconds=sum(r['elapsed_seconds'] for r in episodes),
        measured_total_seconds=manifest['elapsed_seconds'],
        limitations=['Only two training episodes and one learner; no quality or causal claim.',
                     'Capacity category includes greedy allocation effects.',
                     'Instrumentation overhead included; not baseline speed.',
                     'Analysis added after execution; protocol metrics unchanged.'],
        checksums={p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                   for p in sorted(directory.iterdir()) if p.is_file()})


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = analyse(args.directory)
    with args.output.open('x', encoding='utf-8') as file:
        json.dump(result, file, indent=2)
        file.write('\n')
    print(json.dumps({k: v for k, v in result.items() if k not in ('checksums', 'summaries')}, indent=2))
