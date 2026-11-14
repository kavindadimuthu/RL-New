# Research experiment registry

Follow the [project research standard](../docs/RESEARCH_EXPERIMENT_STANDARD.md). Copy `_template` contents into a new study directory, rename the protocol/report files as appropriate, and populate real values. Templates are examples, not completed research records.

| Study ID | Question | Status | Evidence location |
|---|---|---|---|
| EXP-001-evaluation-frequency | Original evaluation-frequency study | Legacy archive | Commit `6de521d` on `archive/evaluation-frequency-legacy`; do not combine with the repeat |
| [EXP-002-evaluation-frequency-repeat](EXP-002-evaluation-frequency-repeat/README.md) | Prospective repeat with recorded provenance | Closed; standby diagnosis and timing qualification retained; off-machine backup pending | [Report](EXP-002-evaluation-frequency-repeat/report.md), [closeout](EXP-002-evaluation-frequency-repeat/closeout.md), and verified compact evidence |
| [EXP-003-passenger-assignment-optimization](EXP-003-passenger-assignment-optimization/README.md) | Faster assignment implementation with unchanged evaluation outputs | Real-data baseline profiling complete; C01 registered, not implemented; no speedup claim | [Stage-1 results](EXP-003-passenger-assignment-optimization/stage1-results.md), [C01 plan](EXP-003-passenger-assignment-optimization/candidate-C01-plan.md), [verification](EXP-003-passenger-assignment-optimization/verification.md) |

Add study records in their own experiment changes. Distinguish a local inventory from a tracked, backed-up evidence archive.

For each new study add a row linking its tracked protocol and report. Record repeated runs under unique IDs. Keep failed/incomplete runs visible and document corrections instead of overwriting observations.

Current direction from [EXP-002-D01](EXP-002-evaluation-frequency-repeat/decision.md): retain A (every-action evaluation) as the default baseline, retain B (committed changes) for further investigation, and deprioritize C (hour-end evaluation) under the tested settings. Future experiments receive their own IDs and prospectively committed protocols.
