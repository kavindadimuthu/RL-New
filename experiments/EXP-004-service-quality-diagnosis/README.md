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


## Stage 6 update — 2026-11-18

Fixed smaller-step diagnostic completed 300 episodes at one seed without a numerical guard, but both trained checkpoints served 0% by immediately finishing every hour. Not adopted; no larger quality comparison launched. See [Stage 6 results and D03](stage6-results.md), [registered protocol](stage6-linear-stability.md), and `linear-stability-verification.json`. Analysis path-normalization correction is disclosed in the results.


## Stage 7 update — 2026-11-18

Frozen-model diagnostic confirms stopping is ranked above productive reference construction; fixed trajectories serve 0%, 20.9348% and 90.7308%. Positive dense rewards already occur during construction. Cause of learning failure remains unisolated. See [Stage 7 results and D04](stage7-results.md), [registered protocol](stage7-stopping-diagnostic.md) and `stopping-verification.json`. No training or adoption; analysis-only visitation-check correction disclosed.


## Stage 8 update — 2026-11-18

Fixed-return fitting corrects the initial stopping/construction preference but leaves pooled RMSE 1.0440 despite no conflicting training labels. Frozen alpha .001 updates provide tiny local corrections. No causal attribution, new online policy or adoption. See [Stage 8 results and D05](stage8-results.md), [registered protocol](stage8-return-fit.md), and `return-fit-verification.json`. Next proposed test isolates interaction features on fixed data.
