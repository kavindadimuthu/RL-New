# EXP-004 Stage 3: strict 60-action reference

Completed 2026-11-17. Protocol: [stage3-reference60.md](stage3-reference60.md). Execution source `adc89555232744f7bd23ef472ce60b89631a7071`. One deterministic run; all 24 hours completed. No failures, reruns or post-result retuning. Production environment, assignment, reward and defaults unchanged.

**90.7308% of daily demand served, within 60 accepted actions in every hour.** Started from the same empty plan; no warm start from Stage 2. Full production replay used the original deadline of 60, without forced finishes or discarded routes.

## Comparison

| Metric | RL mean, 300 episodes/model | Stage 2 reference | Stage 3 reference60 |
|---|---:|---:|---:|
| Daily served | 31.9935% | 81.5075% | **90.7308%** |
| No eligible path: unserved / total demand | 35.6975% | 18.0263% | **3.9644%** |
| Capacity-constrained: unserved / total demand | 32.3090% | 0.4662% | **5.3048%** |
| Mean hourly buses /99 | 17.1759 | 34.0000 | **43.2917** |
| Mean routes/hour | 7.4676 | 8.0000 | **8.0000** |
| Original daily reward | 7.0165 | 18.6476 | **19.6352** |
| Peak service (08/09/16/17) | 28.7137% | 76.6714% | **79.3459%** |
| Other-hour service | 33.6780% | 83.9915% | **96.5782%** |
| Maximum accepted actions/hour | 60 | 105 | **60** |

Served **149,860 / 165,170**, leaving **15,310** unserved. Difference versus RL mean: **58.7373 percentage points**; versus Stage 2: **9.2232 points**. Descriptive, not significance results. References are single deterministic executions, not independent trained samples. Matching transport and accepted-action limits does not match compute or information: the heuristic scores alternatives before choosing edits, unlike the RL policy.

## Search and replay checks

- **276 accepted production actions**, including all 24 FINISH_PLAN actions. First hour 08:00 used 60; all others used 1–29. Complete edits only; no clipped route or replacement.
- **5,041 score requests**, within the 2,000/hour ceiling; no hour reached the 120-edit ceiling. Sixteen over-budget edit encounters skipped (not necessarily distinct edits). Only the first hour exhausted its action allowance.
- Every accepted action passed production masks. Plan identity/order/frequencies, fleet, passengers, original hourly scores and telescoped daily reward matched search outputs. Original/replay limits both 60.
- Same candidate pool bytes and search knobs as Stage 2. Production config/source/input/package checks match Stage 1, except local data/results paths.
- Cache 239 hits/4,803 misses includes one setup lookup, hence 5,042 lookups. Accepted actions alone are not total search cost or a proof of minimum required actions.

## Interpretation and next direction

A much higher-service, higher-score day is demonstrably feasible under the original transport constraints and 60-action limit. That limit alone cannot explain RL's roughly 32% daily service. This does not isolate contributions of state representation, exploration, reward or stopping; high unseen-state rate remains separate evidence of limited learned guidance.

Stage 3 exceeded Stage 2 because the constraint changed the greedy sequence and inherited plans. Local hourly improvement does not guarantee a better whole day. This is not proof that 60 is generally better than 105 or that this heuristic is optimal.

**Daily 90.73% does not mean every hour met 70%.** At 08:00, service was 8,154/15,569 (**52.3733%**) after all 60 actions. Next-lowest hour 09:00 served 87.6468%. This does not prove 70% is infeasible at 08:00; it shows why a daily average cannot justify a universal finishing threshold.

Retain reference60 as a quality baseline. Next preregister separate RL formulation/learning treatments: remaining-action information is a known concern; knowledge reuse needs separate investigation. More state information can worsen table coverage, so measure quality and unseen decisions rather than promise improvement. No RL treatment or minimum-service threshold adopted here.

## Runtime and evidence

Elapsed **35.4684s**, CPU 34.3750s; search 32.9638s, replay 1.9790s. Maximum recorded working set 114.23 MiB. UTC/monotonic gap −0.000016s. Serial CPU, one numeric thread, no GPU, clean checkout, scoped sleep prevention restored. Power scheme recorded; AC/thermals/concurrent load uncontrolled. Not an equal-compute performance test.

Raw `evidence/S3-reference60-run01/` contains `service-plan.json` (complete hourly plans), `search-hours.jsonl` (edits/actions/search counts/skips/timing), candidates, config, manifest, hashes and dependency lock. About 250 KiB; no model exports, PDF or UI.

`reference60-verification.json` retains comparison and raw SHA-256 inventory. Registered `analysis/summarise_reference60.py` regenerates results exactly without planning/training. All 67 tests passed before execution source commit. Archive checksums match scratch outputs. Separate execution/evidence commits. Local Git only, backup pending; no push/merge/deletion. Existing user docs unchanged.
