# Research experiment registry

Follow the [project research standard](../docs/RESEARCH_EXPERIMENT_STANDARD.md). Copy `_template` contents into a new study directory, rename the protocol/report files as appropriate, and populate real values. Templates are examples, not completed research records.

| Study ID | Question | Status | Evidence location |
|---|---|---|---|
| [EXP-004-service-quality-diagnosis](EXP-004-service-quality-diagnosis/README.md) | Diagnose low service and establish feasible improvements | Earlier screens complete; linear-Q stability stop, full quality comparison incomplete; default unchanged | [Protocol](EXP-004-service-quality-diagnosis/protocol.md), [stage-3 results](EXP-004-service-quality-diagnosis/stage3-results.md), [stage-5 results](EXP-004-service-quality-diagnosis/stage5-results.md), [decision](EXP-004-service-quality-diagnosis/decision.md) |
| EXP-001-evaluation-frequency | Original evaluation-frequency study | Legacy archive | Commit `6de521d` on `archive/evaluation-frequency-legacy`; do not combine with the repeat |
| [EXP-002-evaluation-frequency-repeat](EXP-002-evaluation-frequency-repeat/README.md) | Prospective repeat with recorded provenance | Closed; standby diagnosis and timing qualification retained; off-machine backup pending | [Report](EXP-002-evaluation-frequency-repeat/report.md), [closeout](EXP-002-evaluation-frequency-repeat/closeout.md), and verified compact evidence |
| [EXP-003-passenger-assignment-optimization](EXP-003-passenger-assignment-optimization/README.md) | Faster assignment implementation with unchanged evaluation outputs | C01 exact checks passed; modest gain below registered targets; production unchanged | [C01 result/decision](EXP-003-passenger-assignment-optimization/C01-results.md), [baseline profile](EXP-003-passenger-assignment-optimization/stage1-results.md), [verification](EXP-003-passenger-assignment-optimization/verification.md) |

Add study records in their own experiment changes. Distinguish a local inventory from a tracked, backed-up evidence archive.

For each new study add a row linking its tracked protocol and report. Record repeated runs under unique IDs. Keep failed/incomplete runs visible and document corrections instead of overwriting observations.

Current direction from [EXP-002-D01](EXP-002-evaluation-frequency-repeat/decision.md): retain A (every-action evaluation) as the default baseline, retain B (committed changes) for further investigation, and deprioritize C (hour-end evaluation) under the tested settings. Future experiments receive their own IDs and prospectively committed protocols.

EXP-004 Stage 6 (2026-11-18): smaller-step linear model completed one 300-episode stability diagnostic but learned empty plans (0% served); not adopted. [Results](EXP-004-service-quality-diagnosis/stage6-results.md).
