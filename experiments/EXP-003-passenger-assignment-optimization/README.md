# EXP-003: Passenger-assignment implementation optimization

Status: C01 implemented and tested as a separate experimental backend. Exact checks passed, but its 2.44% miss/7.25% mixed-stream time reductions did not meet the registered 10% advancement targets. Production assignment remains unchanged.

Goal: calculate the same passenger assignments and evaluation outputs more efficiently while retaining every-action evaluation (A). EXP-002 is closed with [its decision](../EXP-002-evaluation-frequency-repeat/decision.md) and [timing/standby qualification](../EXP-002-evaluation-frequency-repeat/closeout.md) retained.

- [Protocol](protocol.md): fixed behavior, acceptance criteria and staged investigation.
- [Frozen baseline identity](baseline.json): master handoff commit, exact source blob and SHA-256.
- [Reference implementation](reference/passenger_assignment.py): byte-preserved copy; never edit to make a candidate pass.
- [Verification](verification.md): foundation tests/preflight and pending work.
- [Stage-1 results](stage1-results.md): real workloads, serial baseline costs, profile findings and archive verification.
- [C01 candidate plan](candidate-C01-plan.md): next implementation target and registered correctness/performance gates.
- [C01 results and decision](C01-results.md): exact verification, paired timings and non-adoption decision.

Commands from the repository root:

```powershell
.\.venv-visualizer\Scripts\python.exe -m unittest discover -s tests -v
.\.venv-visualizer\Scripts\python.exe -m transit_rl.experiment.assignment_equivalence --output transit_rl/results/EXP-003-preflight
```

The second command performs strict correctness comparisons only. It is not a timing benchmark or RL training experiment. Preserve its small result under preexecution/ before committing the foundation. It refuses an existing output directory; choose a new path for a repeated preflight.

Next step: separately register C02 with a broader optimization hypothesis. C01 is retained as a modest-improvement result and does not advance to end-to-end speed trials under its current protocol. No new candidate has started.

[Stage-1 protocol](stage1-protocol.md) now registers fixed real-data workload capture and baseline profiling. It uses separate ordinary timings and profiler runs, and does not execute an optimization candidate.

Regenerate/verify stage-1 baseline evidence without training:

```powershell
.\.venv-visualizer\Scripts\python.exe experiments/EXP-003-passenger-assignment-optimization/analysis/archive_stage1.py --input experiments/EXP-003-passenger-assignment-optimization/evidence/stage1 --verify-only
```

Regenerate/verify C01's retained timing tables without training:

```powershell
.\.venv-visualizer\Scripts\python.exe experiments/EXP-003-passenger-assignment-optimization/analysis/archive_c01.py --input experiments/EXP-003-passenger-assignment-optimization/evidence/C01-paired-run01 --verify-only
```

No large model files are needed. Local records are not an off-machine backup; backup remains pending until explicitly verified. No remote publication or automatic deletion is implied.
