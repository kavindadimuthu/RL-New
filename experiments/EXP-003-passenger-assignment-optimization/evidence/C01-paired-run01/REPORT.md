# EXP-003 C01: verification and paired assignment timing

The production assignment remains unchanged. C01 is an independently selectable experimental backend. All correctness gates passed before timing. Five serial paired repetitions per cache scenario, fresh process per backend/repetition, one numerical thread, same captured inputs.

| Scenario | Baseline median seconds | C01 median seconds | Time reduction | Speedup |
|---|---:|---:|---:|---:|
| miss_stream | 0.780842 | 0.761790 | 2.44% | 1.025x |
| training_stream | 3.059699 | 2.838010 | 7.25% | 1.078x |
| warm_hits | 0.003666 | 0.003745 | -2.14% | 0.979x |

Peak worker working-set high-water mark, including imports/setup/prefill: baseline 97.98 MiB; C01 98.07 MiB. This is not a pure algorithm-allocation measurement.

Registered assignment-level advancement criteria passed: **False**. Timing qualification: False.

The criterion requires at least 10% median reduction in both miss/mixed streams, no warmed-hit regression exceeding both 5% and 1 ms, and no more than 64 MiB additional peak worker memory. Raw paired values and ranges are retained. Very short warmed-hit CPU times have coarse resolution; no significance claim is made.

Correctness verification covers the 67 strict synthetic fixtures, all three real workload streams with exact output hashes, and three complete training episodes for each seed 2032/2033. Rewards, hourly records, action trace, Q-table, visits, epsilon, RNG and final plans agreed exactly. This is finite tested equivalence, not a proof for every possible input.

No end-to-end training-speed experiment or production adoption occurs here. Only if the criteria pass may a separately registered training-speed trial proceed. On failure, preserve this result and register another candidate/run rather than alter the frozen baseline or selectively repeat timings. Large Q-tables/checkpoints were not exported.
