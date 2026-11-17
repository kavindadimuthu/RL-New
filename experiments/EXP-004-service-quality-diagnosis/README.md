# EXP-004: Diagnose low passenger service

Status: stage-0 audit, full stage-1 baseline and stage-2 reference completed; action-budget-matched control pending.

This study investigates planning quality. It is separate from EXP-003, which investigates assignment speed without changing outputs.

- [Protocol](protocol.md): staged procedure and advancement rules.
- [Report](report.md): findings, outstanding questions and execution status.
- [Stage-1 preflight](stage1-preflight.md): committed instrumentation/run procedure and limits.
- [Stage-1 results](stage1-results.md): complete baseline diagnostics, timing and next-stage decision.
- [Stage-2 results](stage2-results.md): 81.51% feasible-reference service, with first-hour action-budget qualification.
- `analysis/audit_existing.py`: dependency-free, retrospective audit of EXP-002 evidence and current input demand. This is not a new training run or independent replication.

The inherited every-action Q-learning method remains the baseline. No production defaults change in this foundation.
