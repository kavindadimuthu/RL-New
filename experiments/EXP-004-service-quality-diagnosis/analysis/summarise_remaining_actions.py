"""Registered S4 paired comparison and historical-control integrity check."""
from datetime import datetime
import argparse
import gzip
import hashlib
import json
import math
from pathlib import Path
import runpy
import statistics

STUDY = Path(__file__).resolve().parents[1]


def analyse(directory):
    validate = runpy.run_path(str(STUDY / 'analysis/summarise_baseline.py'))['validate_hours']
    study = json.loads((directory / 'study-manifest.json').read_text())
    assert study['status'] == 'completed' and len(study['waves']) == 3
    models, configs, inputs, commits = [], [], [], set()
    total_hours = 0
    for seed in (2034, 2035, 2036):
        first_physics, zero_reference = [], []
        for method in ('A', 'B'):
            run = directory / f'EXP-004-S4-{method}-seed{seed}-run01'
            manifest = json.loads((run / 'manifest.json').read_text())
            assert manifest['status'] == 'completed' and manifest['episodes_completed'] == 300
            assert manifest['stage'] == 'S4-remaining-actions' and manifest['method'] == method
            assert manifest['training_seed'] == seed and not manifest['working_tree_status'].strip()
            assert manifest['sleep_scope_exited']
            commits.add(manifest['code_commit'])
            configs.append(json.loads((run / 'config.json').read_text()))
            inputs.append(json.loads((run / 'source-input-sha256.json').read_text()))
            metrics = [json.loads(line) for line in (run / 'episodes.jsonl').read_text().splitlines()]
            assert [m['episode'] for m in metrics] == list(range(1, 301))
            assert math.isclose(sum(m['elapsed_seconds'] for m in metrics), manifest['training_seconds'], abs_tol=1e-6)
            first_physics.append({k: metrics[0][k] for k in ('reward', 'steps', 'served_demand_ratio', 'hourly_rewards')})
            with gzip.open(run / 'training-hours.jsonl.gz', 'rt', encoding='utf-8') as file:
                count = 0
                for line, metric in zip(file, metrics):
                    value = json.loads(line)
                    assert value['episode'] == metric['episode']
                    validate(value['hours'], metric, metric['steps'], metric['unseen'])
                    total_hours += 24
                    count += 1
                assert count == 300 and file.readline() == ''
            checkpoints = []
            for episode in (0, 100, 300):
                checkpoint = json.loads((run / f'evaluation-{episode:03d}.json').read_text())
                assert checkpoint['episode'] == episode and checkpoint['learner_unchanged']
                values = checkpoint['evaluations']
                assert [v['seed'] for v in values] == [7100, 7101, 7102]
                for value in values:
                    validate(value['hours'], value['daily'], value['steps'], value['unseen'])
                    total_hours += 24
                    assert math.isclose(value['diagnostics']['served_ratio'], value['daily']['served_demand_ratio'], abs_tol=1e-12)
                means = {k: statistics.mean(v['diagnostics'][k] for v in values)
                         for k in values[0]['diagnostics'] if all(v['diagnostics'][k] is not None for v in values)}
                means['reward'] = statistics.mean(v['reward'] for v in values)
                checkpoints.append(dict(episode=episode, means=means))
                if episode == 0:
                    zero_reference.append([v['daily'] for v in values])
                if method == 'A':
                    old = json.loads((STUDY / f'evidence/S1-baseline-run01/EXP-004-S1-baseline-seed{seed}-run01/evaluation-{episode:03d}.json').read_text())
                    assert [v['daily'] for v in values] == [v['daily'] for v in old['evaluations']], 'Fresh A checkpoint differs from historical control'
            if method == 'A':
                old_metrics = [json.loads(line) for line in (STUDY / f'evidence/S1-baseline-run01/EXP-004-S1-baseline-seed{seed}-run01/episodes.jsonl').read_text().splitlines()]
                keys = ('reward', 'steps', 'unseen', 'served_demand_ratio', 'q_states', 'q_pairs', 'hourly_rewards')
                assert all(all(a[k] == b[k] for k in keys) for a, b in zip(metrics, old_metrics)), 'Fresh A training differs from historical control'
            span = (datetime.fromisoformat(manifest['finished_at'])-datetime.fromisoformat(manifest['started_at'])).total_seconds()
            models.append(dict(seed=seed, method=method, checkpoints=checkpoints,
                training_seconds=manifest['training_seconds'], process_seconds=manifest['total_elapsed_seconds'],
                cpu_seconds=manifest['total_cpu_seconds'], clock_gap_seconds=span-manifest['total_elapsed_seconds'],
                maximum_recorded_working_mb=max(m['working_mb'] for m in metrics),
                final_q_states=metrics[-1]['q_states'], final_q_pairs=metrics[-1]['q_pairs']))
        assert first_physics[0] == first_physics[1]
        assert zero_reference[0] == zero_reference[1]
    assert len(commits) == 1 and next(iter(commits)) == study['code_commit']
    assert all(c == configs[0] for c in configs)
    assert all(h == inputs[0] for h in inputs)
    final = {method: [m['checkpoints'][-1]['means'] for m in models if m['method'] == method] for method in ('A', 'B')}
    summary = {method: {k: dict(mean=statistics.mean(v[k] for v in values), minimum=min(v[k] for v in values), maximum=max(v[k] for v in values))
               for k in values[0] if all(k in v for v in values)} for method, values in final.items()}
    pairs = [dict(seed=seed, B_minus_A={k: b[k]-a[k] for k in a if k in b})
             for seed, a, b in zip((2034, 2035, 2036), final['A'], final['B'])]
    differences = [p['B_minus_A']['served_ratio'] for p in pairs]
    advance = (statistics.mean(differences) >= .02 and min(differences) >= 0 and
               summary['B']['reward']['mean'] >= summary['A']['reward']['mean'])
    checksums = {p.relative_to(directory).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                 for p in sorted(directory.rglob('*')) if p.is_file()}
    utc = (datetime.fromisoformat(study['finished_at'])-datetime.fromisoformat(study['started_at'])).total_seconds()
    return dict(status='verified', execution_commit=next(iter(commits)), models=models,
        final_method_summary=summary, paired_seed_differences=pairs,
        mean_service_difference_percentage_points=100*statistics.mean(differences),
        service_difference_percentage_point_range=[100*min(differences), 100*max(differences)],
        screening_advance=advance, historical_A_reproduced_exactly=True,
        first_episode_physics_and_empty_Q_evaluations_match=True,
        hourly_records_verified=total_hours, critical_path_elapsed_seconds=study['total_elapsed_seconds'],
        critical_path_utc_span_seconds=utc, total_child_training_seconds=sum(m['training_seconds'] for m in models),
        total_child_cpu_seconds=sum(m['cpu_seconds'] for m in models), checksums=checksums,
        limitations=['Three paired training seeds; ties averaged within each learner.',
            'Same fixed demand; no generalization, convergence or significance claim.',
            'Paired-worker runtime is not comparable to previous serial timing as speed superiority.',
            'Finite-budget screen; not automatic default adoption or universal RL diagnosis.'])


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    value = analyse(args.directory)
    with args.output.open('x', encoding='utf-8') as file:
        json.dump(value, file, indent=2)
        file.write('\n')
    print(json.dumps({k: v for k, v in value.items() if k not in ('models', 'checksums')}, indent=2))
