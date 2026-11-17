# Stage 5: transparent linear function-approximation screen

Protocol v1, 2026-11-17, Asia/Colombo. Status at registration: implementation/tests; no research preflight/full run. Earlier findings known. Question: can a specified shared-feature Q model improve fixed-budget service relative to a deadline-aware exact table? This is not DQN, a neural-network trial, or proof that all function approximators behave alike.

## Arms and interpretation

E: fresh exact-state table with original six fields plus remaining actions, equivalent to Stage4B. L: normalized linear semi-gradient Q using deterministic summaries of those same raw inputs and fixed road network. Both know the deadline. L changes encoding and value parameterization together; results cannot isolate sharing from feature engineering/information loss. No claim that the feature representation is lossless or Markov. Route order and detailed transfer interactions can be lost. A feature-tabular ablation or neural model would need another protocol.

No current/default production state, trainer, reward, actions, deadline or assignment changes. No heuristic hints/warm starts, candidate-plan evaluation, counterfactual passenger assignment, search/lookahead, new reward, replay buffer, target network or adaptive hyperparameter sweep. The network/data-derived descriptors are explicit domain information/inductive bias, not a neutral architecture-only comparison.

## Fixed L model

32 named float64 features in `linear_q.FEATURE_NAMES`; eight separate action-type weight vectors (256 parameters), zero initialization with common Q offset0. For state key7and action, raw vector x is normalized φ=x/||x||₂ (bias ensures positive norm). Q=q0+w[action_type]·φ. Update w←w+.1·[r+γmaxQ(next)−Q]φ, γ1; terminal target r. Same epsilon-greedy/mask/tie rules and episode epsilon schedule as E. Numerical checks fail rather than clip. No convergence guarantee: off-policy bootstrapping with linear approximation can diverge, so preserve any such outcome rather than silently switching algorithms. See [Precup, Sutton and Dasgupta](https://cseweb.ucsd.edu/~dasgupta/papers/offtd.pdf). This is distinct from [DQN](https://doi.org/10.1038/nature14236).

Raw features, in declared order:

1. Bias; normalized day position; sin/cos clock hour; remaining/60.
2. Fleet remaining/99; route count/8; unfinished length/8; kept count/8; plan sum frequencies/(8×12); covered stops/15.
3. Original-OD direct-pair coverage fraction (union of current routes); demand with both endpoints covered /hourly total; demand/(demand+99×effective bus capacity); unfinished-route direct OD /total.
4. Previous route count/8; previous sum frequencies/(8×12); canonical route-set symmetric difference/(2×8), a proxy rather than Hungarian cost.
5. Target route length/8, frequency/12, analytical buses/99 capped1, direct OD fraction and direct-mass/(direct-mass+frequency×effective capacity) pressure proxy.
6. Target final-stop incoming+outgoing demand/(2×total), degree/max network degree, covered-stop indicator; target one-way time/((8−1)×maximum physical link time); previous-route indicator; kept indicator.
7. Analytical frequency delta/12; signed analytical fleet delta/99 clipped[−1,1]; remaining fraction×target length fraction.

Target for indexed actions is that indexed route; ADD_STOP uses unfinished route plus proposed stop, END_ROUTE uses unfinished route, REMOVE_LAST_STOP describes current unfinished route. Initial/fallback frequency uses original fleet calculator; if no feasible end frequency, initial frequency is only a descriptor, not actual service. FINISH has zero target descriptors. Local analytical cost descriptors are not full candidate service evaluations. Directionality/ignored diagonal follow config. Zero demand uses denominator1, no service inference. Source specifies all exact arithmetic/ordering. Two-state feature cache only, no growing feature-memory model.

Both retain exact raw-key visitation audit dictionaries for novelty/diagnostics. L's audit q values are presence markers, not learned action values; weights always drive L predictions, including unseen raw keys. Thus L's unseen-key fraction must not be called random/no-guidance fraction. Evaluation audits separately count unseen keys with a unique best action among multiple valid choices, tied best choices, and only-one-valid-action cases. These counts demonstrate prediction use, not correctness. Audit memory is included in runtime RAM and prevents an architecture-memory-saving claim.

## Operational preflight (first execution)

Two fresh episodes/arm, seed2034, with original300episode schedule; checkpoints0/2, each ties7100/7101/7102. Run one E/L paired wave, not a quality-ranking experiment. Source/protocol/analysis must be committed first. Verify E first-two metrics against Stage4B, initial zero-model evaluation and fully exploratory first-episode physics match E/L, all accounting and learner immutability. Unit tests establish sharing, normalized updates, masks, finite/no-lookahead features and fail-fast guards.

Preflight IDs `EXP-004-S5P-{E|L}-seed2034-run01`. Fresh clean checkout `transit_rl/results/EXP-004-S5P-execution`; root output `transit_rl/results/EXP-004-S5P-function-approx-run01`. CPU two workers, one numeric thread each, no GPU, scoped sleep prevention.120measured training seconds/worker and existing1.5GiBworking/4GiBfree guards, checked after each episode. Estimate under2minutes. Nonfinite values, |estimated Q|>1000 or proposed weight-row norm>10000 fail the run without clipping/restart. Preserve failure and stable pre-exception small weight snapshot. If operational/stability gates fail, do not launch full stage without a new amendment.

Command: `python -m transit_rl.experiment.function_approx_comparison --run --preflight --output <unique-output>`, using existing project `.venv-visualizer/Scripts/python.exe`. Config schedule remains300while actual budget2recorded explicitly. Preflight can inform runtime/resources only; no feature/alpha tuning from service results. A separate full-execution amendment must be committed after reviewing preflight.

## Full screen planned before preflight

Fresh E/L learners at seeds2034/2035/2036,300episodes, checkpoints0/100/300 each ties7100/7101/7102. E rerun despite known Stage4B. Same alpha.1,gamma1,epsilon1→.05 by240then.05, same data/day/reward and60actions. Three serial seed waves, two worker processes/wave. Initial planned guard900measured training seconds/worker to accommodate feature overhead; finalize runtime ceiling prospectively after preflight. Time/setup/evaluation/logging separate. Do not compare paired time against prior serial speed; do not change episode budget by quality. No model/feature hyperparameter sweep.

Primary: final demand-weighted daily served fraction, average ties within each model then paired L−E per seed. Report mean/min/max paired differences, reward, raw-key novelty (not guidance for L), predictive audit, fleet, route/stop/discard outcomes, stability, parameter count, exact audit sizes and measured memory/runtime. Screen advancement requires mean service gain≥2percentage points, no paired seed service decrease and mean reward not lower. This is not statistical superiority or automatic default adoption. Three independent training seeds/arm, not all evaluation days as independent models. Same training demand; no held-out/convergence/optimality claim.

## Retention and failure handling

Registered `analysis/summarise_function_approx.py` handles preflight/full, validates counts/accounting/source/config identity, E historical reproduction, matching empty-model/first-exploration outcomes and evaluation digest immutability including L weights. Full study requires all six completions; otherwise report incomplete/stability/resource failure without normal final aggregation. Stop future seed waves on child failure; retain completed/interrupted attempts, no silent replacement. New IDs on rerun.

Retain all per-episode metrics, gzip full training-hour records, checkpoint evaluations with final route plans, features/numerical settings, dependencies/commands/machine/power/clock/resource records, wave statuses and SHA-256 inventory. L checkpoint/final weights (256 parameters) are small interpretation artifacts, not complete resume checkpoints; E's large Q tables not saved. About12–20MiB expected full archive, no PDF/UI. Verify archive regenerates and raw Git blobs match. Separate source/evidence commits; local backup only, no push/delete/merge authorized. Existing unrelated documentation edits preserved.
