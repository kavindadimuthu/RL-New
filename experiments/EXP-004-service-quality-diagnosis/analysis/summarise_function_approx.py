"""Registered S5 preflight/full accounting, stability status and paired summary."""
import argparse
from datetime import datetime
import gzip
import hashlib
import json
import math
from pathlib import Path
import runpy
import statistics

STUDY = Path(__file__).resolve().parents[1]


def analyse(directory):
    study = json.loads((directory / 'study-manifest.json').read_text())
    checksums = {p.relative_to(directory).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                 for p in sorted(directory.rglob('*')) if p.is_file()}
    preflight = study['stage'] == 'S5P'
    prefix, episodes = ('S5P', 2) if preflight else ('S5', 300)
    seeds = (2034,) if preflight else (2034, 2035, 2036)
    checkpoints = (0, 2) if preflight else (0, 100, 300)
    if study['status'] != 'completed':
        statuses = {p.parent.name: json.loads(p.read_text()) for p in directory.glob('*/manifest.json')}
        return dict(status='incomplete', execution_commit=study['code_commit'], study=study,
                    run_statuses=statuses, checksums=checksums,
                    decision='No normal final comparison: retain failure without automatic rerun.')
    validate = runpy.run_path(str(STUDY / 'analysis/summarise_baseline.py'))['validate_hours']
    models, configs, inputs, raw_count = [], [], [], 0
    for seed in seeds:
        initial_physics, empty_results = [], []
        for method in ('E', 'L'):
            run = directory / f'EXP-004-{prefix}-{method}-seed{seed}-run01'
            manifest = json.loads((run / 'manifest.json').read_text())
            assert manifest['status'] == 'completed' and manifest['episodes_completed'] == episodes
            assert manifest['code_commit'] == study['code_commit'] and not manifest['working_tree_status'].strip()
            assert manifest['method'] == method and manifest['sleep_scope_exited']
            assert manifest['target_episodes'] == episodes
            configs.append(json.loads((run / 'config.json').read_text()))
            inputs.append(json.loads((run / 'source-input-sha256.json').read_text()))
            metrics = [json.loads(line) for line in (run / 'episodes.jsonl').read_text().splitlines()]
            assert [m['episode'] for m in metrics] == list(range(1, episodes+1))
            assert math.isclose(sum(m['elapsed_seconds'] for m in metrics), manifest['training_seconds'], abs_tol=1e-6)
            initial_physics.append({k: metrics[0][k] for k in ('reward', 'steps', 'served_demand_ratio', 'hourly_rewards')})
            with gzip.open(run / 'training-hours.jsonl.gz', 'rt', encoding='utf-8') as file:
                count = 0
                for line, metric in zip(file, metrics):
                    item = json.loads(line)
                    assert item['episode'] == metric['episode']
                    validate(item['hours'], metric, metric['steps'], metric['unseen'])
                    count += 1
                    raw_count += 24
                assert count == episodes and file.readline() == ''
            if method == 'E':
                old = STUDY / f'evidence/S4-remaining-actions-run01/EXP-004-S4-B-seed{seed}-run01'
                old_metrics = [json.loads(line) for line in (old / 'episodes.jsonl').read_text().splitlines()][:episodes]
                keys = ('reward', 'steps', 'unseen', 'served_demand_ratio', 'q_states', 'q_pairs', 'hourly_rewards')
                assert all(all(a[k] == b[k] for k in keys) for a, b in zip(metrics, old_metrics))
            summaries = []
            for episode in checkpoints:
                checkpoint = json.loads((run / f'evaluation-{episode:03d}.json').read_text())
                assert checkpoint['learner_unchanged'] and checkpoint['episode'] == episode
                values = checkpoint['evaluations']
                assert [v['seed'] for v in values] == [7100, 7101, 7102]
                for value in values:
                    validate(value['hours'], value['daily'], value['steps'], value['unseen'])
                    raw_count += 24
                    if method == 'L':
                        audit = value['generalization_audit']
                        assert audit['decisions'] == value['steps']
                        assert audit['unseen_exact_key'] == value['unseen']
                        assert audit['unseen_unique_best']+audit['unseen_tied_best']+audit['unseen_single_valid'] == value['unseen']
                means = {k: statistics.mean(v['diagnostics'][k] for v in values)
                    for k in values[0]['diagnostics'] if all(v['diagnostics'][k] is not None for v in values)}
                means['reward'] = statistics.mean(v['reward'] for v in values)
                if method == 'L':
                    audits = [v['generalization_audit'] for v in values]
                    choices = sum(a['unseen_unique_best']+a['unseen_tied_best'] for a in audits)
                    means['unseen_choice_unique_best_fraction'] = sum(a['unseen_unique_best'] for a in audits)/choices if choices else None
                    snapshot = json.loads((run / f'weights-{episode:03d}.json').read_text())
                    assert snapshot['parameter_count'] == 256 and len(snapshot['feature_names']) == 32
                    assert len(snapshot['weights']) == 8 and all(len(r) == 32 for r in snapshot['weights'])
                    assert all(math.isfinite(w) for row in snapshot['weights'] for w in row)
                if episode == 0:
                    empty_results.append([v['daily'] for v in values])
                if method == 'E' and episode in (0, 100, 300):
                    previous = json.loads((old / f'evaluation-{episode:03d}.json').read_text())
                    assert [v['daily'] for v in values] == [v['daily'] for v in previous['evaluations']]
                summaries.append(dict(episode=episode, means=means))
            span = (datetime.fromisoformat(manifest['finished_at'])-datetime.fromisoformat(manifest['started_at'])).total_seconds()
            models.append(dict(seed=seed, method=method, checkpoints=summaries,
                training_seconds=manifest['training_seconds'], process_seconds=manifest['total_elapsed_seconds'],
                cpu_seconds=manifest['total_cpu_seconds'], clock_gap_seconds=span-manifest['total_elapsed_seconds'],
                maximum_recorded_working_mb=max(m['working_mb'] for m in metrics),
                final_audit_states=metrics[-1]['q_states'], final_audit_pairs=metrics[-1]['q_pairs'],
                parameter_count=256 if method == 'L' else None))
        assert initial_physics[0] == initial_physics[1]
        assert empty_results[0] == empty_results[1]
    assert all(c == configs[0] for c in configs) and all(h == inputs[0] for h in inputs)
    final = {method: [m['checkpoints'][-1]['means'] for m in models if m['method'] == method] for method in ('E', 'L')}
    summaries = {method: {k: statistics.mean(v[k] for v in values) for k in values[0]
                if all(k in v and v[k] is not None for v in values)} for method, values in final.items()}
    pairs = [dict(seed=seed, service_difference_percentage_points=100*(b['served_ratio']-a['served_ratio']),
                  reward_difference=b['reward']-a['reward']) for seed, a, b in zip(seeds, final['E'], final['L'])]
    difference = statistics.mean(p['service_difference_percentage_points'] for p in pairs)
    advance = (not preflight and difference >= 2 and min(p['service_difference_percentage_points'] for p in pairs) >= 0
               and summaries['L']['reward'] >= summaries['E']['reward'])
    return dict(status='verified', preflight=preflight, execution_commit=study['code_commit'],
        models=models, final_method_means=summaries, paired_differences=pairs,
        mean_service_difference_percentage_points=difference, screening_advance=advance,
        historical_E_reproduced=True, empty_models_and_first_random_physics_match=True,
        hourly_records_verified=raw_count, critical_path_seconds=study['total_elapsed_seconds'], checksums=checksums,
        limitations=['Feature engineering and linear approximation are bundled; not isolated sharing causality.',
            'Exact-key novelty is not lack of learned guidance for L.',
            'Same fixed demand, short budget, no held-out/convergence/significance claim.',
            'Single preflight seed is operational only.' if preflight else 'Three paired training seeds; evaluation ties not independent learners.'])


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = analyse(args.directory)
    with args.output.open('x', encoding='utf-8') as file:
        json.dump(result, file, indent=2)
        file.write('\n')
    print(json.dumps({k: v for k, v in result.items() if k not in ('checksums', 'models')}, indent=2))
