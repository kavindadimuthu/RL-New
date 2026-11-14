# Stage 3: equal-training-time comparison

All nine jobs completed: 120 training seconds per treatment per seed (2024, 2025, 2026), in three concurrent-worker waves. Complete the current episode before stopping; exact overshoot is recorded. Evaluation/reporting are outside the training budget.

All treatments use the same elapsed-training-time exploration schedule, reaching epsilon 0.05 at 96 seconds. A fresh learner starts each job. Three common independent greedy-evaluation seeds (6000, 6001, 6002) are averaged within each training seed, then results are averaged across the three training seeds. The independent training sample size is three.

| Method | Mean final reward | Training-seed range | Demand served | Mean episodes | Mean training seconds | Unseen evaluation states |
|---|---:|---:|---:|---:|---:|---:|
| A: every action | 5.4579 | 5.2758–5.5632 | 25.85% | 109.0 | 120.64 | 97.46% |
| B: committed changes | 4.7901 | 3.8650–5.7344 | 21.40% | 178.7 | 120.53 | 98.47% |
| C: hour end | 1.0102 | 0.9322–1.0677 | 4.09% | 1942.7 | 120.03 | 0.00% |

| Method | Seed 2024 reward | Seed 2025 reward | Seed 2026 reward |
|---|---:|---:|---:|
| A: every action | 5.2758 | 5.5632 | 5.5348 |
| B: committed changes | 4.7710 | 5.7344 | 3.8650 |
| C: hour end | 0.9322 | 1.0677 | 1.0308 |

| Method | Reward at 40 training seconds | At 80 | At 120 | Peak worker RAM MiB |
|---|---:|---:|---:|---:|
| A: every action | 4.9262 | 5.7935 | 5.4579 | 345.5 |
| B: committed changes | 5.0228 | 5.0843 | 4.7901 | 385.4 |
| C: hour end | 4.7614 | 3.6622 | 1.0102 | 1203.6 |

## Paired final reward differences against A

B: committed changes: seed 2024: -0.5048, seed 2025: +0.1711, seed 2026: -1.6698.
C: hour end: seed 2024: -4.3436, seed 2025: -4.4955, seed 2026: -4.5039.

## All-stage overview

| Method | Stage 1: serial seconds / 100 episodes | Stage 2: reward after 300 episodes | Stage 3: reward after 120 training seconds |
|---|---:|---:|---:|
| A: every action | 80.12 | 5.6547 | 5.4579 |
| B: committed changes | 59.20 | 5.3766 | 4.7901 |
| C: hour end | 6.99 | 4.3643 | 1.0102 |

## Limits

Stage 1 uses the original episode-based exploration schedule. Stage 2 uses a shared shorter episode-based schedule. Stage 3 uses a shared time-based schedule. Compare treatments WITHIN a stage; changes between stages include exploration timing as well as available training experience.

Same input demand is used in training and evaluation; this measures fixed-problem optimization, not held-out generalization. Exact raw states make new combinations unseen by the Q-table; greedy ties/unseen states still introduce randomness. High unseen-state fractions require caution in interpreting learning.

Three training seeds are insufficient for a definitive statistical ranking. Individual paired results, reward ranges and served-demand ratios matter alongside averages. These are short-budget screening results, not convergence measurements. End-of-episode stopping gives small unequal overshoots; consult exact time and CPU-time fields. Worker timing is subject to shared laptop resources.

The next decision should consider service quality and repeatability together with time and memory. Raw source/input snapshots, configurations, episode logs, all evaluation checkpoints and resource measures remain available. No further training stage was started.

## Final policy behavior

| Method | Mean evaluation actions per day | Mean operating fleet per hour | Mean forced hour endings per day |
|---|---:|---:|---:|
| A: every action | 833.8 | 15.31 | 5.78 |
| B: committed changes | 763.3 | 13.02 | 5.67 |
| C: hour end | 29.7 | 1.93 | 0.00 |

## Observed outcome and recommendation

In this completed short-budget comparison, A has the highest average final reward and demand served in both learning stages. B has lower mean reward but beats A in one of three training seeds in each learning stage; the data do not establish a definitive long-run A-versus-B ranking.

C is much faster per episode, yet its additional episodes did not compensate for delayed feedback in this protocol. All three final greedy policies use very few daily actions (mean 29.7), operate about two buses per hour, and serve about 4.1% of demand. Zero unseen-state fraction in C means those short evaluation trajectories were memorized, not that broad state-space coverage was achieved. Early hour completion with limited service is consistent with the observed low-action policies; these measurements do not establish the precise learning mechanism or an inevitable failure of hour-end rewards.

Retain A as the current default. Prioritize speeding up its assignment implementation while preserving results; retain B as a candidate for further validation. Do not adopt C solely for its timing advantage. A and B still have very high unseen-state fractions, so exact-state coverage is a separate issue from simulator speed. These recommendations are limited to the tested budget, schedules, fixed demand and three training seeds.

The separate empty-Q-table reference from Stage 2 scored 4.5963 and served 23.98% of demand using the same three evaluation seeds. This post-hoc reference is not an additional trained replication.
