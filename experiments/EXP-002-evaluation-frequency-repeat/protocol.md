# EXP-002: Prospective repeat of assignment-evaluation-frequency study

Protocol version: 1.0 · Date: 2026-11-14 (Asia/Colombo, UTC+05:30).
Status: planned before the new execution. Requested by the research project owner; automated implementation/verification by Codex. Independent human review is not claimed.

## Provenance and prior knowledge

This is a fresh, separately reported repeat of EXP-001, whose results are already known. It is not a blinded study or an externally registered preregistration. The legacy study is preserved at commit `6de521d` on `archive/evaluation-frequency-legacy`; its uncommitted-execution history is explicitly documented. Do not pool legacy observations with this repeat. Use new fixed seed sets chosen before execution: training **2027, 2028, 2029**, evaluation **7000, 7001, 7002**. This prevents merely replaying previously selected deterministic trajectories, but three seeds still constitute a preliminary screening sample.

The execution commit is the clean Git HEAD written to each new run manifest; the later evidence commit is a separate archive version. The existing master includes research standard v1.0 via merge `0db40dd`. The current branch is `experiment/evaluation-frequency-v2`.

## Question and fixed conditions

Which assignment-evaluation schedule achieves the best daily service objective at equal episodes and at equal training time?

Treatments:

- **A_dense:** existing score-difference feedback after every action, including feasible tentative routes; hourly correction.
- **B_committed:** score differences after END_ROUTE, frequency changes and REMOVE_ROUTE; no assignment during ADD_STOP, REMOVE_LAST_STOP or KEEP_ROUTE; hourly starting baseline and correction preserve the daily objective.
- **C_hour_end:** zero intermediate reward and final hourly score only; disable all intermediate diagnostic assignments.

Keep real repository inputs, all 24 hours starting at 08:00, exact raw states, capacity constraints, transfer rules, action masks, fleet rules, gamma=1, learning rate, reward coefficients, cache sizes and Hungarian matching fixed. A remains the production default. Identical fixed actions must yield matching final hourly plans, passenger outcomes and daily reward sums. Reward timing and resulting learned choices are the experimental differences.

## Prespecified stages

| Stage | Independent runs | Budget | Exploration |
|---|---|---|---|
| S1 timing | 3 methods, seed 2027 | 100 episodes each, sequential fresh processes | Original 10,000-episode schedule |
| S2 equal episodes | 3 methods × 3 training seeds | 300 episodes each | Same episode-based schedule; epsilon reaches 0.05 after 240 episodes |
| S3 equal training time | 3 methods × 3 training seeds | 120 training seconds each | Same time-based schedule; epsilon reaches 0.05 at 96 training seconds |

Total: **21 trained runs**, plus one prespecified empty-Q-table evaluation diagnostic with the common evaluation seeds and no learning. The diagnostic is not another independent training replication.

For S2/S3, run one worker per treatment concurrently for a training seed, then advance to the next seed. Rotate submission positions by seed as specified by `build_plan()`. Use three processes and one BLAS/OpenMP/numerical-library thread per worker. S1 order is a fixed recorded shuffle with seed 20261113. This retains the legacy order rule but uses fresh training seeds. Do not change settings after seeing new results.

Training timing includes episode reset, environment actions, assignment, Q-updates and episode-based epsilon decay. It excludes checkpoint evaluation, metrics reporting and setup. Record CPU time and whole-process time separately. Stop after the complete episode crossing a time limit; record overshoot. S3 therefore compares shared time-scheduled training recipes, not a shared episode-decay schedule at different speeds.

Evaluate at 100/200/300 episodes in S2 and first episode boundaries crossing 40/80/120 training seconds in S3. The common greedy evaluator uses fresh environments/caches and independent RNGs; it does not update Q/visits or consume learner randomness. It uses hour-end scoring for all treatments. Demand is the same fixed training demand, not a held-out test set.

Primary quality outcome: final mean daily reward, higher is better. Average the three evaluation seeds within each trained model, then summarize three independent training seeds. Report each per-seed value, mean, sample standard deviation and min/max range, and paired seed-wise differences against A. Do not count nine tie-breaking evaluations as nine trained replications or claim statistical significance from this screening design.

Secondary outcomes: demand served, operator/transition penalties, evaluation steps, average fleet, forced hour endings, unseen evaluation-state fraction, episodes, training steps, assignment misses/requests, peak worker memory, elapsed/CPU/evaluation times. S1 primary outcome is serial training seconds and speed ratio versus A; S2/S3 timing is subject to concurrent resource competition. Make within-stage comparisons; stage-to-stage differences also change exploration schedules.

## Resources and stopping

Capture machine information and power scheme before training. Expected hardware is i7-12700H (14 cores/20 logical processors), approximately 24 GiB RAM, AC power, Balanced scheme. GPU is unused because this implementation has no GPU path. Do not change global power settings. Record actual observed hardware rather than assuming it matches.

Require at least 8 GiB free RAM at launch. Stop/label incomplete if a worker exceeds 1.5 GiB working set, free RAM falls below 4 GiB, or a learning job reaches 5,000 episodes or 1,200 training seconds. Checks occur at episode boundaries, not hard OS limits. Preserve partial metrics/manifests; do not silently rerun or exclude failures. A rerun requires a new output directory, run execution identifier and documented reason. This execution uses run01 IDs; the runner refuses overwriting existing run folders.

Expected entire execution: 25–35 minutes and roughly 5–10 MiB of compact evidence. These are estimates, not measured results.

## Reproduction and verification

Use Windows Python 3.13.3. Exact package versions are in `requirements-lock.txt`; the runtime records the interpreter, complete pip freeze, platform, commands, timezone-aware UTC timestamps, source/input SHA-256 hashes, machine/thread data and clean execution commit. Client-facing dates use Asia/Colombo. Create a separate environment with `python -m venv .venv-research` and install the pinned requirements if necessary. Record which interpreter was actually used. No packages are installed automatically by the runner.

Before running:

```powershell
.\.venv-visualizer\Scripts\python.exe -m unittest discover -s tests -v
.\.venv-visualizer\Scripts\python.exe -m transit_rl.experiment.evaluation_comparison --output transit_rl/results/EXP-002-preflight
```

Record test and preflight outcomes in `verification.md`, commit protocol, implementation and analysis, and verify a clean working tree. Execute once:

```powershell
.\.venv-visualizer\Scripts\python.exe -u -m transit_rl.experiment.evaluation_comparison --run --stage all --study-id EXP-002 --output transit_rl/results/EXP-002-repeat
```

After all stages finish, verify and archive without retraining:

```powershell
.\.venv-visualizer\Scripts\python.exe experiments/EXP-002-evaluation-frequency-repeat/analysis/archive_and_analyze.py --input transit_rl/results/EXP-002-repeat
```

The archive tool checks unique IDs, completed counts/budgets/checkpoints, UTC timestamps, configurations/seeds, finite numerical outputs, source/input hashes against snapshots, and file-copy hashes. It generates summaries directly from numerical evidence and copies compact files into `evidence/`. Re-running analysis on the archive must regenerate the same tables without learning. Copy operations do not remove scratch files.

## Retention, reporting and deviations

Keep manifests/configs, original per-episode/evaluation outputs, analysis, summaries, test outcomes, source/input provenance and reproduction instructions in Git. Evidence bytes are protected from Git newline normalization by `.gitattributes`. Do not generate Q-table CSV exports or trained checkpoints for this repeat; mark them `not_saved`. Regeneration would be a new run rather than recovery of an identical old table. Generated PDFs remain outside Git.

After verification, commit evidence/report and update the registry. Local Git history is not an off-machine backup. No remote publication/push is performed without authorized destination/access; report backup status honestly and retain all scratch evidence until backup is verified. No automatic deletion is part of this procedure.

Reports must distinguish observation from explanation. In particular, few evaluation actions/low coverage may be consistent with early termination, but do not establish a universal failure mechanism. Unseen-state fraction and multiple seeds limit inference about learned policies. Report negative results and any deviations, do not adjust the protocol after seeing outcomes. Publication-level convergence/generalization/significance are not claimed.
