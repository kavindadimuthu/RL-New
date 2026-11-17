# Stage 2: deterministic feasible reference, v1, 2026-11-17

Status at registration: implementation/testing; no real-data reference run yet. Stage-1 observations are known. Question: can an explicit demand-guided search produce substantially better feasible service than the observed tabular learner? This is an achievable-service reference, not an equal-compute randomized comparison or an upper bound.

## Algorithm fixed before measurement

Same OD/day order, empty initial plan then inherited previous-hour plan, assignment implementation/path rules, bidirectionality, fleet rounding/capacity, eight routes, two-to-eight stops, frequencies1–12, initial frequency4 with existing fallback. Same original hourly objective S−.3O−.3C (transition off first hour); accept improvements >1e-12. No reward reweighting or70%constraint. Optimize each current hour greedily, no future-hour lookahead.

Candidate pool: one shortest-travel-time physical simple path per OD, Dijkstra with lexicographic path ties; retain paths length2–8, deduplicate route reversal for bidirectional service. No alternative-path enumeration; pool is not exhaustive. Rank candidates by total residual direct OD mass between their stops, including reverse direction. This ranking is only a shortlist; every proposed plan is scored by full original passenger assignment and original reward.

For each hour:

1. Starting with inherited plan, repeatedly score feasible additions among top24ranked paths; append the best strictly improving route at the production END_ROUTE frequency, until no improvement or eight routes.
2. Best-improvement frequency hill climb over all valid +1/−1 changes, original score, until no improvement or budget. Ties retain first encountered option (route-index order, increase before decrease).
3. Up to three removal/replacement rounds: score removal of each route and replacement by top12residual-ranked candidates; replacement removes old route then appends new route at original initial/fallback frequency. Select best positive improvement, then repeat frequency hill climb. Stop replacement phase if no improvement.

Budget: at most2000score requests/hour (including initial plan evaluation), at most120accepted edits/hour; deterministic loop ordering, no stochastic seed. Hitting search budget is a defined bounded solution, not an excluded run. Record every accepted score and action trace. Initialization includes one additional environment setup evaluation outside search-request counts. No hyperparameter sweep/retry based on quality. One deterministic run; do not create three identical outputs and call them independent trials.

## Feasibility and action-budget distinction

Replay accepted route/frequency edits through unmodified production action masks, passenger assignment and dense reward. Each new route is its ADD_STOP sequence then END_ROUTE; replacements are REMOVE_ROUTE then construction; frequency steps are original actions; each hour ends with FINISH_PLAN. No KEEP lock is introduced. Verify every final plan, original score, passenger service and whole-day reward against search evaluation.

Count all accepted construction/edit actions and FINISH_PLAN per hour. If any exceeds60, extend only the replay deadline to maximum accepted trace length and explicitly label output a reference outside original action budget. A valid extended replay is not proof of reachability within60actions or an equally constrained MDP. Report exact over-budget hours and maximum trace length even if none exceed. Rejected candidate-search evaluations also have cost; report them, rather than comparing only accepted actions with RL steps. No claim of minimum action count.

## Execution and resources

Commit source/tests/protocol/analysis before real-data execution. Use fresh clean detached worktree `transit_rl/results/EXP-004-S2-execution`, preserving user's unrelated doc edits. Command module `transit_rl.experiment.service_reference_run --run --output <main-worktree>/transit_rl/results/EXP-004-S2-reference-run01`. New unique output; preserve failures; no automatic retry. CPU, one process/thread, GPU unused, scoped sleep prevention. Save platform/packages, command/cwd/code commit, input/source SHA-256, config, active power scheme and memory. AC status/thermals/concurrent load not controlled; no speed-superiority claim. Free RAM4GiB minimum, working-set1.5GiB, elapsed600second guard at hour boundaries; an expensive final hour may overshoot. Expect roughly1–5minutes; budget ceiling is not a prediction. No full Q exports or PDFs.

## Analysis and retention

Primary: daily demand-weighted served fraction versus stage-1 three-model mean, also each model's descriptive range. Secondary: no-path and capacity-constrained shares of total demand; original daily reward; fleet/routes; hourly service/peak08,09,16,17; elapsed/CPU, search requests/cache counts; accepted actions and deadline exceedance. Same fixed demand, no held-out generalization. Compare resource budgets transparently; no significance or universal heuristic-superiority claim.

Registered `analysis/summarise_reference.py` validates24hours, action/route/frequency/fleet limits and demand accounting, replay checks, common settings/inputs/unchanged production source, completion/sleep scope, source identity and UTC/elapsed consistency. Preserve raw `service-plan.json` (complete hourly plans), `search-hours.jsonl`, candidates, config, manifest, hashes, requirements and checksums in tracked evidence. Regenerate summary without planning/training. Different execution/evidence commits; local backup only, no push authorized. If interrupted, retain incomplete status without completed-study aggregation.

Next decision: establish observed achievable coverage, then prospectively select separate RL formulation/learning experiments. Do not set a universal service threshold from this one heuristic solution.
