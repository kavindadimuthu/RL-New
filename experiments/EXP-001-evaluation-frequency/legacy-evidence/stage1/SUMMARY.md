# Stage 1: serial timing comparison

Completed three 100-episode jobs, seed 2024, real 24-hour OD data and original 10,000-episode exploration schedule. Fresh process per job; serial order A, C, B. No GPU, profiler, plots, large Q-table exports or concurrent training. Only the timing stage was run.

| Method | Training seconds | Seconds/episode | Speedup vs A | Time reduction |
|---|---:|---:|---:|---:|
| A: every action | 80.12 | 0.801 | 1.00x | 0.0% |
| B: committed changes | 59.20 | 0.592 | 1.35x | 26.1% |
| C: hour end | 6.99 | 0.070 | 11.47x | 91.3% |

| Method | Evaluation requests | Actual assignments (cache misses) | RL steps | ms/step | Ending RAM MiB |
|---|---:|---:|---:|---:|---:|
| A: every action | 87,487 | 46,741 | 82,687 | 0.969 | 336.9 |
| B: committed changes | 37,598 | 33,623 | 84,378 | 0.702 | 329.2 |
| C: hour end | 2,400 | 2,396 | 84,212 | 0.083 | 164.8 |

## Interpretation

Evaluation requests include plan scoring even when the passenger assignment result is cached. Actual assignments count cache misses. Counts in this report exclude initial environment construction; they include all episode resets and training actions.

Training rewards can change action choices even with the same random seed, so compare step counts and milliseconds per step as well as total time. These are equal-episode training runs, not replay of an identical action trace. Correctness tests separately established agreement on fixed action sequences.

This stage measures early-training runtime, not which approach learns better. Exploration remains approximately 96% at episode 100. One seed and one serial run per method do not establish uncertainty bounds, long-run speed or convergence. Thermal/system-load and run-order effects remain possible. The next stage should compare learned service quality across training seeds with a common evaluator.

Raw episode logs, CPU times, memory, cached assignment counts, source/input snapshots and configuration are retained. Only outputs are Git-ignored; experiment implementation remains isolated on experiment/evaluation-frequency.

## Next-stage duration estimate

At the measured early-training rate, the equal-episode stage has a baseline of approximately 12.0 minutes with three workers, before checkpoint evaluation, parallel slowdown and changed policies under the shorter exploration schedule.

The equal-time stage has a nominal training floor of 6.0 minutes across three waves, plus episode-boundary overshoot and checkpoint evaluation. These are planning estimates, not measurements of the later stages. Neither later stage was started.
