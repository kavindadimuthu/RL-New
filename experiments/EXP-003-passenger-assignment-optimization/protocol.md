# EXP-003 protocol v0.1: Foundation and candidate-development rules

Date: 2026-11-14 (Asia/Colombo). Stage: foundation. Research owner requested a new experiment on implementation efficiency with unchanged outputs. Performance-stage candidate/budget registration is pending; this document does not authorize a claimed optimization result from baseline-only checks.

## Question and hypothesis

Can passenger assignment run faster with acceptable memory usage while producing exactly the same allocations and evaluation outputs as the frozen reference? Prior profiling in EXP-002 identified repeated path selection and residual-capacity work as important costs. That is motivation, not proof of a particular optimization's benefit.

A remains the default evaluation schedule. B remains available for future research but is not a treatment in this implementation-efficiency study. C is not a treatment. No change to the scientific assignment model is proposed.

## Baseline and invariants

The baseline source is frozen from master after EXP-002 closeout/merge. Its exact commit/blob and byte hash are in baseline.json. The reference file is loaded under an isolated module name with the same package context; it is not the production implementation. Keep the original unchanged so differential tests remain meaningful after optimizing production code.

Preserve original OD matrices, OD-pair processing order, route/stop order, path-choice rules, tie-breaking, transfer options, waiting/travel-time definitions, capacity allocation/reuse, retry behavior, fleet/reward definitions and every-action evaluation. Do not canonicalize/sort routes or parallelize OD allocation if that changes greedy allocation order. Do not cache capacity-dependent choices across load updates without correct invalidation. Approximate assignment, altered rewards, state compression, GPU ports and changed evaluation frequency are outside this study.

Default acceptance is strict equality of all AssignmentResult fields, including assigned/unserved/direct/transfer arrays, scalar metrics, route peak loads, dtypes, shape and read-only flags; derived metrics must also agree. No numerical tolerance is currently accepted. A necessary tolerance requires a documented prospective amendment and analysis of whether it can change paths, rewards or actions; it must not conceal behavioral differences.

## Stage 0: foundation (current work)

- Freeze baseline identity and source before any optimization.
- Implement an independent differential harness and negative controls proving it detects scalar, allocation and mutability changes.
- Establish synthetic fixtures for empty plans, zero/asymmetric demand, direct/common lines, one/two transfers, capacity pressure, frequency changes, route-order ties, keep flags, directionality, trip-time limits, disabled caches and eviction.
- Verify OD inputs remain unchanged and cache counters agree for the current unchanged implementation.
- Implement scoped Windows sleep prevention with prior-thread-state restoration on success/failure. Check real request acquisition/release in the correctness preflight and use injected APIs in unit tests. Do not change global power settings or force display-on/away mode.
- Commit these checks, preflight evidence and protocol before running candidate performance experiments. Foundation checks are not learning or speed evidence.

## Next stages (must be specified before performance runs)

1. Build representative fixed real-data plan/action traces using recorded seeds; include cache misses, repeated hits and frequency/route updates. Record workload/input hashes. Avoid selecting traces after seeing candidate speed.
2. Profile the baseline without confusing profiler overhead with ordinary runtime. Prerecord one candidate (e.g., reuse route-topology structures or reduce repeated capacity queries), anticipated invariance risks and memory bounds. Keep baseline and candidate selectable.
3. Differentially verify every assignment field on synthetic and real workloads, then verify rewards and same-seed end-to-end action/Q trajectories. Preserve failing traces; do not change baseline expectations to match the candidate.
4. Register and run isolated serial performance repetitions: same traces/config/hardware, one numerical thread, controlled cache state, balanced run order and documented warm-up. Report cold/miss and warm/hit workloads separately, median/range and memory/cache behavior. Freeze exact repeat counts, budgets and required useful speedup before timing.
5. Only after correctness and assignment-level benefit, register a bounded end-to-end training comparison under A. Independent repetitions may use CPU processes, but compare serial timings like for like. Do not mix resource-scaling changes into the first code optimization.
6. Report all candidate outcomes and a separate adoption decision. Retain unchanged baseline if speed/memory/correctness criteria are not met. Three finite fixtures or one timing sample never prove equivalence for all inputs or general performance.

Before those stages begin, add a versioned amendment with candidate code/config choices, actual seeds, budgets, stop rules, performance acceptance threshold and analysis commands. Do not describe those unexecuted stages as completed or preregister unspecified settings retroactively.

## Timing and resources

Future timing runs require temporary sleep prevention for the benchmark lifetime, AC/power-state recording, thread counts and raw UTC plus monotonic elapsed and process CPU measurements. Verify release in finally/normal scope exit. Windows may still honor explicit user sleep, battery/thermal actions or OS policy; the request is not an absolute guarantee. Preserve sleep/resume events or diagnose gaps when clocks disagree. Affected runs require an explicit qualification or a new run ID, not silent retiming.

CPU implementation efficiency is the target. More cores or GPU execution are separate future treatments unless a later protocol explicitly isolates them. Keep caches bounded and measure memory; record any time-memory trade-off rather than claiming a free speedup.

## Provenance and retention

Follow research standard v1.0. Commit each runnable candidate/protocol/analysis version before performance runs and require a clean worktree. Use EXP-003 run IDs and fresh output directories. Preserve resolved configurations, dependencies, input/trace hashes, hardware/power/thread records, timing boundaries, all small metrics and failures, analysis and decisions. Keep reports and primary observations separate. Large Q-tables/checkpoints are optional, never required for routine timing evidence. Do not delete existing evidence or publish/push without authorization.

Production passenger_assignment.py remains unchanged in this foundation. A retained baseline plus a passing self-comparison establishes the test harness, not an optimization or improvement.

References for temporary power requests: [Microsoft system sleep criteria](https://learn.microsoft.com/en-us/windows/win32/power/system-sleep-criteria) and [SetThreadExecutionState](https://learn.microsoft.com/en-us/windows/win32/api/winbase/nf-winbase-setthreadexecutionstate).
