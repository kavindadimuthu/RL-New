# Stage 2: equal-episode learning comparison

All nine jobs completed: 300 episodes per treatment per training seed (2024, 2025, 2026). Three independent CPU workers per wave; every wave includes all treatments for one training seed. Stage 3 was not run.

The objective is daily reward: higher is better. Each training seed is evaluated greedily using common independent tie-breaking seeds 6000, 6001, 6002. Average those three evaluations first, then average across the three training seeds. The independent training sample size is THREE, not nine.

| Method | Mean daily reward | Training-seed range | Mean served demand | Mean unseen evaluation states | Mean training seconds |
|---|---:|---:|---:|---:|---:|
| A: every action | 5.6547 | 5.2143–5.9966 | 28.32% | 95.83% | 294.7 |
| B: committed changes | 5.3766 | 4.9353–5.6591 | 24.73% | 98.21% | 190.2 |
| C: hour end | 4.3643 | 3.5751–5.1658 | 17.36% | 98.37% | 24.5 |

| Method | Seed 2024 reward | Seed 2025 reward | Seed 2026 reward |
|---|---:|---:|---:|
| A: every action | 5.7532 | 5.2143 | 5.9966 |
| B: committed changes | 4.9353 | 5.5354 | 5.6591 |
| C: hour end | 4.3521 | 5.1658 | 3.5751 |

| Method | Reward after 100 episodes | After 200 | After 300 |
|---|---:|---:|---:|
| A: every action | 5.4516 | 5.4689 | 5.6547 |
| B: committed changes | 5.0806 | 5.5119 | 5.3766 |
| C: hour end | 4.5963 | 4.7989 | 4.3643 |

## Paired final reward differences against A

B: committed changes: seed 2024: -0.8179, seed 2025: +0.3211, seed 2026: -0.3376.
C: hour end: seed 2024: -1.4011, seed 2025: -0.0485, seed 2026: -2.4216.

## Limits and interpretation

The same shortened exploration schedule was used by all treatments: epsilon reaches 0.05 after 240 episodes. This differs deliberately from Stage 1, which retained the 10,000-episode schedule and stayed highly exploratory. Do not attribute differences in Stage 1 versus Stage 2 timing solely to hardware or evaluation scheduling.

Final service quality is measured on the same fixed hourly demand used for training, not held-out demand. An unseen exact Q-table state has no learned action ranking, so greedy evaluation can still make random decisions. Read reward and coverage together with unseen-state fractions; high unseen rates limit claims of learned generalization.

Only three training seeds and 300 episodes were tested. Reward ranges and individual paired differences are reported instead of significance claims. Lower runtime does not establish better service quality or long-run convergence. Parallel timing is secondary here; Stage 1 remains the serial speed comparison. Evaluation checkpoints do not update the learner or consume its RNG.

Raw configs, logs, evaluations, source/input snapshots and detailed metrics are retained in this directory. Stage 3 is the separate equal-training-time comparison and remains unstarted.

## Additional untrained diagnostic

After the prescribed jobs completed, an empty Q-table was evaluated with the same three evaluation seeds. No learning occurred. Its mean daily reward was 4.5963, with 23.98% of demand served. This is a post-hoc reference, not another independent trained replication or a statistical significance test.

A and B exceed this reference in mean daily reward; C is below it in this short study. A has the highest mean reward and served fraction after equal episodes. B exceeds A in one of three training seeds, so the small mean difference is not a consistent per-seed advantage. C has lower reward than A in all three paired seeds. The next equal-time stage is needed before selecting a method on practical efficiency.
