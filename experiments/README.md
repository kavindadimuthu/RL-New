# Research experiment registry

Follow the [project research standard](../docs/RESEARCH_EXPERIMENT_STANDARD.md). Copy `_template` contents into a new study directory, rename the protocol/report files as appropriate, and populate real values. Templates are examples, not completed research records.

| Study ID | Question | Status | Evidence location |
|---|---|---|---|
| EXP-001-evaluation-frequency | Original evaluation-frequency study | Legacy archive | Commit `6de521d` on `archive/evaluation-frequency-legacy`; do not combine with the repeat |
| [EXP-002-evaluation-frequency-repeat](EXP-002-evaluation-frequency-repeat/protocol.md) | Prospective repeat with complete provenance | Planned; protocol committed before execution | Fresh observations will be archived separately |

Add study records in their own experiment changes. Distinguish a local inventory from a tracked, backed-up evidence archive.

For each new study add a row linking its tracked protocol and report. Record repeated runs under unique IDs. Keep failed/incomplete runs visible and document corrections instead of overwriting observations.
