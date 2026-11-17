# Stage 4: remaining hourly actions in the RL observation

Protocol v1, 2026-11-17, Asia/Colombo. Status at registration: implementation/tests, no new S4 research run. Prior stages known; this is not blind. Question: does exposing the finite hourly decision budget improve the exact-state learner under a fixed short training budget?

## Treatments and fixed conditions

- A: original six-field exact Q-table key, fresh learner.
- B: same six fields plus integer `max_steps_per_hour - steps_in_hour`, measured before action selection. Remaining budget includes the current decision (60 at hour start, 1 at last decision). Reset to60after voluntary/forced hour ending; no terminal key queried. No binning, aggregation or neural model.

Only learning observation changes. Raw transport state, action masks, assignment, route/fleet/frequency limits, reward/delta reconciliation, FINISH_PLAN availability,60action deadline, start-empty/inherit-previous rules and learning algorithm unchanged. Production trainer/state/config untouched; experimental keyed loop follows production updates exactly. Diagnostics query the same key used by its learner. No70%threshold, warm start, heuristic route hints, altered Q initialization or alternate termination.

Fresh A/B learners for training seeds2034/2035/2036,300episodes each. A is rerun, not only historical control. Alpha.1,gamma1,epsilon1→.05 by episode240 then.05. Checkpoints0/100/300, independent evaluation ties7100/7101/7102, fresh environment/RNG and no updates. Full learner digest verifies Q/visits/epsilon/training RNG immutability across evaluation. Same fixed training demand, no generalization test. Pair by training seed; random trajectories may diverge after learned choices differ. Known historical seed results motivate check, not sample-size inflation.

## Correctness and integrity gates

Tests: identical raw plan at different elapsed action counts collides under A but differs under B; counter resets at voluntary/forced transition; fixed actions preserve rewards, transport states/outcomes; treatment diagnostics and learner share key; A's experimental loop equals production full learning loop on two complete real-data episodes (Q, visits, RNG, hourly metrics/diagnostics). Run full suite before commit. Correctness trajectories are disposable development checks.

After execution, compare fresh A quality/count metrics/checkpoint daily results with archived S1same-seed results, ignoring timing/resource fields. Expect exact deterministic reproduction; flag discrepancy for investigation rather than silently substituting historical data or dropping seeds. Episode0evaluation outcomes and fully exploratory first-episode physics should match A/B; Q/state coverage can differ. No assumption later paths should match.

## Execution, resources and evidence

Prospectively commit source/protocol/analysis. Clean detached worktree `transit_rl/results/EXP-004-S4-execution`, no user-doc edits included. Command module `remaining_action_comparison --run --output <main-worktree>/transit_rl/results/EXP-004-S4-remaining-actions-run01`. Three serial seed waves, two fresh subprocesses per wave (A/B), each one numerical-library thread. Parent threads only launch/wait; learning occurs in independent processes. GPU unused. Equal300episode quality comparison; no comparison of paired elapsed times with old serial timings as speed superiority.

Same limits per process:600measured training seconds checked at episode boundaries,1.5GiB working set,4GiB free RAM; possible one-episode overshoot. Across six runs at most3600training seconds plus overshoot, roughly30minutes critical path if fully used, plus setup/evaluation/logging. Estimate20–30minutes based on serial baseline, not guaranteed. Preserve all failures/incomplete runs; stop later waves if a child incomplete; no automatic retry/extension or exclusions. Scoped Windows sleep prevention per worker, active power scheme/battery/platform/packages/source/input hashes, process/CPU/UTC timing recorded. Thermals/concurrent applications uncontrolled. Source method flags/observation recorded alongside identical resolved transport configs.

Unique IDs `EXP-004-S4-{A|B}-seed{2034|2035|2036}-run01`. Save all1800episode metrics,43,200training-hour rows gzip-compressed, all54evaluation days (1296hours), wave/process status and compact final plans. No Q-table/checkpoint export, PDFs or UI. Raw plan routes/frequencies remain in evaluation-300.json. File hashes/analysis in Git; execution/evidence commits separate; no overwrites/deletion or unauthorized push. Off-machine backup pending.

## Analysis and decision fixed before execution

Registered `analysis/summarise_remaining_actions.py`: all six runs must complete, configs/source/input hashes match, same execution commit and clean worker trees; validate hourly accounting/actions/visits/fleet/capacity,300episode/checkpoint counts and learner immutability using registered S1validator. Average evaluation ties within each model; compute B−A per training seed, then three-pair mean/min/max. Report A/B quality, no-path/capacity shares, reward, unseen/rare states, forced/discarded finishes, fleet and Q-size/memory/runtime. Ranges are descriptive, not confidence intervals.54ties are not54independent trained models.

Primary: final daily demand-weighted served fraction. Screening advancement: B mean service improvement at least2percentage points, no paired seed service decrease, and mean original reward not lower than A. This is a practical screening rule, not statistical proof or automatic default adoption. Otherwise no demonstrated practical improvement under this budget; retain the negative/uncertain result. Report state-coverage costs even if quality improves. Budget information may expand the table and worsen coverage; correctness of exposing deadline does not guarantee improved short-budget learning. Do not conclude RL generally unsuitable from this screen.

Next treatment, especially knowledge-sharing representation, requires a separate prospective amendment. Strict-budget heuristic remains a descriptive quality reference; no heuristic learning/compute access added here.
