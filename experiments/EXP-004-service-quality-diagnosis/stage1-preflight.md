# Stage-1 instrumentation and preflight, v1, 2026-11-17

Prospective implementation checkpoint; no production defaults change.

`DiagnosticEnvironment` subclasses the production environment and observes its action/finish boundaries. Operational reward, actions, state and assignment are inherited. A separate assigner performs diagnostic calculations; its cost is included in measured preflight time. These timings are not uninstrumented baseline speed measurements.

For each actual unmet OD, ask the same production path selector whether a path exists with infinite segment availability. Keep route direction, frequency/wait, transfer limits, trip cutoff and path-choice rules unchanged. No eligible path => path-rule-limited unmet demand; eligible path => capacity-constrained unmet demand under ordered greedy assignment. The latter is not proof of unavoidable shortage or a global maximum-throughput result. Tests check category accounting, transfer eligibility and trip cutoffs.

Record action-type counts, forced/voluntary ending, discarded route and signed difference between its feasible tentative service and the committed service (not additive causal attribution), fleet, routes/frequencies/lengths, route peak-capacity ratios, unseen state decisions, state visits and chosen-action visits before updates. Rare means fewer than five historical updates to that exact state; this is a diagnostic threshold, not an acceptance target. Zero demand has no service-ratio inference. No minimum coverage constraint is introduced.

Correctness gate: synthetic fixtures plus two matched full-day training episodes on real inputs at seed2034, compare every action/reward/next-state/info, hourly records, Q-table, visits, epsilon, RNG, final plans and operational assignment hit/miss counts. Run the full unit suite. Disposable correctness trajectories are not independent research runs.

Preflight only: two fresh training episodes at seed2034, with the 300-episode exploration schedule (minimum epsilon after240); evaluate once after episode2 at ties7100/7101/7102 without updates or learner RNG use. This is an operational check, not a learned-quality comparison. No claim of convergence. Write unique run directory, all120 hourly diagnostic records, two episode metrics and all three daily evaluations. No checkpoint export. CPU, serial, one numeric thread, scoped sleep prevention; memory limit1.5GiB process, free memory at least4GiB; check120second elapsed guard at training episode boundaries. Evaluation and setup add time beyond this guard. Retain failures, do not overwrite. Estimate: under two minutes on this machine, to be measured, no automatic 300-episode launch.

Commit source/protocol before preflight. An explicit narrow exception permits only the inherited unrelated root README and training-use-guide edits, recorded in manifest. All experiment, production and input changes must be committed; the CLI rejects other dirty paths. No claim that the whole worktree is clean. Existing docs are not read by the runner. Subsequent full baseline stage requires its finalized amendment and clean execution tree, not this exception by default.

Interpreter: existing project `.venv-visualizer/Scripts/python.exe` outside this worktree; no installation. Record actual executable/package versions, platform, logical CPU count, source/data hashes, resolved config and Git status. AC status, thermals and concurrent load are not controlled in this smoke preflight; no resource-speed claim. GPU unused.

Command from repository root (absolute interpreter path appropriate to this machine):

```powershell
& 'C:/Users/kavin/Desktop/automation/rl-repo/RL-New/.venv-visualizer/Scripts/python.exe' -m transit_rl.experiment.service_preflight --run --output experiments/EXP-004-service-quality-diagnosis/evidence/EXP-004-S1-preflight-seed2034-run01
```

Archive evidence and checksums separately after execution; local Git backup only. Full 300-episode stage and demand-guided reference remain pending until preflight review.
