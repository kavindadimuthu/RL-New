"""Analyze completed equal-time jobs and summarize all three stages."""
import json
from pathlib import Path
import statistics as stats

root = Path(__file__).resolve().parent
results = json.loads((root / 'results.json').read_text())
assert len(results) == 9
assert all(r['stop_reason'] == 'completed' and r['job']['phase']=='equal_time'
           and r['training_seconds']>=120 for r in results)
metrics=['reward','served_demand_ratio','total_operator_penalty',
         'total_transition_component','unseen_fraction','steps',
         'average_fleet_used','forced_hour_finishes']
per_seed=[]
checkpoints=[]
for result in results:
    mode,seed=result['job']['mode'],result['job']['seed']
    rows=[json.loads(line) for line in (root/'equal_time'/f'{mode}_seed_{seed}'/'episodes.jsonl').read_text().splitlines()]
    assert len(rows)==result['episodes']
    assert abs(rows[0]['epsilon']-1)<1e-12 and abs(rows[-1]['epsilon']-.05)<1e-12
    assert len(result['evaluations'])==3
    for target,point in zip([40,80,120],result['evaluations']):
        assert point['training_seconds']>=target
        values=point['evaluations']
        assert [v['seed'] for v in values]==[6000,6001,6002]
        checkpoints.append(dict(mode=mode,seed=seed,budget_seconds=target,
                                actual_training_seconds=point['training_seconds'],episode=point['episode'],
                                **{key:stats.mean(v[key] for v in values) for key in metrics}))
    final=checkpoints[-1]
    per_seed.append(dict(**final,training_seconds=result['training_seconds'],
                         training_cpu_seconds=result['training_cpu_seconds'],episodes=result['episodes'],
                         training_steps=result['steps'],assignments=result['assignment_cache_misses'],
                         max_memory_mib=max(r['memory_mb'] for r in rows),
                         states=rows[-1]['states'],pairs=rows[-1]['pairs'],
                         final_episode_seconds=rows[-1]['episode_seconds'],
                         evaluation_rewards=[v['reward'] for v in result['evaluations'][-1]['evaluations']]))
modes=sorted({r['mode'] for r in per_seed})
summary=[]
for mode in modes:
    group=sorted([r for r in per_seed if r['mode']==mode],key=lambda r:r['seed'])
    summary.append(dict(mode=mode,**{key:stats.mean(r[key] for r in group) for key in metrics+
                        ['training_seconds','training_cpu_seconds','episodes','training_steps','assignments','states']},
                        reward_std=stats.stdev(r['reward'] for r in group),
                        reward_min=min(r['reward'] for r in group),reward_max=max(r['reward'] for r in group),
                        episode_min=min(r['episodes'] for r in group),episode_max=max(r['episodes'] for r in group),
                        max_memory_mib=max(r['max_memory_mib'] for r in group),
                        reward_at_checkpoints={str(t):stats.mean(r['reward'] for r in checkpoints if r['mode']==mode and r['budget_seconds']==t) for t in [40,80,120]}))
baseline={r['seed']:r for r in per_seed if r['mode']=='A_dense'}
paired=[dict(mode=r['mode'],seed=r['seed'],reward_difference_vs_A=r['reward']-baseline[r['seed']]['reward'],
             served_ratio_difference_vs_A=r['served_demand_ratio']-baseline[r['seed']]['served_demand_ratio'])
        for r in per_seed if r['mode']!='A_dense']
stage1=json.loads((root.parent/'evaluation_comparison_stage1/comparison.json').read_text())
stage2=json.loads((root.parent/'evaluation_comparison_stage2/comparison.json').read_text())
analysis=dict(summary=summary,per_training_seed=per_seed,paired_differences=paired,checkpoints=checkpoints,
              stage1=stage1,stage2_summary=stage2['summary'],untrained_diagnostic=stage2.get('untrained_diagnostic'))
(root/'comparison.json').write_text(json.dumps(analysis,indent=2),encoding='utf-8')
labels={'A_dense':'A: every action','B_committed':'B: committed changes','C_hour_end':'C: hour end'}
lines=['# Stage 3: equal-training-time comparison','',
       'All nine jobs completed: 120 training seconds per treatment per seed (2024, 2025, 2026), in three concurrent-worker waves. Complete the current episode before stopping; exact overshoot is recorded. Evaluation/reporting are outside the training budget.','',
       'All treatments use the same elapsed-training-time exploration schedule, reaching epsilon 0.05 at 96 seconds. A fresh learner starts each job. Three common independent greedy-evaluation seeds (6000, 6001, 6002) are averaged within each training seed, then results are averaged across the three training seeds. The independent training sample size is three.','',
       '| Method | Mean final reward | Training-seed range | Demand served | Mean episodes | Mean training seconds | Unseen evaluation states |',
       '|---|---:|---:|---:|---:|---:|---:|']
for r in summary:
    lines.append(f"| {labels[r['mode']]} | {r['reward']:.4f} | {r['reward_min']:.4f}–{r['reward_max']:.4f} | {100*r['served_demand_ratio']:.2f}% | {r['episodes']:.1f} | {r['training_seconds']:.2f} | {100*r['unseen_fraction']:.2f}% |")
lines += ['','| Method | Seed 2024 reward | Seed 2025 reward | Seed 2026 reward |','|---|---:|---:|---:|']
for mode in modes:
    group=sorted([r for r in per_seed if r['mode']==mode],key=lambda r:r['seed'])
    lines.append('| '+labels[mode]+' | '+' | '.join(f"{r['reward']:.4f}" for r in group)+' |')
lines += ['','| Method | Reward at 40 training seconds | At 80 | At 120 | Peak worker RAM MiB |',
          '|---|---:|---:|---:|---:|']
for r in summary:
    lines.append('| '+labels[r['mode']]+' | '+' | '.join(f"{r['reward_at_checkpoints'][str(t)]:.4f}" for t in [40,80,120])+f" | {r['max_memory_mib']:.1f} |")
lines += ['','## Paired final reward differences against A','']
for mode in modes[1:]:
    group=sorted([r for r in paired if r['mode']==mode],key=lambda r:r['seed'])
    lines.append(labels[mode]+': '+', '.join(f"seed {r['seed']}: {r['reward_difference_vs_A']:+.4f}" for r in group)+'.')
lines += ['','## All-stage overview','',
          '| Method | Stage 1: serial seconds / 100 episodes | Stage 2: reward after 300 episodes | Stage 3: reward after 120 training seconds |',
          '|---|---:|---:|---:|']
for mode in modes:
    one=next(r for r in stage1 if r['mode']==mode)
    two=next(r for r in stage2['summary'] if r['mode']==mode)
    three=next(r for r in summary if r['mode']==mode)
    lines.append(f"| {labels[mode]} | {one['seconds']:.2f} | {two['reward']:.4f} | {three['reward']:.4f} |")
lines += ['','## Limits','',
          'Stage 1 uses the original episode-based exploration schedule. Stage 2 uses a shared shorter episode-based schedule. Stage 3 uses a shared time-based schedule. Compare treatments WITHIN a stage; changes between stages include exploration timing as well as available training experience.','',
          'Same input demand is used in training and evaluation; this measures fixed-problem optimization, not held-out generalization. Exact raw states make new combinations unseen by the Q-table; greedy ties/unseen states still introduce randomness. High unseen-state fractions require caution in interpreting learning.','',
          'Three training seeds are insufficient for a definitive statistical ranking. Individual paired results, reward ranges and served-demand ratios matter alongside averages. These are short-budget screening results, not convergence measurements. End-of-episode stopping gives small unequal overshoots; consult exact time and CPU-time fields. Worker timing is subject to shared laptop resources.','',
          'The next decision should consider service quality and repeatability together with time and memory. Raw source/input snapshots, configurations, episode logs, all evaluation checkpoints and resource measures remain available. No further training stage was started.']
lines += ['', '## Final policy behavior', '',
          '| Method | Mean evaluation actions per day | Mean operating fleet per hour | Mean forced hour endings per day |',
          '|---|---:|---:|---:|']
for r in summary:
    lines.append(f"| {labels[r['mode']]} | {r['steps']:.1f} | {r['average_fleet_used']:.2f} | {r['forced_hour_finishes']:.2f} |")
lines += ['', '## Observed outcome and recommendation', '',
          'In this completed short-budget comparison, A has the highest average final reward and demand served in both learning stages. B has lower mean reward but beats A in one of three training seeds in each learning stage; the data do not establish a definitive long-run A-versus-B ranking.', '',
          'C is much faster per episode, yet its additional episodes did not compensate for delayed feedback in this protocol. All three final greedy policies use very few daily actions (mean 29.7), operate about two buses per hour, and serve about 4.1% of demand. Zero unseen-state fraction in C means those short evaluation trajectories were memorized, not that broad state-space coverage was achieved. Early hour completion with limited service is consistent with the observed low-action policies; these measurements do not establish the precise learning mechanism or an inevitable failure of hour-end rewards.', '',
          'Retain A as the current default. Prioritize speeding up its assignment implementation while preserving results; retain B as a candidate for further validation. Do not adopt C solely for its timing advantage. A and B still have very high unseen-state fractions, so exact-state coverage is a separate issue from simulator speed. These recommendations are limited to the tested budget, schedules, fixed demand and three training seeds.']
if analysis['untrained_diagnostic']:
    b=analysis['untrained_diagnostic']
    lines += ['',f"The separate empty-Q-table reference from Stage 2 scored {b['reward']:.4f} and served {100*b['served_demand_ratio']:.2f}% of demand using the same three evaluation seeds. This post-hoc reference is not an additional trained replication."]
(root/'SUMMARY.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
print(json.dumps(dict(summary=summary,paired_differences=paired),indent=2))
print('Report: '+str(root/'SUMMARY.md'))
