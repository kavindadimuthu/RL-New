# Prepared evaluation-frequency experiment

Branch: `experiment/evaluation-frequency`, based on master `a06215d`.
Status: implementation and correctness tests prepared; controlled training has not started.

## Question and treatments

Which evaluation schedule produces useful bus-service plans within a practical computation budget?

| Version | Full service evaluation | Reward schedule |
|---|---|---|
| A: dense | Every action, including feasible tentative routes | Score differences, hourly correction |
| B: committed | END_ROUTE, frequency changes, REMOVE_ROUTE, hour end; also hourly starting baseline | Score differences only for committed changes, hourly correction |
| C: hour end | Final committed hourly plan only | Zero intermediate rewards, final hourly score |

B does not score ADD_STOP, REMOVE_LAST_STOP, or KEEP_ROUTE. All versions keep physical action rules, 24-hour ordering, exact raw states, original OD demand, capacity enforcement, transfer choices, objective coefficients, gamma=1, learning rate, assignment cache limits and route matching. The default configuration remains A. B's `committed` mode is new; C uses existing `terminal` mode with intermediate diagnostic evaluation disabled. Simply using legacy `delta` would NOT be a fair substitute: its return subtracts inherited starting scores.

All schedules must sum to the same hourly/daily objective for identical actions. Fixed-action tests cover inherited plans, every action type, forced endings, unfinished-route discard, and random action traces on a small synthetic network. These are correctness tests rather than learning experiments. Tests also verify that common evaluation cannot change the learner's Q-table, visits, RNG, or training caches.

## Stages and fairness

1. **Serial timing:** 100 training episodes per version, seed 2024. Fresh process per job; no simultaneous training. Version order is fixed by a recorded shuffle. Retain the original 10,000-episode exploration schedule for continuity with the previous baseline. This estimates speed, not learning quality, and one timing run per treatment is preliminary.
2. **Equal episodes:** 300 episodes per version for each seed 2024, 2025, 2026 (nine jobs). Explicit shortened exploration schedule, identical across versions: epsilon reaches 0.05 after 240 episodes. This is intentionally different from the early-training timing phase, where exploration stays high.
3. **Equal training time:** 120 training seconds per version for the same three seeds (nine fresh jobs). Exploration follows the same elapsed-training-time schedule for every version, reaching 0.05 at 96 seconds. Schedule updates and stopping occur at episode boundaries; save exact duration and overshoot. This compares complete short training recipes at equal time, not just the same episode-based decay running at different speeds.

At one-third, two-thirds, and completion of each learning job, evaluate greedily using separate RNG seeds 6000, 6001, 6002. All treatments use the same hour-end evaluator, same objective, and fresh evaluation caches. Evaluate on the same input demand; this measures optimization of the fixed problem, not generalization to unseen demand. Independent evaluation RNGs test random tie-breaking; they are not additional training replications.

Report final mean evaluation reward for each training seed as the primary quality measure. Report served-demand fraction, fleet use, transition penalty, unseen-state fraction, training steps, assignment calls/misses, CPU and elapsed training seconds, table size, memory and forced hour endings. Summarize paired per-seed differences against A with individual values and ranges; three training seeds are insufficient for strong statistical claims. More seeds/budget may be needed if outcomes disagree or ties dominate.

Timing and time-budget clocks exclude evaluation, disk reporting and exports; actual process elapsed time is also recorded. No large Q-table CSVs or plots are generated during training. Do not compare parallel throughput directly with the earlier single-worker 84-second baseline; use the serial timing stage for speed ratios. Fewer evaluation calls are not proof of better learning.

## Machine and execution

Inspected hardware: Intel Core i7-12700H, 14 physical cores/20 logical processors; 23.6 GiB usable RAM with approximately 14.4 GiB free at inspection; NVIDIA RTX 3050 Laptop GPU, 4 GiB VRAM; approximately 66 GiB free on C:. Battery reports AC power, 100% charge; Windows power scheme is Balanced. No training Python processes were active at inspection.

Use three separate CPU processes for independent learners, with one NumPy/BLAS/OpenMP thread per process. Each parallel wave contains all three treatments for one training seed; rotate submission positions between waves. Windows may schedule workers on different P/E cores, and laptop power/thermal limits and background activity remain sources of timing variation. Rotation reduces a fixed treatment/worker association but does not eliminate hardware effects. Record CPU time alongside elapsed time. Keep AC power and the same power scheme throughout; do not change global machine settings during the comparison.

Python processes allow independent CPU-bound jobs to run across cores. Numerical thread limits avoid nested thread oversubscription. The GPU is intentionally unused: this model uses Python path searches and dictionary Q-tables, with no GPU implementation. Porting it would introduce another experimental change.

Start only with at least 8 GiB free RAM. Each worker checks memory at episode boundaries and stops the experiment as incomplete if its working set exceeds 1.5 GiB or system free RAM drops below 4 GiB. Learning jobs also have 5,000-episode/1,200-training-second safety limits. These guards are not hard OS limits; transient peaks within episodes are possible. Any partial job invalidates an ordinary completed-treatment comparison and must be reviewed before resuming.

Expected elapsed time: **25–40 minutes**, based on A's measured 0.84 seconds/episode and three workers. This includes serial timing, both learning stages, evaluation checkpoints and overhead. B/C runtime and parallel laptop throughput are still unmeasured, so this is a planning estimate. Use the serial phase to revise the estimate before continuing long work if necessary. The short-horizon study is a screening comparison, not evidence of 10,000-episode convergence.

## Commands

Preparation only (no training):

```powershell
.\.venv-visualizer\Scripts\python.exe -m transit_rl.experiment.evaluation_comparison
```

Correctness tests:

```powershell
.\.venv-visualizer\Scripts\python.exe -m unittest discover -s tests -v
```

Explicit experiment launch, after reviewing the preparation:

```powershell
.\.venv-visualizer\Scripts\python.exe -u -m transit_rl.experiment.evaluation_comparison --run
```

Run only the first (serial timing) stage:

```powershell
.\.venv-visualizer\Scripts\python.exe -u -m transit_rl.experiment.evaluation_comparison --run --stage timing --output transit_rl/results/evaluation_comparison_stage1
```

`--stage equal_episodes` and `--stage equal_time` similarly select one later stage. Use a fresh output directory for each launch.

Results live under Git-ignored `transit_rl/results/evaluation_comparison_prepared/`. Preparation creates `plan.json`. Running records configuration, input/source hashes, exact source snapshots (including uncommitted source), commit/status, per-episode logs, evaluation checkpoints and per-job summaries. An existing run manifest prevents accidental overwrite; use a new `--output` for another run. The `.venv-visualizer` name identifies the existing dependency environment; the visualizer itself is not used.
