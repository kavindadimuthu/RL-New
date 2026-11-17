# Stage 5 full-execution amendment, v1, 2026-11-17

Prospective checkpoint after operational preflight, before full screen. Original algorithm, all32features,256weights, alpha.1,gamma1, unit-L2normalization, epsilon schedule, numerical guards and practical-advancement rule remain unchanged from [stage5-function-approx.md](stage5-function-approx.md). No quality-based tuning.

Preflight source `a84499b`: both two-episode arms completed. All384hourly records verified; E matched historical Stage4Bfirst-two training metrics, empty models/fully exploratory first-episode physics match, and evaluations left Q/visits/RNG/weights unchanged. No numerical instability. E measured training2.3331s, L3.0345s; total parent13.3907s. Preflight is operational, not an independent quality sample; its service results do not enter the full-screen aggregate. Small weights and raw outputs preserved in `evidence/S5P-function-approx-run01/`, checksum summary `function-approx-preflight-verification.json` regenerates exactly.78tests passed before source commit. No feature/algorithm change after preflight.

Finalize full plan unchanged: six fresh learners, E/L for2034/2035/2036,300episodes each, checkpoints0/100/300 and ties7100/7101/7102. E/L both deadline-aware; start from empty and retain same production reward/action masks/60action deadline/assignment. Three serial paired waves, two CPU workers, one numeric thread each, no GPU. Preflight learners not resumed. Dedicated clean checkout `transit_rl/results/EXP-004-S5-execution` at this amendment's source commit.

Training guard900measured seconds/process (six at most5400aggregate seconds, possible complete-episode overshoot); memory1.5GiBworking and4GiBfree checks at episode boundaries. Numerical Q/weight guards fixed; failure stops future waves and yields incomplete study without normal final comparison. No reruns or budget extension by observed quality. Setup/evaluation/logging are extra; expect roughly25–35minutes with feature/state growth, not guaranteed. Budget ceiling critical path roughly45minutes plus extras. Runtime is descriptive, not a speed comparison against old serial execution.

```powershell
& 'C:/Users/kavin/Desktop/automation/rl-repo/RL-New/.venv-visualizer/Scripts/python.exe' -m transit_rl.experiment.function_approx_comparison --run --output '<main-worktree>/transit_rl/results/EXP-004-S5-function-approx-run01'
```

Use unique full IDs `EXP-004-S5-{E|L}-seed{2034|2035|2036}-run01`. Registered analysis unchanged, handles full completion versus failure and compares E with archived Stage4Bfor deterministic integrity. L unseen exact keys are novelty counts; record learned-ranking audit rather than labeling them random fallback. Full snapshots are small linear weights only, not complete resumable training models. All compact evidence/negative results retained and committed separately; no master merge/push/deletion, off-machine backup pending.
