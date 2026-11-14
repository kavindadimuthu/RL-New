"""Summarize only completed stage-one results; no training is performed."""
import json
from pathlib import Path
import statistics

root = Path(__file__).resolve().parent
results = json.loads((root / 'results.json').read_text())
assert len(results) == 3, 'All three timing jobs must finish before analysis'
assert all(r['stop_reason'] == 'completed' and r['episodes'] == 100 and
           r['job']['phase'] == 'timing' for r in results)
results.sort(key=lambda r: r['job']['mode'])
baseline = results[0]
summary = []
for result in results:
    mode = result['job']['mode']
    rows = [json.loads(line) for line in (root / 'timing' / f'{mode}_seed_2024' / 'episodes.jsonl').read_text().splitlines()]
    assert len(rows) == 100
    hits, misses = result['cache_hits'], result['assignment_cache_misses']
    item = dict(mode=mode, seconds=result['training_seconds'],
                speedup=baseline['training_seconds']/result['training_seconds'],
                time_reduction_percent=100*(1-result['training_seconds']/baseline['training_seconds']),
                mean_episode_seconds=result['mean_episode_seconds'],
                median_episode_seconds=statistics.median(row['episode_seconds'] for row in rows),
                cpu_seconds=result['training_cpu_seconds'], steps=result['steps'],
                milliseconds_per_step=1000*result['training_seconds']/result['steps'],
                evaluations=result['evaluation_requests'], actual_assignments=misses,
                cache_hit_percent=100*hits/(hits+misses),
                memory_mib=result['final_memory_mb'],
                max_memory_mib=max(row['memory_mb'] for row in rows),
                forced_finishes=sum(row['forced_finishes'] for row in rows),
                states=rows[-1]['states'], pairs=rows[-1]['pairs'],
                process_wall_seconds=result['process_wall_seconds_including_evaluation'],
                mean_seconds_by_25_episode_block=[statistics.mean(row['episode_seconds'] for row in rows[i:i+25])
                                                for i in range(0,100,25)])
    summary.append(item)
(root / 'comparison.json').write_text(json.dumps(summary, indent=2))
labels = {'A_dense': 'A: every action', 'B_committed': 'B: committed changes', 'C_hour_end': 'C: hour end'}
lines = ['# Stage 1: serial timing comparison', '',
         'Completed three 100-episode jobs, seed 2024, real 24-hour OD data and original 10,000-episode exploration schedule. Fresh process per job; serial order A, C, B. No GPU, profiler, plots, large Q-table exports or concurrent training. Only the timing stage was run.', '',
         '| Method | Training seconds | Seconds/episode | Speedup vs A | Time reduction |',
         '|---|---:|---:|---:|---:|']
for r in summary:
    lines.append(f"| {labels[r['mode']]} | {r['seconds']:.2f} | {r['mean_episode_seconds']:.3f} | {r['speedup']:.2f}x | {r['time_reduction_percent']:.1f}% |")
lines += ['', '| Method | Evaluation requests | Actual assignments (cache misses) | RL steps | ms/step | Ending RAM MiB |',
          '|---|---:|---:|---:|---:|---:|']
for r in summary:
    lines.append(f"| {labels[r['mode']]} | {r['evaluations']:,} | {r['actual_assignments']:,} | {r['steps']:,} | {r['milliseconds_per_step']:.3f} | {r['memory_mib']:.1f} |")
lines += ['', '## Interpretation', '',
          'Evaluation requests include plan scoring even when the passenger assignment result is cached. Actual assignments count cache misses. Counts in this report exclude initial environment construction; they include all episode resets and training actions.', '',
          'Training rewards can change action choices even with the same random seed, so compare step counts and milliseconds per step as well as total time. These are equal-episode training runs, not replay of an identical action trace. Correctness tests separately established agreement on fixed action sequences.', '',
          'This stage measures early-training runtime, not which approach learns better. Exploration remains approximately 96% at episode 100. One seed and one serial run per method do not establish uncertainty bounds, long-run speed or convergence. Thermal/system-load and run-order effects remain possible. The next stage should compare learned service quality across training seeds with a common evaluator.', '',
          'Raw episode logs, CPU times, memory, cached assignment counts, source/input snapshots and configuration are retained. Only outputs are Git-ignored; experiment implementation remains isolated on experiment/evaluation-frequency.', '',
          '## Next-stage duration estimate', '']
# Nine equal-episode jobs: three concurrent modes per seed wave, three seed waves.
equal_episode_seconds = 3 * 3 * max(r['seconds'] for r in summary)
equal_time_seconds = 3 * 120
lines += [f'At the measured early-training rate, the equal-episode stage has a baseline of approximately {equal_episode_seconds/60:.1f} minutes with three workers, before checkpoint evaluation, parallel slowdown and changed policies under the shorter exploration schedule.', '',
          f'The equal-time stage has a nominal training floor of {equal_time_seconds/60:.1f} minutes across three waves, plus episode-boundary overshoot and checkpoint evaluation. These are planning estimates, not measurements of the later stages. Neither later stage was started.']
(root / 'SUMMARY.md').write_text('\n'.join(lines)+'\n', encoding='utf-8')
print(json.dumps(summary, indent=2))
print('Report: '+str(root / 'SUMMARY.md'))
