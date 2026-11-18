# EXP-004-D01: remaining-action observation screen

Date 2026-11-17; basis [Stage-4 results](stage4-results.md), prospective source `f274f24`.

Retain original A as the project's default and continuing baseline. B (same exact key plus remaining actions) did not meet the registered practical-advancement rule after 300 episodes at three paired seeds: mean service âˆ’0.2172 percentage points, mixed per-seed direction, near-identical mean reward, persistent high unseen-state fraction and more Q states. Do not claim a statistically established negative effect or dismiss deadline information generally.

Keep the tested B implementation/results for inspection. A's hidden remaining-action concern remains a formulation limitation; this finite-budget result does not prove omitting time is correct. Neither state default, reward, stopping rule nor passenger assignment changed in production.

Keep the verified 60-action reference as a quality baseline. Next direction: a separately registered knowledge-reuse/generalization study with matched deadline handling between arms; exact method/resources require prospective design. No automatic experiment continuation, heuristic imitation, reward redesign or 70% finish requirement is authorized by this decision record alone.

All raw evidence and negative/uncertain findings retained locally. No off-machine backup/push verified, no outputs deleted. Execution commit and subsequent evidence commit serve distinct roles.

## EXP-004-D02: linear-Q stability stop, 2026-11-17

Basis: [Stage-5 results](stage5-results.md), prospective sources `a84499b` and `89ebd99`.

Do not advance or deploy this linear semi-gradient Q variant. Its seed-2034 run completed 48 episodes, then exceeded the registered Q bound during 49. Stop later seed waves as registered; full three-pair quality comparison is incomplete, not a computed failure of the service-improvement criterion. No algorithm/feature/learning-rate rescue tuning or rerun was performed.

Keep preflight, failed-run metrics/manifests, final stored finite weights and completed exact control. Parameters at failure are not certified stable. This finding does not establish that knowledge sharing or DQN is ineffective. Original production/default remains unchanged.

Next design a separately preregistered stability-focused update revision with fixed features and transport settings before another quality comparison. Candidate stabilizers/alternative updates need prospective choice and tests; no automatic larger neural run, reward change or service threshold is implied.


## Stage 6 update — 2026-11-18

Fixed smaller-step diagnostic completed 300 episodes at one seed without a numerical guard, but both trained checkpoints served 0% by immediately finishing every hour. Not adopted; no larger quality comparison launched. See [Stage 6 results and D03](stage6-results.md), [registered protocol](stage6-linear-stability.md), and `linear-stability-verification.json`. Analysis path-normalization correction is disclosed in the results.


## Stage 7 update — 2026-11-18

Frozen-model diagnostic confirms stopping is ranked above productive reference construction; fixed trajectories serve 0%, 20.9348% and 90.7308%. Positive dense rewards already occur during construction. Cause of learning failure remains unisolated. See [Stage 7 results and D04](stage7-results.md), [registered protocol](stage7-stopping-diagnostic.md) and `stopping-verification.json`. No training or adoption; analysis-only visitation-check correction disclosed.


## Stage 8 update — 2026-11-18

Fixed-return fitting corrects the initial stopping/construction preference but leaves pooled RMSE 1.0440 despite no conflicting training labels. Frozen alpha .001 updates provide tiny local corrections. No causal attribution, new online policy or adoption. See [Stage 8 results and D05](stage8-results.md), [registered protocol](stage8-return-fit.md), and `return-fit-verification.json`. Next proposed test isolates interaction features on fixed data.
