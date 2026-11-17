# Stage 3: reference with original 60-action limit

Protocol v1, 2026-11-17, Asia/Colombo. Status at registration: implementation/testing; no real-data stage3run. Stage1/2findings known. Question: does the demand-guided reference still find higher service within the original hourly accepted-action allowance?

## Fixed conditions and treatment

Same deterministic Stage2algorithm, shortest-path candidate generator, residual-demand ranking, top24additions/top12replacements, three replacement rounds, original S−.3O−.3C objective, score tolerance1e-12,2000score requests/hour and120accepted edits/hour. Same production code, data, starting empty plan, inherited previous-hour reference plan, transport constraints and no learning/RNG. No warm start from the105action first-hour solution. No parameter sweep, target threshold or automatic retry.

The only algorithm option added is `action_limit=60`. Every candidate edit carries its complete production-action trace (route construction includes every ADD_STOP and END_ROUTE; replacement includes REMOVE_ROUTE and construction). Before scoring an edit, reject it when already accepted actions + entire edit trace + one reserved FINISH_PLAN exceeds60. Continue to examine other fitting candidates in original deterministic order. Rejected-over-budget encounters do not consume a score request; they are counted separately and may repeat across iterations. This tests an action-aware bounded planner, not a clipped prefix of Stage2.

At most59construction/edit actions plus FINISH_PLAN; finish earlier if no improving fitting edit. No partial route or partial replacement is committed. Search can inspect rejected alternatives and choose a multi-action edit; the RL agent does not have identical lookahead/search access. Same accepted-action budget and transport MDP, not equal-compute or equal-information comparison.

## Verification and execution

Replay all accepted actions through **unmodified60step production deadline** and masks, assignment/reward, no forced ending. Match target plans/order/frequencies, served demand, original hourly scores and day reward. Assert initial previous plan empty; all24hour traces<=60including FINISH_PLAN. No extended replay configuration. Synthetic tests cover limits1/2/3/4/6/60, full-edit atomicity, deadline replay, original deterministic/capacity/budget tests and invalid zero allowance. Run full suite before commit.

Commit source/protocol/analysis before actual measurement. Fresh clean detached checkout `transit_rl/results/EXP-004-S3-execution`; original user docs remain untouched. One deterministic unique run, output `transit_rl/results/EXP-004-S3-reference60-run01`. CPU serial one numeric thread, no GPU, scoped sleep prevention. Resource guards unchanged: working set1.5GiB, free RAM4GiB,600s elapsed checked at complete-hour boundaries with possible one-hour overshoot. Save failures and do not overwrite. No model exports/PDFs/UI. Expected roughly1–3minutes from Stage2's51second observation, not a guaranteed time.

```powershell
& 'C:/Users/kavin/Desktop/automation/rl-repo/RL-New/.venv-visualizer/Scripts/python.exe' -m transit_rl.experiment.service_reference_run --run --action-limit 60 --output '<main-worktree>/transit_rl/results/EXP-004-S3-reference60-run01'
```

## Outcomes and analysis

Primary daily demand-weighted served fraction; compare against Stage1three-model mean/range and Stage2single deterministic reference. Secondary original reward, no-path/capacity shares, fleet/routes, peak08/09/16/17versus other service, accepted actions/hour, skipped edit encounters, exhausted action budgets, search score requests and runtime. Do not pool deterministic runs as independent trials or claim statistical/universal superiority. This comparison does not isolate why RL learning is weak, prove global optimality, establish a100%ceiling, or prescribe70%for all demands.

Registered `analysis/summarise_reference60.py` reuses Stage2accounting/settings/source/package verifier and adds strict60step/replay/empty-initial/candidate-pool/unchanged search-knob checks, plus explicit Stage2comparison. Full raw plan, hourly search/actions, config/source/input/package metadata, manifest status, times and SHA-256 inventory retained. All24hours required; incomplete failures reported without completed aggregate. Regenerate archived summary without planning; verify raw Git bytes. Local backup only, no push/merge authorized. Next improvement selected only after this result; no RL default change in this stage.
