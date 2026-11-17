# EXP-004 status and findings

Foundation created 2026-11-17. No new training or improvement treatment executed.

Code inspection identifies exact-state random fallback, no service-acceptance condition on FINISH_PLAN, hidden remaining action budget, and equal-hour service weighting versus demand-weighted reporting. These are mechanisms/risks, not measured causal attribution. Assignment uses ordered greedy passenger allocation; no globally maximal throughput guarantee.

Stage 0 will verify historical descriptive values and input demand. Stage 1 must distinguish absent connections from capacity-limited assignment and ineffective planning. Stage 2 must establish an achievable reference before choosing service thresholds. No claim yet about the attainable service ceiling or the improvement of any proposed change.

## Stage 0 completed

Execution source: `d6b40df`. Run `EXP-004-S0-audit-run02` passed all accounting, count, finiteness and committed-input checks. The three-model means (evaluation ties averaged within each model) are:

| Metric | Value |
|---|---:|
| Daily served demand | 34.2557% |
| Unseen evaluation states | 95.7158% |
| Average buses used | 17.3657 / 99 |
| Forced hour finishes/day | 5.3333 |
| Actions/day | 788.7778 |

This is a retrospective verification of EXP-002, not new training, a causal explanation, or a new independent replication. Complete model means, 24 demand totals, raw/Git input hashes, interpreter and working-tree provenance are in `evidence/EXP-004-S0-audit-run02/audit.json`. Existing unrelated README and training-guide edits were present and are recorded; they were not included in experiment commits.

The first audit failed on CRLF checkout conversion; its failure record is retained under run01. Protocol revision 0.1a describes the correction. Reproduce with Python's standard library from the repository root, using an unused output directory:

```powershell
python experiments/EXP-004-service-quality-diagnosis/analysis/audit_existing.py --output experiments/EXP-004-service-quality-diagnosis/evidence/EXP-004-S0-audit-run03
```

Source compile and CLI smoke checks passed. Audit execution took approximately one second of command runtime; this is not a training estimate. No dependency installation or model export was required. Off-machine backup remains pending.

Next: implement and equivalence-check stage-1 instrumentation, then commit its exact procedure before new model runs. Stage-1 training runtime is not yet measured; the 30-minute training guard is a budget ceiling, not an estimated completion time.
