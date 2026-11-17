# EXP-004 Stage 4: remaining-action observation result

Completed 2026-11-17. Prospective protocol: [stage4-remaining-actions.md](stage4-remaining-actions.md). Execution source `f274f24eda3bd3f66b57ac30a31e06cc1d27f3ff`. All six fresh learners completed 300 episodes and checkpoints 0/100/300, with three evaluation ties each. No failed/incomplete runs, resource stops, reruns or exclusions. Production state/trainer/config unchanged.

**Adding remaining hourly actions to the exact Q-table key did not demonstrate a consistent practical improvement under this budget.** The preregistered advancement screen failed. This is a finite-budget screening result, not proof that deadline information is unnecessary or harmful in general.

## Final comparison

A uses the original six-field key. B appends remaining hourly actions. All other planning/learning settings, reward, valid actions, assignment and 60-step deadline were fixed. Ties averaged within each learner, then three learner means; three paired seeds, not 54 independent trained models.

| Metric | A: original | B: plus remaining actions |
|---|---:|---:|
| Daily served | **31.9935%** | **31.7762%** |
| No eligible path: unmet / total demand | 35.6975% | 39.7316% |
| Capacity-constrained: unmet / total demand | 32.3090% | 28.4922% |
| Original daily reward | 7.0165 | 7.0099 |
| Decisions in unseen states | 96.0519% | 96.4287% |
| Decisions in states with <5 updates | 96.1847% | 96.6409% |
| Forced hour endings/day | 4.4444 | 5.3333 |
| Discarded unfinished routes/day | 2.5556 | 2.6667 |
| Mean fleet /99 | 17.1759 | 17.1389 |
| Mean routes/hour | 7.4676 | 7.4120 |
| Mean actions/day | 826.5556 | 853.8889 |
| Peak-hour service (08/09/16/17) | 28.7137% | 27.4357% |
| Other-hour service | 33.6780% | 34.0055% |
| Mean final Q states/learner | 219,453.3 | 247,733.7 |
| Mean final Q state-action pairs | 236,810.7 | 248,060.3 |
| Mean largest recorded working set | 568.00 MiB | 583.58 MiB |

## Paired seed outcomes

| Training seed | A served | B served | B−A percentage points | A reward | B reward |
|---|---:|---:|---:|---:|---:|
| 2034 | 32.4151% | 29.1381% | −3.2770 | 7.5767 | 6.4312 |
| 2035 | 31.2441% | 34.7794% | +3.5352 | 6.6721 | 7.6136 |
| 2036 | 32.3211% | 31.4111% | −0.9100 | 6.8007 | 6.9849 |
| Mean | 31.9935% | 31.7762% | **−0.2172** | 7.0165 | 7.0099 |

One seed improved, two decreased. Paired service range −3.2770 to +3.5352 points is descriptive, not a confidence interval. No significance or convergence claim. Criterion registered before execution required mean service improvement ≥2 points, no paired seed decrease, and mean reward not lower; all three conditions were unmet. `screening_advance=false`.

## Integrity and interpretation

- All 44,496 hourly records verified: 43,200 training + 1,296 evaluation. Training 1,800 episodes; 54 evaluation days include all three checkpoints, not just final evaluations.
- Fresh A reproduced every same-seed S1episode reward/steps/unseen/Q-count/hourly-reward record exactly, and all checkpoint daily outcomes exactly; timing/memory intentionally excluded. This supports control integrity despite the new experimental loop and paired CPU scheduling.
- Empty-Q evaluations and fully exploratory first-episode physics match A/B. Treatment keys reset correctly at voluntary/forced transitions; fixed actions preserve transport/reward. All evaluations passed full learner digest immutability.
- All worker configs/source/input hashes match, clean same execution checkout, original deadline/reward/assignment unchanged. No heuristic search, hints or warm start added to either method.

B stored about 12.9% more exact Q states and still faced roughly 96% unseen-state decisions. More fragmented tabular experience is consistent with the coverage concern, but trajectories also differed; the experiment does not separately quantify why B changed quality. Exposing a meaningful deadline does not itself provide generalization between similar plans. Stopping/discard diagnostics show no improvement in their averages either.

The previously demonstrated 90.73% strict-budget heuristic service remains a descriptive attainable-quality reference with different candidate-search access. This trial did not attempt to imitate it or match its compute procedure.

Decision: retain A as the current default/baseline; do not advance B as a standalone practical improvement from this screen. Preserve B and the hidden-budget formulation concern for future work. Next investigate knowledge reuse/generalization in a separately preregistered comparison, holding deadline observation identical between its arms rather than combining representation and reward/stopping changes. No new treatment executed here.

## Runtime and retained evidence

Three serial seed waves, two independent CPU workers per wave, one numeric thread each; no GPU. Critical-path runner elapsed **1,240.9322s (20.68min)**; UTC span 1,240.9067s. Sum of child measured training elapsed **2,219.4016s (36.99min)** and child CPU **2,374.3438s (39.57min)**. Overlap is intentional; do not sum child times as calendar time or compare paired timings with old serial runs as speed superiority. Individual clock gaps below 0.001s. All sleep-prevention scopes restored. Power/battery observations retained; thermals/concurrent applications uncontrolled.

Largest recorded working set across runs 584.54 MiB, below the 1.5 GiB guard. Data/archive about **11.92MiB**, no large model exports, PDFs or UI. No resource stops; no causal speed claims.

Raw `evidence/S4-remaining-actions-run01/` contains parent `study-manifest.json` and six `EXP-004-S4-{A|B}-seed{2034|2035|2036}-run01/` directories. Each has `evaluation-300.json` (all final plans), earlier checkpoints, `episodes.jsonl`, gzip full hourly training records, config, manifest, hashes and dependency lock.

`remaining-actions-verification.json` retains per-model/checkpoint/paired summaries, screening decision and raw SHA-256 inventory. Registered `analysis/summarise_remaining_actions.py` regenerates the archive exactly without training. All 72 tests passed before execution. Evidence/source commits separate; local Git backup only, off-machine backup pending. No push/merge/deletion; unrelated user docs retained untouched.
