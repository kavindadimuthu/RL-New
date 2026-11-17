# Research experiment registry

Follow the [project research standard](../docs/RESEARCH_EXPERIMENT_STANDARD.md). Copy `_template` contents into a new study directory, rename the protocol/report files as appropriate, and populate real values. Templates are examples, not completed research records.

| Study ID | Question | Status | Evidence location |
|---|---|---|---|
| [EXP-004-service-quality-diagnosis](EXP-004-service-quality-diagnosis/README.md) | Diagnose low service and establish feasible improvements | Foundation and retrospective audit completed; new model stages pending | [Protocol](EXP-004-service-quality-diagnosis/protocol.md), [report](EXP-004-service-quality-diagnosis/report.md) |
| EXP-001-evaluation-frequency | Original evaluation-frequency study | Legacy archive | Commit `6de521d` on `archive/evaluation-frequency-legacy`; do not combine with the repeat |
| [EXP-002-evaluation-frequency-repeat](EXP-002-evaluation-frequency-repeat/README.md) | Prospective repeat with recorded provenance | Closed; standby diagnosis and timing qualification retained; off-machine backup pending | [Report](EXP-002-evaluation-frequency-repeat/report.md), [closeout](EXP-002-evaluation-frequency-repeat/closeout.md), and verified compact evidence |
| [EXP-003-passenger-assignment-optimization](EXP-003-passenger-assignment-optimization/README.md) | Faster assignment implementation with unchanged evaluation outputs | C01 exact checks passed; modest gain below registered targets; production unchanged | [C01 result/decision](EXP-003-passenger-assignment-optimization/C01-results.md), [baseline profile](EXP-003-passenger-assignment-optimization/stage1-results.md), [verification](EXP-003-passenger-assignment-optimization/verification.md) |

Add study records in their own experiment changes. Distinguish a local inventory from a tracked, backed-up evidence archive.

For each new study add a row linking its tracked protocol and report. Record repeated runs under unique IDs. Keep failed/incomplete runs visible and document corrections instead of overwriting observations.

Current direction from [EXP-002-D01](EXP-002-evaluation-frequency-repeat/decision.md): retain A (every-action evaluation) as the default baseline, retain B (committed changes) for further investigation, and deprioritize C (hour-end evaluation) under the tested settings. Future experiments receive their own IDs and prospectively committed protocols.
