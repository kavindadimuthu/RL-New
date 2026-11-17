# EXP-004 Stage 2: feasible-reference result

Completed 2026-11-17. Execution source `e87f6339a5ff12fa5cc9941b1428b68fc3c135a2`. Prospective algorithm, search budget and action-budget qualification: [stage2-reference.md](stage2-reference.md). All 24 hours completed; production-action replay and registered analysis passed. One deterministic run, no reruns, excluded attempts, training or parameter sweep.

**The reference serves 81.51% under the original transport limits, but its first hourly plan requires 105 accepted actions rather than RL's 60.** This is an achievable transport-feasibility reference outside the original first-hour action budget, not a fair equal-action-budget superiority claim. Subsequent 23 traces are within 60 actions but inherit the over-budget first plan; they do not independently establish whole-day reachability under the original deadline.

## Measured comparison

RL column is the registered Stage-1 average of three model means (each averaging three evaluation ties). The deterministic reference is one procedure, not three independent samples. Same fixed demand, same hourly objective, same production assignment and transport constraints; different planning/search/learning budgets.

| Metric | RL baseline, 300 episodes/model | Reference |
|---|---:|---:|
| Daily demand served | 31.9935% | **81.5075%** |
| No eligible path: unserved / total demand | 35.6975% | **18.0263%** |
| Capacity-constrained: unserved / total demand | 32.3090% | **0.4662%** |
| Average hourly fleet /99 | 17.1759 | **34.0000** |
| Mean routes/hour | 7.4676 | **8.0000** |
| Original daily reward | 7.0165 | **18.6476** |
| Peak-hour served (08/09/16/17) | 28.7137% | **76.6714%** |
| Other-hour served | 33.6780% | **83.9915%** |

Served **134,626 of 165,170**, leaving 30,544 unserved. Daily difference versus RL mean **49.5141 percentage points**, descriptive and action-budget-qualified. Reference maximum fleet 62/99. Lowest hourly service 75.8767% at 15:00; all 24 reference hours exceed 70% in this expanded-first-hour replay. That does not establish feasibility under 60 actions, a universal target for other demands, or 100% attainability. This heuristic and candidate pool are not exhaustive; the remaining 18.49% unmet demand is not an unavoidable lower bound.

## Search and replay evidence

- **6,108 candidate-plan score requests** across the day; no hour reached the 2,000-request or 120-edit budget. Assignment cache counts 295 hits/5,814 misses include the one initialization evaluation, hence 6,109 total lookups.
- **318 accepted production actions**, including all 24 FINISH_PLAN actions. First hour 08:00 used 105; other hours used 1–39. Search includes rejected alternatives, so 318 is not its total computational cost or a proven minimum action count.
- All accepted route edits/frequency steps replayed through original masks. Final routes/order/frequencies, original hourly scores, passenger counts and daily telescoped reward match search outputs. No forced finish in the extended replay. Replay limit 105 saved explicitly; original limit 60 also saved.
- **Same inputs, dependency lock, transport config and production source hashes** as Stage 1, allowing only machine-local data/results paths in config comparison. No reward or transport assumptions relaxed. Extended action deadline is a separate, explicit planning-budget difference.
- **51.3612s total**, 50.2344s CPU; search 48.4463s and replay 2.3704s. UTC/monotonic gap −0.000014s; no timing qualification indicated. Largest recorded working set 123.69 MiB. One CPU process, one numeric thread, no GPU; scoped sleep prevention restored. Active Performance power scheme recorded; AC/thermals/concurrent load not controlled. This is not an equal-compute experiment against RL training.

## Interpretation and next decision

The original evaluator/objective permits a much higher-service, higher-score plan than the observed learner produced, under the transport constraints and an extended first-hour action allowance. Poor RL results cannot be attributed solely to those transport limits. Route construction and frequency allocation jointly improved; this run does not identify their separate causal contributions. High exact-state novelty remains an observed learning limitation, not a quantified explanation of the whole gap.

The next useful control is a **prospectively registered reference restricted to 60 accepted actions each hour, starting from the same empty initial plan**, rather than clipping this result or retaining its expanded-budget first plan. Compare that controlled reference before attributing the gap to learning or changing termination. Then select separate RL state/deadline, representation or reward experiments. Do not install a 70% finish rule from this result alone. No production defaults changed or reference adopted as a replacement.

## Raw evidence and reproduction

- `evidence/S2-reference-run01/service-plan.json`: complete saved hourly routes, frequencies, buses, passenger outcomes and diagnostics; daily summary and deadline qualification.
- `search-hours.jsonl`: per-hour search requests, accepted edits/scores, full accepted production-action traces, timing/resource records and budget flags.
- `route-candidates.json`, `config.json`, `manifest.json`, `source-input-sha256.json`, `requirements-lock.txt` retain candidate pool and provenance.
- `reference-verification.json`: registered summary/comparison, qualification and raw SHA-256 inventory. Raw archive about 259 KiB.

`analysis/summarise_reference.py` regenerates the summary from archived files without planning/training. Verified archived summary equals original scratch summary, including checksums. Execution and evidence commits are separate. Scratch/execution worktree retained. Local Git only; off-machine backup pending, nothing pushed or merged. Existing unrelated docs remain untouched.
