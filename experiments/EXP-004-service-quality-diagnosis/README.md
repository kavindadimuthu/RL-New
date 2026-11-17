# EXP-004: Diagnose low passenger service

Status: earlier screens completed; Stage-5 linear-Q trial stopped on numerical guard, full quality comparison incomplete; default unchanged.

This study investigates planning quality. It is separate from EXP-003, which investigates assignment speed without changing outputs.

- [Protocol](protocol.md): staged procedure and advancement rules.
- [Report](report.md): findings, outstanding questions and execution status.
- [Stage-1 preflight](stage1-preflight.md): committed instrumentation/run procedure and limits.
- [Stage-1 results](stage1-results.md): complete baseline diagnostics, timing and next-stage decision.
- [Stage-2 results](stage2-results.md): 81.51% feasible-reference service, with first-hour action-budget qualification.
- [Stage-3 results](stage3-results.md): 90.73% daily service within the original 60-action limit.
- [Stage-4 results](stage4-results.md): paired remaining-action observation screen; no consistent practical improvement.
- [Stage-5 results](stage5-results.md): linear feature model hit numerical guard in episode49; incomplete quality comparison and failed evidence retained.
- [Decision](decision.md): default unchanged; linear variant not advanced, stability revision needed before another screen.
- `analysis/audit_existing.py`: dependency-free, retrospective audit of EXP-002 evidence and current input demand. This is not a new training run or independent replication.

The inherited every-action Q-learning method remains the baseline. No production defaults change in this foundation.
