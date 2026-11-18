# Stage 7: predictions favor stopping despite productive feasible continuations

2026-11-18. No training. Executed committed protocol/source `95f76561fc1999fdb724aae2a4d211069cb33e1f` using frozen Stage-6 weights at checkpoints 0/100/300. All 81 correctness tests passed before execution. [Protocol](stage7-stopping-diagnostic.md).

## Actual fixed trajectories

| Fixed behavior | Actions/day | Daily served | Daily reward |
|---|---:|---:|---:|
| Immediately finish every hour from empty | 24 | 0% | 0 |
| Build first reference route, then finish every hour | 33 | 20.9348% | 7.7116 |
| Replay complete strict-60 reference | 276 | 90.7308% | 19.6352 |

The single route is `[1,2,3,6,8,10,11,13]`, frequency 4, five buses. Finishing later hours retains that inherited route and keeps serving passengers. Thus FINISH_PLAN does not necessarily mean zero service; the all-empty case starts with no routes and never builds any.

At the initial empty state, the final model predicts Q(FINISH_PLAN)=.244519 versus Q(ADD_STOP(1))=.009457. Every possible starting stop has predicted Q between .009445 and .009914. FINISH is therefore the unique greedy choice. The checkpoint-100 model already shows the same ordering (.208708 versus .019952 for stop 1); initial zero weights tie all actions.

Starting at stop 1 and completing the chosen single-route continuation actually earns 7.7116 over the full day; the full reference continuation earns 19.6352. These are feasible values attainable after that initial action and therefore lower-bound its optimal undiscounted return. The model substantially underestimates that action's achievable future benefit. Its stopping prediction is also above the zero return achieved by the observed all-empty policy, but this does not prove overestimation of optimal Q(FINISH_PLAN): the agent could stop hour 1 and build routes in later hours. Fixed-continuation rank disagreements do not establish the true optimal action ranking.

After the first route has been committed, continuing the full reference earns another 19.5167 from that point; finishing every remaining hour earns another 7.5931. Prefix rewards are excluded from both suffix values. The model still ranks finishing (.293258) above the reference's next ADD_STOP(1) (.018855). Again, these are descriptive contrasts between available continuations, not exact optimal values or independent generalization tests.

## Feedback is already available during construction

The first route's rewards start with ADD_STOP(1):0, ADD_STOP(2):.019631, ADD_STOP(3):.006937, followed by further positive additions. END_ROUTE itself gives zero because the dense tentative-plan score has already credited this route. Its total hour-1 score is .118512. The full reference also includes negative intermediate adjustments (minimum -.093575), while preserving positive whole-day reward.

This rules out the claim that these examples receive no feedback until route completion. It does not explain why the training update and shared representation failed to learn useful values. Features, bootstrapping, sampling/exploration and finite training remain possible contributors; none is isolated by this diagnostic. Earlier speculation that route benefits were exclusively delayed must not be treated as a finding.

## Verification and correction

The diagnostic completed in 4.1754 seconds. All three primary trajectories (72 hourly records) passed action legality, original hourly cap, fleet/capacity/passenger accounting, reward-to-objective equality and suffix recurrence checks. The complete reference exactly reproduced its archived daily metrics, and empty replay exactly reproduced all Stage-6 final evaluations. All saved model weights stayed unchanged; no learner or visitation updates were performed. Auxiliary stop-rest probes save their daily outcome and remaining reward; the 72-hour count refers to the three primary trajectories.

The first analysis invocation failed because the reused training validator required visitation-list lengths, while this no-learner replay intentionally has no visitation observer. It left an empty scratch summary file. A disclosed post-execution correction uses explicit transport-accounting checks without fabricating visits and calculates the result before opening its output file. The corrected summary used a new filename. No diagnostic execution or raw output was changed or repeated. This correction changes analysis only; exact execution source remains recoverable.

## Decision EXP-004-D04 and next step

Keep both experimental linear variants unadopted. This diagnostic identifies a concrete prediction failure on known useful construction; it does not identify its cause or justify switching to DQN or imposing a service threshold.

Recommended next experiment: a fixed-data representational and learning-target check. Fit the same features to actual return-to-go on prespecified trajectories, with separate evaluation trajectories, and inspect whether productive starts and stopping can be distinguished. Separately trace bootstrapped update targets on fixed transitions. This can distinguish difficulty representing the relevant values from difficulty learning them with the current online update; supervised fixed-policy targets still do not equal optimal Q*. Register that design before running it. No additional training or parameter sweep was executed in Stage 7.

Raw files: `evidence/S7-stopping-run01/`; `first_reference_route.json` and `full_reference.json` contain per-action predictions, rewards, suffix returns, service plans and stop probes. `stopping-verification.json` and `analysis/summarise_stopping.py` regenerate the summary with SHA256 inventory. Dependencies, config and input/weight/source hashes retained. Source/evidence commits separate. Production unchanged; unrelated user documentation untouched. Local Git only, off-machine backup pending; no push, merge or deletion.
