# EXP-003 stage 1 outcome

Status: baseline capture/profiling completed; candidate C01 registered but not implemented. Execution commit: `d08842d`. This record describes baseline costs, not an optimization speedup.

## Observations

Four instrumented real-data episodes (two each for seeds 2030 and 2031) produced 3,559 assignment requests, including 1,895 cache misses and 1,664 hits. The preserved trace includes ordered actions, plans, hours and exact output hashes. This is an early-training workload, not a mature-policy or learning-quality study.

| Workload | Calls per repetition | Median time across three serial repetitions |
|---|---:|---:|
| Mixed training requests | 3,559 | 3.317744 seconds |
| Sampled unique cache misses | 512 | 0.859874 seconds |
| Prepopulated cache hits | 2,048 | 0.004364 seconds |

Setup, prefill, hashing and serialization are outside these timers. CPU-time granularity limits interpretation of the very short cache-hit samples. Individual samples/ranges are retained in [the generated report](evidence/stage1/REPORT.md) and raw measurements.

The mixed-stream profile recorded 1,029,713 `available` calls, accounting for 2.73 of 7.35 profiled seconds cumulatively (about 37%). Small-segment NumPy maximum operations are a substantial nested cost. Path selection is the larger enclosing operation; cumulative percentages overlap. Profile times include profiler overhead and are not ordinary execution timings.

The complete stage recorded 37.78 monotonic seconds. Its UTC/counter discrepancy was approximately 0.003 seconds; the power-event query completed with no standby events in the recorded interval. The scoped sleep request was restored. This short successful run does not guarantee that a later benchmark cannot be interrupted.

## Verification and provenance

- 52 unit tests passed before the execution commit, including sampling/cache-scenario checks.
- Output digests were verified before timing. Independent archive verification replayed **6,119 outputs** across all three workloads and confirmed exact hashes, configuration, input/source/workload identity and cache semantics.
- Archive-only replay regenerated the baseline report byte-for-byte. [Checksums](stage1-checksums.json) and [verification](stage1-verification.json) are retained.
- Production passenger_assignment.py is unchanged from the frozen reference. No optimized implementation or GPU/resource-scaling treatment was run.
- The archive/replay verification helper was added after execution; the capture, timing and primary report-generation procedure was committed beforehand. Do not confuse these versions.

## Next decision

Advance to [C01 planning](candidate-C01-plan.md): reduce overhead in residual-capacity segment-maximum queries while preserving exact results. The plan defines strict correctness gates, paired timing procedures and advancement thresholds before candidate implementation/timing. It is a hypothesis to test, not an established speedup.

No baseline is replaced and no default changes. If C01 fails equality or useful-speed criteria, preserve that negative result and select another candidate prospectively. All evidence is local; off-machine backup remains unverified and scratch files remain intact.
