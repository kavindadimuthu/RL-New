# EXP-002: Evaluation-frequency repeat

**Status:** all 21 planned trained runs plus the prespecified untrained diagnostic completed. The execution protocol, implementation and primary analysis were committed before training as `d8885c7`. The legacy study remains separate on `archive/evaluation-frequency-legacy` at `6de521d`.

**Important qualification:** a post-execution audit found a large UTC-versus-performance-counter discrepancy in Stage 3's first seed wave. Read the [timing review](timing_review.md) before interpreting its equal-time results. The recorded training/CPU budgets were met, but uninterrupted wall-calendar timing is not established. Original observations are retained without silent exclusions or replacements.

- [Prespecified protocol](protocol.md): prior knowledge, fresh seeds, budgets, evaluation, stopping and retention.
- [Results and interpretation](report.md): primary numerical tables, per-seed results and limits.
- [Research decision EXP-002-D01](decision.md): retain A as default, B as a candidate, and deprioritize C under the tested conditions; procedure for subsequent studies.
- [Verification and deviations](verification.md): tests, independent archive checks and timing qualification.
- [Original compact evidence](evidence/): timestamps, source/input hashes, environment, hardware, settings, metrics and evaluations.
- [Analysis scripts](analysis/): regenerate primary summaries without training; separate post-hoc timestamp diagnostic.
- `archive_checksums.json`: byte-level inventory verified against the scratch evidence.
- `postexecution-checks.json`: mechanical validation and regeneration record.

Evidence archive version: annotated tag `research/EXP-002-v1` (created after the evidence commit). This identifies the post-run archive rather than the original execution commit. Local Git is not an off-machine backup; no remote push or public release has been performed. Keep scratch copies until backup is verified.

Large Q-table exports, trained checkpoints and PDFs were not generated for this repeat. Their absence is intentional and recorded. Rerunning would create a new experiment execution rather than restore an identical saved trained model.
