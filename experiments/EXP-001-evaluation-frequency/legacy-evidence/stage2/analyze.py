"""Analyze completed equal-episode jobs; no learning is performed."""
import json
from pathlib import Path
import statistics as stats

root = Path(__file__).resolve().parent
results = json.loads((root / 'results.json').read_text())
assert len(results) == 9
assert all(r['stop_reason'] == 'completed' and r['episodes'] == 300 and
           r['job']['phase'] == 'equal_episodes' for r in results)
metrics = ['reward', 'served_demand_ratio', 'total_operator_penalty',
           'total_transition_component', 'unseen_fraction', 'steps']
per_seed = []
checkpoints = []
for result in results:
    mode, seed = result['job']['mode'], result['job']['seed']
    rows = [json.loads(line) for line in (root / 'equal_episodes' / f'{mode}_seed_{seed}' / 'episodes.jsonl').read_text().splitlines()]
    assert len(rows) == 300
    assert abs(rows[0]['epsilon'] - 1) < 1e-12
    assert abs(rows[-1]['epsilon'] - .05) < 1e-12
    assert [e['episode'] for e in result['evaluations']] == [100, 200, 300]
    for checkpoint in result['evaluations']:
        values = checkpoint['evaluations']
        assert [e['seed'] for e in values] == [6000,6001,6002]
        checkpoints.append(dict(mode=mode, seed=seed, episode=checkpoint['episode'],
                                **{key:stats.mean(e[key] for e in values) for key in metrics}))
    final = checkpoints[-1]
    per_seed.append(dict(**final, training_seconds=result['training_seconds'],
                         training_cpu_seconds=result['training_cpu_seconds'],
                         assignments=result['assignment_cache_misses'],
                         max_memory_mib=max(r['memory_mb'] for r in rows),
                         states=rows[-1]['states'], pairs=rows[-1]['pairs'],
                         forced_finishes=sum(r['forced_finishes'] for r in rows),
                         evaluation_rewards=[e['reward'] for e in result['evaluations'][-1]['evaluations']]))
modes = sorted({r['mode'] for r in per_seed})
summary = []
for mode in modes:
    group = sorted([r for r in per_seed if r['mode']==mode], key=lambda r:r['seed'])
    summary.append(dict(mode=mode, training_seeds=[r['seed'] for r in group],
                        **{key:stats.mean(r[key] for r in group) for key in metrics + ['training_seconds','training_cpu_seconds','assignments','states']},
                        reward_std_across_training_seeds=stats.stdev(r['reward'] for r in group),
                        reward_min=min(r['reward'] for r in group), reward_max=max(r['reward'] for r in group),
                        max_memory_mib=max(r['max_memory_mib'] for r in group),
                        reward_at_checkpoints={str(ep):stats.mean(r['reward'] for r in checkpoints if r['mode']==mode and r['episode']==ep) for ep in [100,200,300]}))
baseline={r['seed']:r for r in per_seed if r['mode']=='A_dense'}
paired=[]
for r in per_seed:
    if r['mode']!='A_dense':
        paired.append(dict(mode=r['mode'], seed=r['seed'], reward_difference_vs_A=r['reward']-baseline[r['seed']]['reward'],
                           served_ratio_difference_vs_A=r['served_demand_ratio']-baseline[r['seed']]['served_demand_ratio']))
analysis=dict(summary=summary, per_training_seed=per_seed, paired_differences=paired, checkpoints=checkpoints)
baseline_path = root / 'untrained_evaluation.json'
untrained = None
if baseline_path.exists():
    values = json.loads(baseline_path.read_text())
    untrained = dict(reward=stats.mean(r['reward'] for r in values),
                     served_demand_ratio=stats.mean(r['served_demand_ratio'] for r in values),
                     note='Post-hoc diagnostic only; empty Q-table, common evaluation seeds, no training.')
    analysis['untrained_diagnostic'] = untrained
(root/'comparison.json').write_text(json.dumps(analysis,indent=2),encoding='utf-8')
labels={'A_dense':'A: every action','B_committed':'B: committed changes','C_hour_end':'C: hour end'}
lines=['# Stage 2: equal-episode learning comparison','',
       'All nine jobs completed: 300 episodes per treatment per training seed (2024, 2025, 2026). Three independent CPU workers per wave; every wave includes all treatments for one training seed. Stage 3 was not run.','',
       'The objective is daily reward: higher is better. Each training seed is evaluated greedily using common independent tie-breaking seeds 6000, 6001, 6002. Average those three evaluations first, then average across the three training seeds. The independent training sample size is THREE, not nine.','',
       '| Method | Mean daily reward | Training-seed range | Mean served demand | Mean unseen evaluation states | Mean training seconds |',
       '|---|---:|---:|---:|---:|---:|']
for r in summary:
    lines.append(f"| {labels[r['mode']]} | {r['reward']:.4f} | {r['reward_min']:.4f}–{r['reward_max']:.4f} | {100*r['served_demand_ratio']:.2f}% | {100*r['unseen_fraction']:.2f}% | {r['training_seconds']:.1f} |")
lines += ['', '| Method | Seed 2024 reward | Seed 2025 reward | Seed 2026 reward |', '|---|---:|---:|---:|']
for mode in modes:
    group=sorted([r for r in per_seed if r['mode']==mode],key=lambda r:r['seed'])
    lines.append('| '+labels[mode]+' | '+' | '.join(f"{r['reward']:.4f}" for r in group)+' |')
lines += ['', '| Method | Reward after 100 episodes | After 200 | After 300 |','|---|---:|---:|---:|']
for r in summary:
    lines.append('| '+labels[r['mode']]+' | '+' | '.join(f"{r['reward_at_checkpoints'][str(ep)]:.4f}" for ep in [100,200,300])+' |')
lines += ['', '## Paired final reward differences against A','']
for mode in modes[1:]:
    group=sorted([r for r in paired if r['mode']==mode],key=lambda r:r['seed'])
    lines.append(labels[mode]+': '+', '.join(f"seed {r['seed']}: {r['reward_difference_vs_A']:+.4f}" for r in group)+'.')
lines += ['', '## Limits and interpretation','',
          'The same shortened exploration schedule was used by all treatments: epsilon reaches 0.05 after 240 episodes. This differs deliberately from Stage 1, which retained the 10,000-episode schedule and stayed highly exploratory. Do not attribute differences in Stage 1 versus Stage 2 timing solely to hardware or evaluation scheduling.','',
          'Final service quality is measured on the same fixed hourly demand used for training, not held-out demand. An unseen exact Q-table state has no learned action ranking, so greedy evaluation can still make random decisions. Read reward and coverage together with unseen-state fractions; high unseen rates limit claims of learned generalization.','',
          'Only three training seeds and 300 episodes were tested. Reward ranges and individual paired differences are reported instead of significance claims. Lower runtime does not establish better service quality or long-run convergence. Parallel timing is secondary here; Stage 1 remains the serial speed comparison. Evaluation checkpoints do not update the learner or consume its RNG.','',
          'Raw configs, logs, evaluations, source/input snapshots and detailed metrics are retained in this directory. Stage 3 is the separate equal-training-time comparison and remains unstarted.']
if untrained:
    lines += ['', '## Additional untrained diagnostic', '',
              f"After the prescribed jobs completed, an empty Q-table was evaluated with the same three evaluation seeds. No learning occurred. Its mean daily reward was {untrained['reward']:.4f}, with {100*untrained['served_demand_ratio']:.2f}% of demand served. This is a post-hoc reference, not another independent trained replication or a statistical significance test.", '',
              'A and B exceed this reference in mean daily reward; C is below it in this short study. A has the highest mean reward and served fraction after equal episodes. B exceeds A in one of three training seeds, so the small mean difference is not a consistent per-seed advantage. C has lower reward than A in all three paired seeds. The next equal-time stage is needed before selecting a method on practical efficiency.']
(root/'SUMMARY.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
print(json.dumps(analysis,indent=2))
print('Report: '+str(root/'SUMMARY.md'))
