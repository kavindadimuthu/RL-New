# Stage 1 full diagnostic baseline, v1, 2026-11-17

Status at registration: planned; preflight results known. This is a descriptive diagnosis of the existing method, not a treatment comparison or blind replication. Stage-1 diagnostic categories are fixed by the preflight protocol. No service threshold, reward change, alternative evaluator or production optimization is introduced.

## Execution

Fresh learners at training seeds2034/2035/2036, each300episodes. Seeds run serially in separate processes. Dense defaults, alpha=.1, gamma=1, epsilon1 to.05 by episode240, then.05; no learner is resumed from preflight. Same fixed demand. Checkpoints0/100/300; each uses fresh independent evaluation RNG seeds7100/7101/7102, no updates, full learner digest before/after (Q/visits/epsilon/RNG). Episode0 reference is identical across training seeds and is not three independent trained models.

Freeze source/protocol/analysis before execution. Create a clean detached execution worktree at that commit under ignored `transit_rl/results/EXP-004-S1-execution`. This preserves unrelated user documentation edits in the main worktree. Runner rejects any dirty execution tree. Output is written to the main worktree's ignored `transit_rl/results/EXP-004-S1-baseline-run01`, a separate run directory per seed; archive raw compact files after verification. No automatic deletion. No model exports or PDFs.

Use existing project interpreter; packages/source/input hashes, command, UTC/process/CPU times, logical CPUs, active power scheme and battery status recorded. One numeric thread, one worker, CPU only, scoped sleep prevention. Hardware thermals and concurrent applications not controlled; no baseline speed superiority claim. Instrumented runtime includes diagnostic work. Preflight about1second/episode; estimate15–25minutes overall allowing state growth, not a guaranteed completion time.

Budget: up to600measured training seconds per seed, checked at complete episode boundaries; three seeds at most1800training seconds plus one-episode overshoot per seed. Evaluations/setup/logging are separate costs and can extend calendar time. Guard working set1.5GiB and free RAM4GiB at episode boundaries. Incomplete/failed runs retained and no automatic replacement. If any seed fails/incompletes, no normal completed-study aggregate. Separate processes release learner/cache memory between seeds. Progress every25episodes. No parallel jobs for this baseline.

## Outputs and analysis

Retain all300episode metrics and all7200training-hour diagnostic rows per seed; gzip JSONL stores repeated small data efficiently. Retain all9evaluation days per seed at the three checkpoints, with hourly routes/frequencies, demand partition, action counts, exact-state visits, stop/discard details and fleet. Metadata/requirements and SHA-256 inventory retained in Git. Training hour records are measured under exploration; headline outcomes use independent greedy evaluation.

Primary: final daily demand-weighted served fraction. Secondary: original reward, no-path/capacity shares of total demand, unseen and rare-state decisions, fleet/routes, forced finishes and discarded routes. Peak hours prespecified08,09,16,17; compare their demand-weighted service with other hours. Voluntary/forced subgroup service is descriptive; stopping type is not randomized and does not imply causation. Rare exact state means fewer than5updates. No arbitrary70%target or significance claim.

Analysis `analysis/summarise_baseline.py` validates300episodes, accounting and action/visit/fleet bounds for all training/evaluation hours, matching checkpoint counts, evaluation immutability, identical episode0 reference, source commit, clean execution and raw file checksums. Average ties within model, then average three model means; report individual model values and min/max ranges (not confidence intervals). Compare checkpoint0/100/300 descriptively; no optional stopping by observed quality. UTC/elapsed differences are reported for standby/timing qualification. Requirements to advance: all runs and accounting complete. No superiority/feasible-coverage conclusion without the separate reference stage.

## Commands

From the clean execution worktree, launch each seed serially using absolute paths:

```powershell
& 'C:/Users/kavin/Desktop/automation/rl-repo/RL-New/.venv-visualizer/Scripts/python.exe' -m transit_rl.experiment.service_baseline --run --seed 2034 --output '<main-worktree>/transit_rl/results/EXP-004-S1-baseline-run01/EXP-004-S1-baseline-seed2034-run01'
```

Repeat for2035and2036 in fresh processes. Exact executed commands/cwd live in manifests. Regenerate analysis after archive with Python standard library:

```powershell
python experiments/EXP-004-service-quality-diagnosis/analysis/summarise_baseline.py experiments/EXP-004-service-quality-diagnosis/evidence/S1-baseline-run01 --output '<unused-summary-path>.json'
```

Tests before commit: all existing diagnostic trajectory tests and new learner-digest mutation/summary tests. Evidence commit remains distinct from execution commit. Local commits only, off-machine backup pending.
