# Stage 6 result: stable run, empty service policy

2026-11-18. Source/protocol/analysis execution commit `2536f381e720f5ac27275c5ea98d001d6ca71aca`. [Prospective protocol](stage6-linear-stability.md). One seed 2034, fresh linear model, constant learning rate .001 instead of Stage-5 .1; all algorithmic settings otherwise fixed. All 78 tests passed before execution.

The run completed 300 episodes without a numerical or resource guard. This passes the registered operational gate only. It does not establish convergence or a useful policy.

| Greedy checkpoint | Mean demand served | Mean daily reward |
|---|---:|---:|
| Untrained | 26.3012% | 5.9327 |
| 100 episodes | 0% | 0 |
| 300 episodes | 0% | 0 |

All three evaluation seeds at both trained checkpoints produced the same empty service behavior: one FINISH_PLAN action per hour, no routes, no passengers served. This is a degenerate learned policy, not an assignment failure. The experiment does not establish why this update and feature representation preferred stopping; reward timing, feature aliasing and update dynamics remain candidate explanations requiring targeted tests. Do not claim that the objective globally prefers empty plans: earlier feasible references achieved positive reward and substantial service.

Training took 25.6342 seconds; entire process 32.6744 seconds. Peak recorded working set 225.67 MiB. Final weight norm .497349, maximum episode-end norm .497487. Runtime was much shorter than the prospective 10–15 minute estimate because trajectories became short (first training day 896 actions, last 24). This is not a fair computational speedup or improved passenger-assignment efficiency. No GPU or multicore benefit is claimed.

Analysis verified 7,416 hourly records (300 training days and nine evaluation days), passenger accounting, masks/accounting diagnostics, initial evaluation and first exploratory-day physics against Stage 5, finite stored weights and immutable evaluations. The original registered analysis stopped on differing absolute checkout paths in data_dir/results_dir. A disclosed post-execution analysis correction excludes those two location fields, checks all other config fields except the intended learning-rate change, and separately requires identical CSV input hashes. No training was rerun and no source settings changed. Raw artifacts were not modified.

## Decision EXP-004-D03

Do not adopt this variant or proceed directly to a larger quality screen. Smaller updates avoided the observed Stage-5 numerical stop over this one run but did not produce useful service. Keep production unchanged. Next recommended work is a registered diagnostic of stopping-action values and delayed route-completion rewards on fixed trajectories before choosing another learning algorithm or tuning more rates. Compare predictions against actual finite-day returns; test whether the feature model can distinguish productive route construction from immediate stopping. This is a proposed explanation check, not an established cause or an already executed experiment.

## Evidence

Raw outputs: `evidence/S6-linear-stability-run01/EXP-004-S6-L-seed2034-run01/`. `evaluation-300.json` contains all three final full-day plans. `linear-stability-verification.json` retains summaries and SHA256 inventory; `analysis/summarise_linear_stability.py` regenerates it without training. Archive 13 files, 1,246,641 bytes, including small 256-parameter weights, not full resume checkpoints. Scratch and clean execution checkout retained. Local commits only; off-machine backup pending. No push, merge, deletion or unrelated documentation staging.
