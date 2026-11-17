# EXP-004: Low-service diagnosis and controlled improvement

Protocol v0.1 with recorded amendments, 2026-11-17, Asia/Colombo. Status: stage 0 and separately registered stage-1 preflight completed; full baseline pending. Owner: project research team.

## Question and prior knowledge

Why is daily passenger service low, and which independently tested changes improve it under the same transport constraints?

EXP-002 findings are already known: short-budget dense evaluation served about 34.3%, with about 95.7% unseen evaluation states. These motivate this investigation; this is not a blind confirmatory study. EXP-003 assignment optimizations are not treatments here. Inherited baseline: commit 24ad862, unchanged production assignment, dense feedback, exact-state tabular Q-learning.

## Stage 0: retrospective audit

Recompute all nine final A_dense evaluations from EXP-002's three independent training seeds (2027–2029), each with evaluation ties 7000–7002. Average ties within each trained model, then average three model means. Report daily served ratio, unseen fraction, mean fleet, forced finishes and actions; retain per-model values. Validate identities, finite numbers, evaluation count and passenger accounting. Record SHA-256 of source evidence and all 24 OD inputs. Compute hourly demand totals, diagonal totals, and off-diagonal totals independently. Do not train, alter evidence or claim new independent results.

The audit may run in a worktree with unrelated documentation edits: it reads only committed evidence and input CSVs and records Git status explicitly. This is an analysis-only exception, not permission for dirty model execution. Source and protocol must be committed before executing the audit. Use a unique evidence directory; never overwrite it.

## Stage 1: instrument and diagnose

Stage-0 revision 0.1a: run01 failed input validation because the CSV checkout uses CRLF while Git stores LF (`git ls-files --eol` confirmed). Preserve the failure. For CSVs only, compare after CRLF-to-LF conversion and retain both raw-file and Git-content SHA-256. Archived JSON evidence remains byte-exact. Commit the correction before run02; no model outputs or scientific thresholds changed.

Before running, commit runnable instrumentation, analysis and a stage-specific protocol amendment. Separate diagnostic categories using explicit counterfactuals: no allowed path with capacities removed, versus capacity-constrained unserved demand. These are assignment-model categories, not proven real-world causes. Record hourly demand, coverage, fleet, route count/length/frequency, peak segment utilization, action types, voluntary/forced finish, discarded tentative route, and exact-state and selected-action visit counts. Verify accounting and that instrumentation leaves actions, rewards, Q updates and RNG unchanged on matched trajectories.

Implementation/preflight amendment: [stage1-preflight.md](stage1-preflight.md), committed at `da64b82`; see report for completed checks and run. Full baseline procedure still requires its execution amendment.

Planned baseline budget: 300 episodes per fresh learner, training seeds 2034, 2035, 2036; evaluate at 0, 100 and 300 episodes using independent ties 7100, 7101, 7102. Same fixed demand as training; no held-out generalization claim. Dense baseline, inherited learning rate/gamma, epsilon 1 to .05 by episode 240, then .05. No model export. These budgets are provisional until the runnable stage amendment is committed; no stage-1 execution authorized by the audit command.

## Stage 2: feasible reference (implementation pending)

Register a deterministic demand-guided route construction and frequency-improvement algorithm before measuring it. Same network, assignment, route/frequency/fleet constraints, and transition objective as baseline. Report quality and evaluation count/runtime; do not call an unconstrained or unlimited-search reference a fair equal-compute competitor. Check whether reference plans are reachable within the baseline's 60 actions, or label them feasibility references outside its action budget. A reference is a demonstrated achievable result, not an upper bound or optimality certificate.

## Later stages: separate changes, not a combined fix

First investigate remaining-action information (deadline currently absent from state). Separately consider service-objective alignment, then knowledge-sharing representations if coverage remains poor. Each needs a prospective amendment, fixed baseline and independent seeds. Changing reward, actions, state and stopping simultaneously is excluded. Do not impose an arbitrary 90% minimum or remove safety termination before feasibility is established.

## Outcomes, resources and decisions

Primary quality outcome: demand-weighted daily served fraction. Also report original daily reward, individual hourly service, peak/off-peak outcomes, fleet/cost, unseen fraction and forced stops. Primary stage-0 output is descriptive, not a hypothesis test. Three training seeds are screening evidence, not proof of superiority. Do not pool evaluation ties as independent learners.

Future model stages: serial processes, one numerical-library thread, scoped Windows sleep prevention, CPU backend, no GPU change. Measure CPU, elapsed and UTC span separately. Preflight a complete episode before final runtime estimate; stop safely after a complete episode if total stage training exceeds 30 minutes or memory exceeds 1.5 GiB per process, preserve incomplete status. Record hardware, interpreter/dependencies, AC status and concurrent load. Check memory availability before execution. No full training starts as part of foundation setup.

Retain protocols, exact execution commits, resolved configs, source/data hashes, commands, dependencies, small metrics, failures and analysis in Git. Large Q-tables and PDFs not needed. New IDs on rerun; no silent exclusion or overwrite. Local commits are not off-machine backup; backup pending, no push authorized. No default adoption without reviewing measured quality and costs.
