# EXP-002 verification and deviations

Protocol v1.0 created before the new execution. Legacy findings are known and explicitly disclosed.

Pre-execution correctness tests: **43 passed**, including fixed-action reward conservation, evaluator isolation, and failure-manifest preservation. Command: `.\.venv-visualizer\Scripts\python.exe -m unittest discover -s tests -v`. Original output is retained in `preexecution/correctness-tests.txt`.

Process preflight passed: three independent Windows-spawned processes loaded the real 15-stop network and all 24 OD matrices with numerical-library thread limits of one. No training was performed by preflight. See `preexecution/process-preflight.json`, `plan.json` and `checks.json`. The committed analysis script passed a Python syntax check.

Execution commit: recorded automatically in every runtime manifest; no retrospective substitution.
Post-execution checks, archive copy hashes, table regeneration and final evidence commit: pending.

Artifact policy: final Q-tables/checkpoints not saved; compact original numerical outputs retained.
Backup status: local Git only until an off-machine backup is explicitly verified. No external publication is implied.

Deviations: none recorded at planning time. Preserve and describe any subsequent failure/change here.
