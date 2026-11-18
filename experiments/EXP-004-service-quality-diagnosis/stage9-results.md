# Stage 9: actual-return control improves a collapsed linear baseline, but final service remains poor

2026-11-18. Source/protocol/tests/analysis `3395b8f0797473304d105e83c52fd112b2238f94`; full-execution amendment/source `2c6e6a72f8fab7a5f2f5743914c7d398b36575cd`. [Protocol](stage9-return-control.md), [full amendment](stage9-full-execution.md). All88 tests passed before execution. Production/default tabular trainer, features, reward, assignment and action rules were not changed. This comparison concerns two experimental linear learners, not replacement of the original production model.

## Treatment

T is the existing one-step max-bootstrap linear learner, alpha.001/gamma1. M buffers a whole day with weights fixed, computes each action's actual remaining-day reward, then performs one chronological every-visit gradient pass at alpha.001 using the same unit-normalized32features/eight action blocks. No reference demonstrations, max-record updates, new priorities, new features, clipping or parameter sweeps. Returns do not stop at hourly boundaries. M learns from exploratory future actions and updates after a day; T bootstraps toward the best predicted next action online. Those timing/policy differences are bundled with the target change, so this is not an isolated target-only causal comparison or exact reproduction of Yoo et al.

## Operational preflight

Two25-episode runs at seed2034 completed, with checkpoints0/25 and three evaluation tie seeds each. All1488hourly records verified. T matched historical Stage6 first25 exactly; initial evaluations/first fully exploratory-day physics matched. Parent53.7162s. M training40.7790s, T15.4120s; finite weights and RAM below guards. The unchanged full screen was committed after this check; no tuning or pooling from preflight quality. Small artifacts in `evidence/S9P-return-control-run01/`.

## Complete full comparison

Fresh three independent training seeds per method;300episodes each; checkpoints0/100/300 with ties7100/7101/7102. Two single-thread CPU children per wave, three serial waves, no GPU. All six learners completed without numerical/resource stops. No replacements or retries. Final values average evaluation ties within each learner; ties happened to give identical final outcomes, not additional independent trained models.

| Training seed | T served at300 | M served at100 | M served at300 | M daily reward at300 | M forced finishes/day at300 |
|---|---:|---:|---:|---:|---:|
|2034|0%|23.8294%|5.0154%|.154080|20|
|2035|0%|35.1426%|2.5646%|.382148|24|
|2036|0%|39.1705%|.6424%|.194792|24|
|Mean|0%|32.7142%|2.7408%|.243673|22.6667|

All T final rewards are0. Paired final service gains are+5.0154,+2.5646,+.6424percentage points, mean+2.7408pp (range+.6424 to+5.0154pp, a range across model means, not a confidence interval). Mean reward difference+.243673. The **preregistered practical-advancement screen passes**: mean gain>=2pp, no negative paired service difference and mean reward not lower. This remains a small screening result relative to a degenerate comparator, not statistical superiority or production readiness. We do not add a post-hoc requirement and pretend the registered gate failed.

Absolute final service is poor and declines from checkpoint100 in all three M runs. The common untrained evaluation served26.3012%; these final trained policies are worse than that recorded diagnostic reference. Mean empty hours at300 is15/24 for M versus24/24 for T. M final mean fleet by seed3.5,5.1667,.2917buses; no full empty day in M evaluations, but limited committed service. High action counts do not imply useful planning. Historical original-tabular baseline served31.9935% in Stage1; this is context only, not another contemporaneous arm or a matched update comparison.

## Post-execution behavior inspection

Explicitly post-hoc, not an advancement metric: `analysis/audit_return_behavior.py` regenerates `return-behavior-posthoc.json` from final evaluations. M total actions/day1214,1440,1440. Discarded unfinished routes20,23,24. Each first hour has only additions/removals and no committed route: ADD/REMOVE counts31/29,33/27,34/26. In those hours, the60-action cap ends construction and discards the unfinished route, with zero service.

Across the day M additions/removals are611/505,740/653,767/672; END_ROUTE counts13,5,1. Thus these final policies often continue construction without completing useful routes. Aggregated counts do not preserve an exact selected-action order, so do not invent particular cycles or prove a causal mechanism. Realized rewards, shared function approximation, exploration and update timing are not isolated causes here. The result does not show that all Monte Carlo methods fail or that forcing construction/finishing would solve the objective.

## Verification, resources and retention

All1800training days plus54evaluation days =44,496hourly records validated. Every retained M update target matched its actual suffix reward, actual day terminal target matched immediate reward, hourly/day reward accounting matched final committed objectives, finite snapshots and evaluation immutability passed. T seed2034 reproduced Stage6 all300metrics and checkpoints exactly. Paired initial zero-model/first fully exploratory-day physics and configs/input hashes matched. Registered analysis completed without correction.

Full parent elapsed1485.8341s =24.76minutes, near the lower end of the amended25–35minute projection; preflight adds.90minute. Summed child training1482.3751s =24.71minutes, including collection and updates but excluding checkpoint evaluation and audit serialization. Summed process CPU1572.4219s =26.21minutes; process elapsed, training and CPU boundaries are distinct. T training by seed30.3300/31.6328/30.8114s; M373.7589/565.9178/449.9241s. No wall/performance-clock gaps of practical size. Scoped awake restoration recorded for all children. Performance power plan and AC battery state observed; no global power change.

Maximum recorded working set572.48MiB; final M weight norms28.6428/28.4807/26.7111, no registered Q/row guard failure. Recorded post-episode RAM is not a continuous peak-memory measurement of M's temporary trajectory buffer. Runtime is not a speedup: M does more planning and a different update. No multicore scaling claim from two concurrent children, and no claim GPU would help.

Full archive85original files,42,060,471bytes (40.11MiB), exceeding prospective10–30MiB because every-transition target audits were retained as registered. Reviewed largest compressed target audit11,153,910bytes; none is a large Q-table, PDF or full resume checkpoint. Preflight25files2,709,422bytes. Keep these original compact numerical outputs; no deletion or hidden exclusion. Small256weight checkpoints retain exact parameters, not full resume state. Archive summaries regenerate exactly and raw Git bytes/SHA256 inventories checked. Local Git only; off-machine backup pending. No push, merge, deletion or unrelated user-documentation staging.

## Decision EXP-004-D06

Keep episodic return regression as a candidate that passed its relative screen; **do not adopt it as the production default**. Direct realized-return learning reduced immediate empty-plan behavior compared with the collapsed linear TD control, but final useful service is still very low and deteriorated with further training in all three runs. This experiment did not solve low served demand. Do not select checkpoint100 after seeing the decline and present it as the preregistered final result.

Recommended next diagnostic: replay frozen checkpoint100 and300 decisions on the same construction states, comparing END_ROUTE against repeated ADD_STOP/REMOVE_LAST_STOP choices and actual feasible route-completion continuations. This can target the newly observed unfinished-route failure before changing masks, features, rewards or action priority. Existing Stage8 representation limitations remain relevant. A changed feature/update or early-checkpoint-selection rule needs another prospective experiment; no automatic extra training in this stage.

Raw full outputs: `evidence/S9-return-control-run01/EXP-004-S9-{T|M}-seed<seed>-run01/`. Each `evaluation-300.json` contains all final full-day service plans; `evaluation-100.json` retains the earlier checkpoint. `return-control-verification.json` is the registered summary, and `return-behavior-posthoc.json` is the separately labeled behavior inspection. Results belong to the study branch with source and evidence commits separated.
