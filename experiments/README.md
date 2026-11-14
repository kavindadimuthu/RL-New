# Research experiment registry

Follow the [project research standard](../docs/RESEARCH_EXPERIMENT_STANDARD.md). Copy `_template` contents into a new study directory, rename the protocol/report files as appropriate, and populate real values. Templates are examples, not completed research records.

| Study ID | Question | Status | Evidence location |
|---|---|---|---|
| EXP-001-evaluation-frequency | Original evaluation-frequency study | Legacy archive | Commit `6de521d` on `archive/evaluation-frequency-legacy`; do not combine with the repeat |
| [EXP-002-evaluation-frequency-repeat](EXP-002-evaluation-frequency-repeat/README.md) | Prospective repeat with recorded provenance | Completed; Stage 3 timing anomaly disclosed; off-machine backup pending | [Report](EXP-002-evaluation-frequency-repeat/report.md), [timing review](EXP-002-evaluation-frequency-repeat/timing_review.md), and verified compact evidence |

Add study records in their own experiment changes. Distinguish a local inventory from a tracked, backed-up evidence archive.

For each new study add a row linking its tracked protocol and report. Record repeated runs under unique IDs. Keep failed/incomplete runs visible and document corrections instead of overwriting observations.
