# Post-hoc timing review: EXP-002

The timestamp audit identified a discrepancy between wall-calendar UTC intervals and the recorded monotonic performance-counter/CPU measurements. The cause was not independently recorded. Do not attribute it to sleep, clock correction, or another cause as an established fact.

This audit was added after observing the discrepancy. A five-second diagnostic threshold allows ordinary setup overhead but is not a prespecified exclusion rule. Original observations/manifests are unchanged; no seed was silently removed or replaced.

| Run | UTC span seconds | Process elapsed seconds | Training seconds | Training CPU seconds |
|---|---:|---:|---:|---:|
| EXP-002-S3-A-seed2027-run01 | 7393.05 | 121.96 | 120.85 | 120.02 |
| EXP-002-S3-B-seed2027-run01 | 7393.05 | 121.94 | 120.42 | 119.64 |
| EXP-002-S3-C-seed2027-run01 | 7392.54 | 121.26 | 120.06 | 119.28 |

## Interpretation

3 of 21 trained runs were flagged. Consult summaries/timestamp_audit.json for all runs, including the unflagged ones.

The affected equal-time jobs met the recorded training-counter budget and each used approximately the same CPU time. This supports comparing their measured compute budgets, but it does not establish an uninterrupted two-minute wall-calendar experience. The recorded UTC study span includes this discrepancy and must not be presented as active training duration.

Treat Stage 3 as qualified evidence with a timing/provenance anomaly. Do not use it alone for a publication claim about wall-clock efficiency. Stage 1 provides serial timing measurements, and Stage 2 compares fixed episode counts; neither is automatically validated by this supplemental audit alone. If uninterrupted real-time behavior is a research requirement, run a separately identified, prospectively amended repeat rather than overwrite these runs.

This finding is a deviation/limitation of the execution record, not a reason to edit original outputs. Analysis tables retain all originally planned seeds. No additional training was performed for this audit.
