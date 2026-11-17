# EXP-004 Stage 5: linear-Q stability stop

Status 2026-11-17: **full quality comparison incomplete; registered stability stop reached**. No model adopted. Prospective protocol [stage5-function-approx.md](stage5-function-approx.md), preflight source `a84499b`, full amendment/source `89ebd99fcce170e410df80f6fd0fa2b580d675a2` in [stage5-full-execution.md](stage5-full-execution.md). This was normalized linear Q, not DQN.

## What was tested

E: exact table with remaining hourly actions (equivalent to Stage4B). L: same deadline-aware raw inputs represented by 32 fixed normalized features and 256 shared weights across eight action types. No candidate-plan scoring, heuristic hints, warm start, reward change, neural network, experience replay or target network. Encoding and approximation were bundled, so even a successful trial would not isolate the benefit of sharing from feature selection.

All 78 tests passed before source commit. Tests established pure/no-assignment features, normalized updates, learned prediction on an unvisited key, masks, zero-model/random-policy consistency and immutable evaluation including weights.

## Operational preflight

Both arms completed two episodes at seed 2034 using the 300-episode epsilon schedule, with checkpoint 0/2 evaluation ties 7100/7101/7102. All 384 hourly records verified. E reproduced historical metrics; empty-model evaluations and first fully random episode physics matched E/L. No numerical guard hit. Parent elapsed 13.3907s; measured two-episode training E 2.3331s, L 3.0345s. No feature/alpha/guard changes were made from preflight service results. Preflight was not pooled into full results.

## Full execution outcome

| Run | Outcome | Evidence |
|---|---|---|
| E, seed 2034 | Completed 300 episodes and checkpoints 0/100/300 | Reproduced historical Stage-4 B same-seed quality/count/checkpoint outcomes exactly |
| L, seed 2034 | 48 complete episodes; failed during 49 | `FloatingPointError('Registered linear Q stability guard exceeded')` |
| E/L, seeds 2035/2036 | Not started | Registered stop on child failure; no replacements or retries |

An estimated Q value exceeded the preregistered absolute bound 1,000. Parameter values remained finite; final maximum weight-row norm 1,103.15 was below the separate 10,000 row bound. The exact offending state/action/Q magnitude was not saved, so no exact trigger value is claimed. A bounded finite-day return does not justify treating such growing predictions as trustworthy.

The already-running E control was allowed to finish, as the procedure specified stopping future waves. No clipping, learning-rate adjustment, alternate algorithm or silent rerun was used to rescue L. It did not reach a trained checkpoint 100/300. **No final three-pair service comparison, significance result or practical-advancement assessment is available.** Last training-episode service is not substituted for missing greedy evaluation.

Post-execution failure audit (explicitly post-hoc) validated 8,640 retained hourly records: 348 complete training days ×24 plus 12 evaluation days ×24. E has 300 training days and 9 evaluations; L has 48 complete training days and only 3 initial untrained evaluations. Partial episode 49 was not retained as a complete day.

## Observed numerical growth

| L point | Whole weight-vector L2 norm |
|---|---:|
| Episode 1 end |1.3468 |
| Episode 10 end |18.0183 |
| Episode 25 end |120.9834 |
| Episode 48 end |2,729.9310 |
| Failure-time stored parameters |2,929.7705 |

This is observed instability/growth within this implementation, not proof of asymptotic divergence or that all feature models fail. Off-policy Q-learning with linear approximation can be unstable in known examples ([Precup, Sutton and Dasgupta](https://cseweb.ucsd.edu/~dasgupta/papers/offtd.pdf)); this run does not isolate the causal roles of step size, gamma, features and bootstrapping. Unit tests do not establish convergence.

The protocol called the failure snapshot 'stable pre-exception'; the saved file is actually the **last stored finite parameters at failure, not a certified stable or safe policy**. No rollback occurred. Keep this qualification with the raw weights; do not deploy them.

## Resources and metadata qualifications

Whole paired wave 355.9923s (**5.93min**), E process 354.6191s and L 100.8362s. Completed-episode training E 325.7889s and L 93.7130s; L's partial episode 49 is outside its summed completed-episode training timing. Training/data/RAM guards were not the failure cause. Latest complete L working-set record 324.39 MiB, below the 1.5 GiB limit, with over 12,000 MiB free RAM. Serial seed waves/two CPU workers, one numeric thread each, no GPU. Timings are not an equal-compute performance comparison.

E explicitly recorded sleep-scope restoration. L's exception manifest lacks `sleep_scope_exited`; the tested context manager runs restoration in `finally`, and no restoration error replaced the numerical exception, but no explicit success flag was recorded. We did not add one retrospectively. Improve exception instrumentation in a future revision.

## Decision and next direction

Do not advance or adopt this unstable L variant. Production/default RL, assignment and stopping rules remain unchanged. This is a stability result, **not evidence that generalization is useless or that DQN failed**. The feature model did share predictions on novel inputs in tests/preflight, but useful/stable learning was not established.

Next design a separately preregistered stability-focused revision before another quality screen, keeping features/demand/reward fixed to identify the update change. Stabilizers or an alternative update require their own protocol and tests; no automatic architecture/learning-rate switch in this record. Do not simply launch a larger neural run or impose a service threshold from this failure.

## Raw outputs and reproduction

- `evidence/S5P-function-approx-run01/`: complete operational preflight and small L weights.
- `evidence/S5-function-approx-run01/`: parent failure manifest, E complete outputs, L partial metrics/gzip hours, initial evaluation and final stored weights.
- `function-approx-verification.json`: registered incomplete-study result; no normal final aggregate.
- `linear-failure-audit.json`: post-execution partial-evidence checks and weight-growth summary.
- `analysis/summarise_function_approx.py` and post-hoc `analysis/audit_linear_failure.py` regenerate these records without training. Archived summaries/checksums match scratch exactly.

Execution/evidence commits separate. Small weights are not full resume checkpoints. No large Q exports, PDFs or UI. Local Git only, off-machine backup pending; no push/merge/deletion. Failed results retained and user documentation edits untouched.
