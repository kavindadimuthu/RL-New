# EXP-003 stage 1: real workload and baseline profile

Baseline only. No candidate optimization or speedup claim. Fixed traces from two 24-hour episodes for each training seed 2030 and 2031, using A and the original exploration schedule. Instrumented capture durations are not ordinary training timings.

| Scenario | Calls/repetition | Median seconds | Range seconds | Median ms/call |
|---|---:|---:|---:|---:|
| miss_stream | 512 | 0.859874 | 0.838035–0.860298 | 1.679442 |
| training_stream | 3559 | 3.317744 | 3.264296–3.358819 | 0.932213 |
| warm_hits | 2048 | 0.004364 | 0.004168–0.004574 | 0.002131 |

## Profile interpretation

Separate cProfile runs exist for miss_stream and training_stream. Their cumulative times overlap; do not sum them or treat profiled durations as unprofiled execution speed. The retained profile text/function tables identify candidates, not a demonstrated improvement.

Samples cover observed hour/route-count buckets and retain sequence order. They are early-training traces, not a proof of mature-policy representativeness. Miss_stream disables result caching but allows route-table caching within each fresh replay. Warm_hits prepopulates the sampled plans outside timing. Training_stream preserves the captured mixed-hit/miss sequence with a fresh assigner each repetition.

Output hashes were verified outside timed loops. Setup, prefill, serialization, digest checks and profiler runs are excluded from baseline timings. Results are serial, one numerical thread, no GPU. Run metadata records sleep request, power/hardware, input/workload hashes and clock checks. No final Q-table export is retained.
