# EXP-003 C01 outcome and decision

Date: 2026-11-14 (Asia/Colombo). Candidate execution commit: `19b9284`. Status: correctness passed; registered performance advancement criteria not met. Keep the current production assignment as default. Do not proceed to a training-speed trial for C01 on the basis of this run.

## What was implemented

C01 is a separate experimental backend, not a change to production PassengerAssignment. It bypasses the general-purpose NumPy maximum reduction for one- and two-element native float64 load segments. Other shapes/dtypes/longer segments and two-value NaN cases retain the original reduction. Only the local capacity-peak expression changes in the copied assignment method; an AST check guards unrelated method changes.

A development test initially caught a float16 signed-zero mismatch before any timing. The fast path was restricted to native float64 and tests rerun. The failed development source/log and corrected prechecks are retained in preexecution/C01/. No reference expectations or numeric tolerances were relaxed.

## Correctness evidence

- **58 tests passed**, including helper edge cases, random segments and advancement-gate tests.
- **67** strict synthetic assignment comparisons passed.
- **6,119** real request output hashes matched across mixed, miss and hit streams.
- Training seeds **2032 and 2033**, three episodes each, matched the reference exactly: rewards, hourly records, actions, Q-table, visits, epsilon, RNG and final plans. This is six matching episode pairs, twelve episode executions, not six independent training replications.
- The timed run repeated those correctness gates from the clean committed version before any measurements. No tolerance was used. This is tested equivalence on finite cases, not a universal proof for all possible inputs.

## Paired timing result

Five serial paired repetitions per scenario, balanced backend order, fresh process per backend/repetition and one numerical thread. Both backends used the same recorded workload and cache conditions. Setup, prefill, output hashing and correctness checks were outside assignment timing.

| Workload | Baseline median | C01 median | Time change |
|---|---:|---:|---:|
| 512 cache misses | 0.780842 s | 0.761790 s | **2.44% reduction** |
| 3,559 mixed training requests | 3.059699 s | 2.838010 s | **7.25% reduction** |
| 2,048 cache hits | 0.003666 s | 0.003745 s | **2.14% increase** (about 0.078 ms per batch) |

Peak worker working-set high-water mark, including imports/setup/prefill: baseline **97.98 MiB**, C01 **98.07 MiB**. This is not isolated assignment allocation; the increase is about **0.09 MiB**.

The complete committed trial took approximately **91.72 seconds** on its process timer, with a matching UTC span. Sleep prevention was restored and the event query found no standby events in the measured interval. No timing qualification was triggered. Raw paired values/ranges, exact packages, hardware/power state, configs/provenance and output checks are in [the evidence](evidence/C01-paired-run01/REPORT.md).

## Decision

**Do not promote C01 or claim a training-time improvement.** The registered target was at least 10% median reduction in both the miss and mixed workloads. Neither met it. The warmed-hit and memory gates passed, and observed output correctness was preserved, but those do not override the primary speed targets.

Preserve this modest improvement as a research result rather than selectively rerunning or lowering the threshold after observing it. No significance or universal speed claim is made from these five pairs. The stage-1 routine's 37% profiled share was not an achievable-speedup prediction: C01 optimizes only a narrow subset of its work.

The next candidate should be separately registered, targeting a broader source of repeated capacity/path work while keeping exact outputs. No C02 implementation or performance run has started. Any later reconsideration of C01 requires a new protocol/decision rather than rewriting this result.

The original production assignment and every-action evaluation remain unchanged. No full Q-table, checkpoint or PDF was generated. Archive checksums and independent table regeneration are retained; off-machine backup remains unverified. The new archive/reproduction checker is post-execution verification; the primary timing/summary code was committed beforehand.
