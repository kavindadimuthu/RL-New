# EXP-004: Low-service diagnosis and controlled improvement

Protocol v0.1 with recorded amendments, 2026-11-17, Asia/Colombo. Status: earlier screens completed; Stage-5 linear-Q full screen stopped on stability guard, no full quality aggregate. Owner: project research team.

## Question and prior knowledge

Why is daily passenger service low, and which independently tested changes improve it under the same transport constraints?

EXP-002 findings are already known: short-budget dense evaluation served about 34.3%, with about 95.7% unseen evaluation states. These motivate this investigation; this is not a blind confirmatory study. EXP-003 assignment optimizations are not treatments here. Inherited baseline: commit 24ad862, unchanged production assignment, dense feedback, exact-state tabular Q-learning.

## Stage 0: retrospective audit

Recompute all nine final A_dense evaluations from EXP-002's three independent training seeds (2027â€“2029), each with evaluation ties 7000â€“7002. Average ties within each trained model, then average three model means. Report daily served ratio, unseen fraction, mean fleet, forced finishes and actions; retain per-model values. Validate identities, finite numbers, evaluation count and passenger accounting. Record SHA-256 of source evidence and all 24 OD inputs. Compute hourly demand totals, diagonal totals, and off-diagonal totals independently. Do not train, alter evidence or claim new independent results.

The audit may run in a worktree with unrelated documentation edits: it reads only committed evidence and input CSVs and records Git status explicitly. This is an analysis-only exception, not permission for dirty model execution. Source and protocol must be committed before executing the audit. Use a unique evidence directory; never overwrite it.

## Stage 1: instrument and diagnose

Stage-0 revision 0.1a: run01 failed input validation because the CSV checkout uses CRLF while Git stores LF (`git ls-files --eol` confirmed). Preserve the failure. For CSVs only, compare after CRLF-to-LF conversion and retain both raw-file and Git-content SHA-256. Archived JSON evidence remains byte-exact. Commit the correction before run02; no model outputs or scientific thresholds changed.

Before running, commit runnable instrumentation, analysis and a stage-specific protocol amendment. Separate diagnostic categories using explicit counterfactuals: no allowed path with capacities removed, versus capacity-constrained unserved demand. These are assignment-model categories, not proven real-world causes. Record hourly demand, coverage, fleet, route count/length/frequency, peak segment utilization, action types, voluntary/forced finish, discarded tentative route, and exact-state and selected-action visit counts. Verify accounting and that instrumentation leaves actions, rewards, Q updates and RNG unchanged on matched trajectories.

Implementation/preflight amendment: [stage1-preflight.md](stage1-preflight.md), committed at `da64b82`; see report for completed checks and run. Full baseline procedure still requires its execution amendment.

Full baseline amendment: [stage1-baseline.md](stage1-baseline.md), source/protocol/analysis committed at `578086b` before execution. All three runs completed; see [stage1-results.md](stage1-results.md). This amendment finalized the following originally provisional budget; it does not retrospectively change it.

Planned baseline budget: 300 episodes per fresh learner, training seeds 2034, 2035, 2036; evaluate at 0, 100 and 300 episodes using independent ties 7100, 7101, 7102. Same fixed demand as training; no held-out generalization claim. Dense baseline, inherited learning rate/gamma, epsilon 1 to .05 by episode 240, then .05. No model export. These budgets are provisional until the runnable stage amendment is committed; no stage-1 execution authorized by the audit command.

## Stage 2: feasible reference

Registered implementation/protocol/analysis at `e87f633` before execution: [stage2-reference.md](stage2-reference.md). Completed results and action-budget qualification: [stage2-results.md](stage2-results.md). The following foundation requirements are retained; no retrospective changes to the tested algorithm.

Register a deterministic demand-guided route construction and frequency-improvement algorithm before measuring it. Same network, assignment, route/frequency/fleet constraints, and transition objective as baseline. Report quality and evaluation count/runtime; do not call an unconstrained or unlimited-search reference a fair equal-compute competitor. Check whether reference plans are reachable within the baseline's 60 actions, or label them feasibility references outside its action budget. A reference is a demonstrated achievable result, not an upper bound or optimality certificate.

## Later stages: separate changes, not a combined fix

Stage5feature/linear-Q screen registered at `a84499b`, full execution amendment `89ebd99`: [protocol](stage5-function-approx.md), [execution amendment](stage5-full-execution.md). Preflight passed; full Lhit stability guard during49after48completed episodes, later waves not started. See [stage5-results.md](stage5-results.md); no rescue tuning or default adoption. Future stability revision requires a new prospective amendment.

Stage4remaining-action observation registered at `f274f24` before execution: [stage4-remaining-actions.md](stage4-remaining-actions.md). Six fresh runs completed; [results](stage4-results.md) and [decision](decision.md) retain failed practical-advancement screen. No default adoption. Later knowledge-reuse comparison must fix deadline handling across arms.

Stage 3 action-budget control registered at `adc8955` before execution: [stage3-reference60.md](stage3-reference60.md). Whole day recomputed from empty; original 60-step production replay passed. See [stage3-results.md](stage3-results.md). No retrospective change to Stage 2 or RL treatment adoption.

First investigate remaining-action information (deadline currently absent from state). Separately consider service-objective alignment, then knowledge-sharing representations if coverage remains poor. Each needs a prospective amendment, fixed baseline and independent seeds. Changing reward, actions, state and stopping simultaneously is excluded. Do not impose an arbitrary 90% minimum or remove safety termination before feasibility is established.

## Outcomes, resources and decisions

Primary quality outcome: demand-weighted daily served fraction. Also report original daily reward, individual hourly service, peak/off-peak outcomes, fleet/cost, unseen fraction and forced stops. Primary stage-0 output is descriptive, not a hypothesis test. Three training seeds are screening evidence, not proof of superiority. Do not pool evaluation ties as independent learners.

Future model stages: serial processes, one numerical-library thread, scoped Windows sleep prevention, CPU backend, no GPU change. Measure CPU, elapsed and UTC span separately. Preflight a complete episode before final runtime estimate; stop safely after a complete episode if total stage training exceeds 30 minutes or memory exceeds 1.5 GiB per process, preserve incomplete status. Record hardware, interpreter/dependencies, AC status and concurrent load. Check memory availability before execution. No full training starts as part of foundation setup.

Retain protocols, exact execution commits, resolved configs, source/data hashes, commands, dependencies, small metrics, failures and analysis in Git. Large Q-tables and PDFs not needed. New IDs on rerun; no silent exclusion or overwrite. Local commits are not off-machine backup; backup pending, no push authorized. No default adoption without reviewing measured quality and costs.


## Stage 6 update — 2026-11-18

Fixed smaller-step diagnostic completed 300 episodes at one seed without a numerical guard, but both trained checkpoints served 0% by immediately finishing every hour. Not adopted; no larger quality comparison launched. See [Stage 6 results and D03](stage6-results.md), [registered protocol](stage6-linear-stability.md), and `linear-stability-verification.json`. Analysis path-normalization correction is disclosed in the results.


## Stage 7 update — 2026-11-18

Frozen-model diagnostic confirms stopping is ranked above productive reference construction; fixed trajectories serve 0%, 20.9348% and 90.7308%. Positive dense rewards already occur during construction. Cause of learning failure remains unisolated. See [Stage 7 results and D04](stage7-results.md), [registered protocol](stage7-stopping-diagnostic.md) and `stopping-verification.json`. No training or adoption; analysis-only visitation-check correction disclosed.


## Stage 8 update — 2026-11-18

Fixed-return fitting corrects the initial stopping/construction preference but leaves pooled RMSE 1.0440 despite no conflicting training labels. Frozen alpha .001 updates provide tiny local corrections. No causal attribution, new online policy or adoption. See [Stage 8 results and D05](stage8-results.md), [registered protocol](stage8-return-fit.md), and `return-fit-verification.json`. Next proposed test isolates interaction features on fixed data.


## Stage 9 update — 2026-11-18

Completed preregistered three-seed return-control comparison: final served T0%,M2.7408%; relative advancement gate passed, but final absolute quality poor and all M runs declined from checkpoint100. No production adoption. All88 tests and44,496full hourly records verified; post-hoc construction/discard inspection separately labeled. See [Stage9 results and D06](stage9-results.md), [protocol](stage9-return-control.md), [full amendment](stage9-full-execution.md), and `return-control-verification.json`.
