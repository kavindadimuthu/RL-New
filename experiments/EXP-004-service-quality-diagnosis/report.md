# EXP-004 status and findings

Current status, 2026-11-17: baseline, references and remaining-action RL screen completed. [Stage 1](stage1-results.md): **31.99% served**. [Stage 2](stage2-results.md): **81.51%**, with 105 first-hour actions. [Stage 3](stage3-results.md): **90.73%**, original 60-action limit. [Stage 4](stage4-results.md): fresh A 31.99% versus B 31.78%; practical-advancement screen failed. [Decision](decision.md): default unchanged; separately investigate knowledge reuse next.

Stage 3 establishes achievable daily service under the original transport and accepted-action constraints. Search/compute access still differs from RL. It does not isolate learning causes or justify a universal 70% finish rule: its first hour served only 52.37%. Detailed Stage-3 findings supersede earlier next-stage statements below, retained as stage-closeout context.

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

At stage-0 closeout, the next task was to implement and equivalence-check instrumentation. That task is completed below. The 30-minute full-stage training guard is a budget ceiling, not an estimated completion time.

## Stage-1 preflight completed

Registered in [stage1-preflight.md](stage1-preflight.md); execution source `da64b823193811036565055707997f031969d5cd`. Run `EXP-004-S1-preflight-seed2034-run01` completed two training episodes and three evaluation ties. All **120 hourly records** passed accounting/count checks; evaluation left learner Q/visits/RNG unchanged. Scoped sleep prevention exited successfully. Full unit gate: 62 passing tests, including exact two-episode per-action trajectory, learning and operational-cache equality.

| Preflight evaluation metric | Mean of three ties, one learner |
|---|---:|
| Served / total demand | 28.4649% |
| No eligible path: unserved / total demand | 40.7354% |
| Capacity-constrained: unserved / total demand | 30.7997% |
| Unseen state decisions | 99.8412% |
| Mean fleet | 16.4028 / 99 |

The first three percentages partition total demand. These are only a two-episode operational demonstration, not a comparison against the 300-episode EXP-002 result. No claim that these proportions explain mature models. Capacity-constrained includes the effects of ordered greedy allocation; it is not a proof of physically unavoidable shortage. No eligible path retains all configured transfer, direction and trip-time rules. Remaining unused buses do not prove an attainable coverage target.

Measured instrumented training total 2.0057s; whole runner 5.4318s (CPU 5.2813s). Working set after training episodes 75.98/82.86 MiB; initial free RAM 13,944 MiB. Includes observation overhead, not an uninstrumented speed comparison or reliable extrapolation to 300 episodes, where state/cache growth matters. No GPU, dependency installation or model exports. No failed preflight. Existing documentation edits were explicitly recorded and excluded under the preregistered narrow exception.

Raw compact evidence is in `evidence/EXP-004-S1-preflight-seed2034-run01/`. `preflight-verification.json` contains all file SHA-256s, five per-day diagnostic summaries and checks. Post-execution `analysis/summarise_preflight.py` regenerates this verification without training; labelled post-execution because its implementation followed the run. No numerical outcomes or thresholds were selected by this analysis.

Next: finalize and commit the three-seed 300-episode baseline execution amendment, including standalone evaluation checkpoints and runtime guards, then run it. The demand-guided feasible reference follows. Do not introduce a 70% finish restriction before feasibility assessment. Full baseline and reference remain pending. Nothing merged to master or pushed; off-machine backup pending.

Subsequent status: the full baseline above is completed and archived under source `578086b`; that earlier next-task statement records preflight closeout. [Stage-1 results](stage1-results.md) is the current detailed result/decision. All900training episodes and27evaluation days completed;22,248hourly records verified. Reference and controlled fixes remain pending.

Stage2subsequently completed under source `e87f633`: see [stage2-results.md](stage2-results.md) for current reference findings/qualification and next decision. Retain the earlier stage closeout statements as historical context. No claim that the81.51%plan satisfies the original 60-action first-hour budget.
