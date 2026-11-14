# EXP-003: Passenger-assignment implementation optimization

Status: foundation and stage-1 real-data baseline profiling completed. C01 is registered but not implemented or timed; no optimization speedup is claimed.

Goal: calculate the same passenger assignments and evaluation outputs more efficiently while retaining every-action evaluation (A). EXP-002 is closed with [its decision](../EXP-002-evaluation-frequency-repeat/decision.md) and [timing/standby qualification](../EXP-002-evaluation-frequency-repeat/closeout.md) retained.

- [Protocol](protocol.md): fixed behavior, acceptance criteria and staged investigation.
- [Frozen baseline identity](baseline.json): master handoff commit, exact source blob and SHA-256.
- [Reference implementation](reference/passenger_assignment.py): byte-preserved copy; never edit to make a candidate pass.
- [Verification](verification.md): foundation tests/preflight and pending work.
- [Stage-1 results](stage1-results.md): real workloads, serial baseline costs, profile findings and archive verification.
- [C01 candidate plan](candidate-C01-plan.md): next implementation target and registered correctness/performance gates.

Commands from the repository root:

```powershell
.\.venv-visualizer\Scripts\python.exe -m unittest discover -s tests -v
.\.venv-visualizer\Scripts\python.exe -m transit_rl.experiment.assignment_equivalence --output transit_rl/results/EXP-003-preflight
```

The second command performs strict correctness comparisons only. It is not a timing benchmark or RL training experiment. Preserve its small result under preexecution/ before committing the foundation. It refuses an existing output directory; choose a new path for a repeated preflight.

Next step: implement C01, differentially verify it against the frozen reference, commit the exact candidate/analysis, and only then run its registered paired timing comparison. Candidate results must not be inferred from baseline profiling.

[Stage-1 protocol](stage1-protocol.md) now registers fixed real-data workload capture and baseline profiling. It uses separate ordinary timings and profiler runs, and does not execute an optimization candidate.

Regenerate/verify stage-1 baseline evidence without training:

```powershell
.\.venv-visualizer\Scripts\python.exe experiments/EXP-003-passenger-assignment-optimization/analysis/archive_stage1.py --input experiments/EXP-003-passenger-assignment-optimization/evidence/stage1 --verify-only
```

No large model files are needed. Local records are not an off-machine backup; backup remains pending until explicitly verified. No remote publication or automatic deletion is implied.
