# EXP-003-C01: Specialized small-segment capacity maximum

Date: 2026-11-14 (Asia/Colombo). Status: candidate selected after the registered baseline profile; not implemented or timed yet. This is a prospective candidate plan informed by baseline results, not a claim that candidate selection preceded baseline profiling.

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
