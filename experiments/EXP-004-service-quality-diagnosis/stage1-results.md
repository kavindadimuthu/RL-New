# EXP-004 stage 1: completed diagnostic baseline

2026-11-17. Execution commit `578086ba1f37a1e82536870cebb743062f2e4d63`; prospective procedure in [stage1-baseline.md](stage1-baseline.md). All three fresh learners completed 300 episodes. No resource stops, failures, reruns or exclusions. This is diagnosis of the current method, not a test of a proposed fix.

## Final evaluation

Each row averages ties 7100/7101/7102 within one independently trained learner. Final mean gives equal weight to the three learner means. Percentages below partition total daily demand (165,170); capacity-constrained includes greedy assignment effects.

| Training seed | Served | No eligible path: unserved | Capacity-constrained: unserved | Unseen decisions | Mean buses |
|---|---:|---:|---:|---:|---:|
| 2034 | 32.4151% | 34.2203% | 33.3646% | 95.5631% | 17.1806 |
| 2035 | 31.2441% | 39.9701% | 28.7857% | 96.4095% | 17.0278 |
| 2036 | 32.3211% | 32.9021% | 34.7768% | 96.1831% | 17.3194 |
| Mean | **31.9935%** | **35.6975%** | **32.3090%** | **96.0519%** | **17.1759 / 99** |

Across model means, served demand ranged 31.2441–32.4151%. This range is descriptive, not a confidence interval. Training seeds are the independent units; nine evaluation ties are not nine independent trained models.

Additional registered diagnostics:

- Mean route count **7.4676 / 8**; unused fleet does not imply unlimited room for new routes.
- Forced finishes **4.4444 hours/day**; voluntarily finished **19.5556**. Their respective subgroup service means were 29.3326% and 32.5990%; groups are selected by behavior, not randomized treatments.
- Discarded unfinished routes **2.5556/day**. Signed tentative-service deltas are retained per hour, not added as causal lost passengers.
- Peak-hour service **28.7137%** for prespecified clock hours 08/09/16/17; other-hour demand-weighted service **33.6780%**.
- Rare-state decisions (<5 updates) **96.1847%**. About 219k exact Q states were stored per learner; this did not provide broad evaluation-state coverage.
- Mean daily reward **7.0165**. Reported service percentages remain demand-weighted; reward still sums equally weighted hourly service scores minus costs.

## Learning checkpoints

| Seed | Episode0 served | Episode100 served | Episode300 served |
|---|---:|---:|---:|
| 2034 | 26.3012% | 28.3623% | 32.4151% |
| 2035 | 26.3012% | 28.6031% | 31.2441% |
| 2036 | 26.3012% | 27.8404% | 32.3211% |

The identical empty-Q episode 0 evaluation is one shared no-learning reference, not three independent trained baselines. Final service exceeds that reference descriptively, while most evaluation actions remain in unseen states. No significance, convergence or held-out generalization claim. These are different training/evaluation seeds from EXP-002; do not interpret 31.99% versus its 34.26% as a controlled regression.

## Interpretation and next decision

1. **Both missing permitted connections and capacity-constrained allocation matter in these observed plans.** Serving just one category cannot explain all unmet demand. No-path keeps direction, frequency-related wait/trip cutoff and transfer rules; it does not mean the physical road network is disconnected.
2. **Limited learned guidance is directly observed.** At unseen exact states the production agent chooses randomly among valid actions even in greedy evaluation. This is a plausible planning limitation; the study has not measured a causal effect of replacing the representation.
3. **Fleet shortage at the total fleet limit is not the general explanation.** Plans nearly fill the route-count allowance while using little fleet. Route connectivity/coverage, frequency allocation and route replacement warrant investigation; this is not proof of attainable 70% or 100% service.
4. **Changing stopping alone is not yet justified as the fix.** Both voluntary and forced groups have low service. Their difference does not isolate stopping effects. The hidden action budget remains a separate formulation concern.

Next stage: register and implement a deterministic demand-guided feasible reference with the same assignment and transport constraints. Report the action budget separately if the reference is not reachable in 60 actions. It establishes achievable service, not an optimality bound. Only afterward select separate state/deadline, reward or learning treatments. Keep the proposed minimum-service finish rule deferred. No production defaults adopted.

## Runtime, resources and evidence

| Seed | Instrumented training seconds | Total process seconds | Largest recorded working set |
|---|---:|---:|---:|
| 2034 | 352.1299 | 382.1582 | 568.04 MiB |
| 2035 | 344.9338 | 374.2736 | 568.27 MiB |
| 2036 | 345.5792 | 373.9660 | 567.87 MiB |

Training sum **1,042.6429s (17.38min)**; summed process time **1,130.3977s (18.84min)**. Calendar interval from first start to last finish **18.88min**, including process-launch gaps, excluding implementation/analysis/archiving. UTC versus monotonic difference below 0.001s per process; no observed clock-gap qualification. CPU training total 1,028.75s. Timings include diagnostics and cannot be compared as an uninstrumented speed claim.

Serial CPU, one numeric thread, no GPU. Active power scheme recorded as Performance; battery status 2/100% recorded. Thermals/concurrent applications not controlled. Scoped sleep prevention restored successfully. All processes started in the same clean detached execution worktree; original worktree's unrelated documentation edits were preserved.

**22,248 hourly records validated**: 21,600 training + 648 evaluation. All checkpoints passed full learner-digest immutability, demand partition/action/visit/fleet/capacity checks. No Q-table/checkpoint export. Gzip small records and metadata total **6.04 MiB**. `baseline-verification.json` retains model/checkpoint summaries, individual timing gaps and SHA-256 inventory. Raw archive `evidence/S1-baseline-run01/` copies original outputs byte-for-byte. Registered `analysis/summarise_baseline.py` regenerates verification without training. Cross-seed source/input hashes and resolved configs were additionally compared and match. Archive regeneration matches the scratch summary exactly.

Execution source and evidence commits are separate. Local Git only; off-machine backup pending. Scratch and isolated execution worktree retained; nothing deleted, pushed or merged.
