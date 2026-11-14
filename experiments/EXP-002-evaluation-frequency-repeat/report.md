# EXP-002 results: prospective evaluation-frequency repeat

Execution code commit: `d8885c7f15f21e421fe13934dca7987acdfb5469`. Status: all 21 trained runs and the prespecified untrained diagnostic completed. All verification assertions passed.

Legacy findings were known. These observations are a separate repeat using training seeds 2027–2029 and evaluation seeds 7000–7002; no legacy results were pooled. Each learning-stage mean averages evaluation seeds within models, then the three independent trained models.

| Stage | Method | Training seconds | Episodes | Final daily reward | Demand served | Unseen evaluation states |
|---|---|---:|---:|---:|---:|---:|
| timing | A_dense | 86.00 | 100.0 | not assessed | — | — |
| timing | B_committed | 64.47 | 100.0 | not assessed | — | — |
| timing | C_hour_end | 7.91 | 100.0 | not assessed | — | — |
| equal_episodes | A_dense | 318.10 | 300.0 | 6.7719 | 34.26% | 95.72% |
| equal_episodes | B_committed | 206.44 | 300.0 | 5.3335 | 25.23% | 98.05% |
| equal_episodes | C_hour_end | 26.25 | 300.0 | 5.0519 | 16.94% | 97.78% |
| equal_time | A_dense | 120.71 | 101.7 | 6.4194 | 30.95% | 97.13% |
| equal_time | B_committed | 120.40 | 161.0 | 5.6598 | 28.23% | 98.59% |
| equal_time | C_hour_end | 120.04 | 1798.7 | 0.2221 | 1.33% | 0.00% |

## Independent seed results

| Stage | Method | Seed | Final daily reward |
|---|---|---:|---:|
| equal_episodes | A_dense | 2027 | 6.1019 |
| equal_episodes | B_committed | 2027 | 5.8091 |
| equal_episodes | C_hour_end | 2027 | 5.2984 |
| equal_episodes | B_committed | 2028 | 5.5049 |
| equal_episodes | C_hour_end | 2028 | 5.3225 |
| equal_episodes | A_dense | 2028 | 7.1071 |
| equal_episodes | C_hour_end | 2029 | 4.5348 |
| equal_episodes | A_dense | 2029 | 7.1066 |
| equal_episodes | B_committed | 2029 | 4.6865 |
| equal_time | A_dense | 2027 | 6.6927 |
| equal_time | B_committed | 2027 | 5.2420 |
| equal_time | C_hour_end | 2027 | 0.4866 |
| equal_time | B_committed | 2028 | 6.0234 |
| equal_time | C_hour_end | 2028 | 0.0827 |
| equal_time | A_dense | 2028 | 5.9000 |
| equal_time | C_hour_end | 2029 | 0.0971 |
| equal_time | A_dense | 2029 | 6.6654 |
| equal_time | B_committed | 2029 | 5.7139 |

## Interpretation and limits

The prespecified untrained reference averaged 5.2435. It is a no-learning diagnostic, not an additional independent training sample.

Highest observed mean reward in equal_episodes: **A_dense**, 6.7719. This is a short-budget observation from three training seeds, not a significance or convergence claim.
Highest observed mean reward in equal_time: **A_dense**, 6.4194. This is a short-budget observation from three training seeds, not a significance or convergence claim.

Interpret runtime alongside service quality and state coverage. High unseen-state fractions mean most evaluation states have no learned exact-state action ranking. Low unseen fractions on a very short, low-service trajectory do not imply broad coverage. Speed alone does not establish an improvement. The stages intentionally use different exploration schedules, so comparisons between stages are not isolated schedule-frequency effects.

All demand is the same fixed problem used in training, not a held-out generalization test. CPU/elapsed timings depend on laptop load and thermal scheduling. Time limits stop at complete-episode boundaries; exact overshoot is in run metrics. Rerunning time-scheduled jobs may produce different episode counts and models.

## Evidence, artifacts and backup

Original manifests, configuration, UTC timestamps, environment locks, machine data, source/input hashes, episode logs and evaluation checkpoints are retained under evidence/. SHA-256 inventory is in archive_checksums.json. No final Q-table/checkpoint or PDF was generated. Analysis regeneration requires no training.

Evidence is committed locally after execution; the evidence commit is distinct from the execution commit above. Off-machine backup has not been verified and no remote push/publication is implied. Retain scratch files until backup is verified.

## Deviations and verification

No automatic exclusions or reruns are performed by this analysis. Any failed/incomplete run prevents a normal completed-study report. Validation checks identity, status, expected budgets/counts, timestamps, common evaluation seeds, numerical finiteness, daily objective consistency, timing totals, provenance hashes, and archive copy integrity. Review verification.md for test/preflight outcomes and any subsequent deviations.
