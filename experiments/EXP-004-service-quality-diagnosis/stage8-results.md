# Stage 8: partial representation capacity and small bootstrap corrections

2026-11-18. Execution/source/protocol/analysis commit `51ae878`. [Prospective protocol](stage8-return-fit.md). All 84 tests passed before execution. No online RL training or production changes. Fixed-data fitting and frozen-target audit completed in .7158 seconds, excluding command startup. One CPU numeric thread, no GPU. All 72 primary hourly records and saved summaries verified without analysis amendments or research reruns.

## What was fitted

Training: 24 all-empty stopping transitions and 33 transitions building `[1,2,3,6,8,10,11,13]` at frequency 4 and then retaining it. Targets are actual remaining-day rewards. The second route `[1,2,3,6,8,10,11]` was excluded from pooled training; its 32 transitions serve 19.3685% and earn 6.9349. Training-route service/reward remain 20.9348%/7.7116, empty 0/0, exactly reproducing Stage 7.

There are 57 unique training state/actions and 57 unique training feature vectors, with no contradictory duplicate labels. Evaluation shares seven initial state/action pairs and feature vectors with training; their continuation returns differ because routes later diverge. These are fixed-controller target differences, not proof of feature aliasing. Report 25 nonoverlapping evaluation rows separately. This same-network, same-demand, closely related single route is a limited diagnostic, not a blind or statistically independent quality experiment.

## Directly fitting returns changes the initial ranking

| Initial decision | Frozen Stage-6 Q | Pooled OLS fit | Known continuation return |
|---|---:|---:|---:|
| Finish from empty, keep finishing | .244519 | .922128 | 0 |
| Start at stop 1, build training route | .009457 | 7.711633 | 7.711633 |

Fixed ridge .001 also ranks construction higher: 7.707513 versus 1.021019. Therefore the existing representation can express this particular preference when supplied direct future-return labels. These fitted numbers are not values from an evaluated online policy; do not claim that supervised fitting solved planning or achieved new service results.

## The features do not fit all examples well together

| In-sample fit | OLS RMSE | OLS maximum error |
|---|---:|---:|
| Empty trajectory alone | 0 | 0 |
| Training route alone | .042158 | .106740 |
| Both training trajectories together | 1.044027 | 2.380090 |
| Evaluation route alone, using its own labels | .032248 | .072330 |

Pooled zero-predictor RMSE is 4.638831, so the fitted model captures much of the variation but leaves substantial residual error. Because pooled training contains no duplicate-label conflicts, those residuals cannot be explained by the cross-controller duplicate issue. They show limitations of this linear feature span for these particular labels at the registered numerical cutoff. This does not establish that feature information loss caused Stage-6 collapse or that the raw representation is non-Markov. Individual trajectories' good fits do not establish joint expressiveness.

Pooled OLS design rank is 17 for 57 examples and 256 parameters; it is underdetermined. Minimum-norm fitted weight norm is 73.9147, versus Stage-6 final norm .4973. Fixed ridge gives training RMSE 1.050425 and weight norm 29.4715. Its augmented solve has rank 256 due to regularization, not 256 independent informative data dimensions. No rate/regularizer/model was selected by these results.

Pooled OLS evaluation RMSE is .925072 over all 32 rows, .962523 over the 25 nonoverlapping rows. Fixed ridge gives .915533 and .949529 respectively. Evaluation-route self-fit residuals above are expressly in-sample and are not used as heldout performance. No uncertainty or statistical superiority claim follows from one closely related trajectory.

## Frozen updates transmit small local signals

At checkpoint 300, initial ADD_STOP(1): immediate reward 0; current Q .009457; next masked max .012622; one-step bootstrap target .012622. Alpha .001 changes the same-feature prediction only to .009460, an increase of about .000003165. The achieved return of the chosen whole-day continuation is 7.711633, but that return is not directly provided to this one-step update.

Initial FINISH_PLAN from empty: immediate reward 0; current Q .244519; next masked max .241203; target .241203. One normalized update reduces it only to .244516, about .000003316. Finishing hour 1 is nonterminal; its target correctly bootstraps into hour 2. Only final-day termination uses zero bootstrap. The tests and trace confirm the registered algebra, not a terminal-handling bug.

These examples are consistent with small local corrections and slow propagation with alpha .001, combined with shared linear predictions across states. They do not reconstruct the historical training sequence, establish convergence rates, or isolate the reason the policy collapsed. Actual fixed-continuation returns are not exact optimal Q targets; do not equate bootstrap discrepancies with a proven erroneous update implementation. Stage-7 positive dense construction feedback remains confirmed.

## Decision EXP-004-D05 and next direction

Do not adopt the fitted weights or launch a larger online run yet. The diagnostic shows both a representational limitation across these examples and weak local corrections, so changing only learning rate again would not address all observed issues.

Recommended next stage: preregister a small, explicit interaction-feature revision on this same fixed-data benchmark (for example time/demand with plan coverage/frequency), compared with the existing features at identical solver settings. Keep fixed-continuation overlap accounting and evaluate additional prespecified route examples. This can test whether joint residual error improves before combining a representation change with a different learning update. It is a next hypothesis, not an already implemented fix. A return-based or multi-step online update remains a separate candidate and would need its own stability and quality screen.

## Evidence

`evidence/S8-return-fit-run01/` contains source/model/input hashes, config/dependencies/manifest, three original feature/return/target datasets and tiny fitted coefficients/rank diagnostics in `fits.json`. `return-fit-verification.json` reproduces through `analysis/summarise_return_fit.py` with SHA256 inventory. No trained visitation tables required or exported. No research run overwritten. Source/evidence commits separate; production and unrelated user docs untouched. Local Git only, off-machine backup pending. No push, merge or deletion.
