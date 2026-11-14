# EXP-003-C01: Specialized small-segment capacity maximum

Date: 2026-11-14 (Asia/Colombo). Candidate selected after the registered baseline profile. Implementation revision 1 is prepared below; its correctness checks precede the registered timing trial. No candidate timings were used to choose this implementation.

## Implementation revision 1 and execution

`C01PassengerAssignment` is a separate experimental backend. The production PassengerAssignment remains unchanged. C01 copies the frozen assignment method with only the local segment-peak expression changed; an AST check verifies no other method-body differences. The new helper bypasses the general NumPy reduction for one- and two-element native float64 segments, preserves tie/signed-zero behavior, and falls back for NaNs, other dtypes, larger segments, empty and unusual arrays. No capacity value is cached across load updates.

A development-only test of revision 1 found dtype-specific float16 signed-zero behavior. Before any timing trial, revision 2 restricted the fast path to native float64 (the actual model load dtype); other types use the original reduction. The failed test log/source are retained in preexecution/. No speed measurements were taken on the failing revision, and reference expectations were not relaxed.

Before timing, run unit tests and a correctness precheck (which is permitted to record uncommitted candidate development, but is not speed evidence). Then commit the exact candidate, this plan and timing/analysis code and use a clean worktree. The timed trial repeats the entire correctness precheck from that committed version.

```powershell
.\.venv-visualizer\Scripts\python.exe -m unittest discover -s tests -v
.\.venv-visualizer\Scripts\python.exe -m transit_rl.experiment.assignment_c01_trial --verify --output transit_rl/results/EXP-003-C01-precheck-run01
# After committing the verified candidate/analysis:
.\.venv-visualizer\Scripts\python.exe -u -m transit_rl.experiment.assignment_c01_trial --run --output transit_rl/results/EXP-003-C01-paired-run01
```

The driver creates a fresh process per backend/repetition for all 30 timed blocks, serially, to measure an independent per-process peak working set. Peak memory includes imports, setup, warm-up and prefill, not only assignment allocation. The parent sleep-prevention scope covers correctness and timings; raw power events and UTC/counter checks qualify any interrupted run. No profilers run during the paired trial. A 240-second total active-stage guard is checked between blocks. All samples and failed/incomplete records remain available.

The preceding code/plan commit is the execution version; a later evidence commit is distinct. Unique output directories refuse overwriting. No production adoption or end-to-end speed claim is implied by implementing C01.

## Evidence and scope

The baseline mixed stream contains 3,559 assignment requests, including 1,895 misses. Its separate profile recorded 1,029,713 `available` calls with 2.73 seconds cumulative time out of 7.35 profiled seconds (about 37%). NumPy maximum reductions account for a substantial nested part; cumulative times must not be added. `leg_load` alone accounts for only about 5% self time, so caching views alone is not the primary first target.

First candidate: specialize the residual-capacity calculation for the short route segments encountered here, avoiding repeated general-purpose NumPy reduction overhead. Retain the exact maximum, capacity subtraction, float conversion and nonnegative clamp semantics. The implementation must explicitly handle or fall back for empty/unusual/nonfinite segments as required to preserve reference behavior. It may reduce view/index overhead as part of the same local query, but must not change allocation iteration or arithmetic accumulation order elsewhere.

Do not cache a scalar capacity value across boarding updates without correct invalidation; the first candidate should avoid persistent capacity-result caching. Keep state local to an assignment. Do not reorder OD pairs, routes, transfer loops, tie-breaking, or change cached result keys/limits. No parallelism, GPU, reward change, input approximation or evaluation-frequency change is part of C01.

## Gates before timing

1. Commit the exact candidate and benchmark/analysis implementation before measuring speed. Keep the frozen baseline selectable. If the implementation expands beyond the local capacity query, revise this plan before timing.
2. Pass all foundation tests and the 67 strict fixtures, plus targeted segment cases (single/multiple segments, equal peaks, saturated capacity, directionality and relevant nonfinite/empty behavior).
3. Verify exact output digests against the retained real-data training/miss/hit streams. Retain any failures. No numerical tolerance is approved.
4. Verify end-to-end rewards, action/Q/visit/RNG trajectories against the reference using seeds 2032 and 2033, three full 24-hour episodes each, original exploration schedule and A. Use reference/candidate environments with independent identical initial RNGs. This is equivalence verification, not a learned-quality comparison.

## Registered assignment-level timing comparison

Use the retained stage-1 workload hash and the same three cache scenarios. Run five serial paired repetitions per scenario with a fresh assigner per backend/repetition, one numerical thread, same configuration and bounded scoped sleep request. Alternate backend order baseline/candidate then candidate/baseline, with the fifth pair baseline/candidate. Preserve individual samples; exclude initialization, prefill, serialization and digest checks from timed loops. A disposable 16-query warm-up per backend precedes timing. Do not compare a new candidate run to the historical stage-1 timing alone; run its reference alongside it.

Prespecified advancement targets: at least **10% reduction in median elapsed time** in both miss_stream and training_stream; no warm-hit slowdown exceeding **both 5% and 1 millisecond per timed batch**; no additional persistent cache and no peak-process-memory increase above **64 MiB** versus the paired reference. These are practical screening thresholds, not statistical significance claims. If noisy/inconsistent, preserve the result and register another run rather than selectively repeat samples. Report setup/prefill separately and CPU granularity limits for very short hit timings.

Record UTC, monotonic and CPU clocks, actual machine/power state, sleep events, memory, hit/miss counts, exact commit/config/input/workload hashes and failure status. Flag time discrepancies; preserve interrupted runs. Total-stage guard 240 active seconds and existing 1.5 GiB/4 GiB memory thresholds apply, checked between blocks.

## Later adoption

Only if correctness and assignment-level targets pass, prerecord a serial end-to-end training speed trial (budget/order/repetitions) in a later amendment. Do not infer a training speedup from assignment-only improvement. Default production behavior remains the reference until an explicit adoption decision. A candidate that fails correctness or useful-speed targets remains a documented negative result; never edit the frozen baseline to force acceptance.
