# EXP-002 verification and deviations

Protocol v1.0 created before the new execution. Legacy findings are known and explicitly disclosed.

Pre-execution correctness tests: **43 passed**, including fixed-action reward conservation, evaluator isolation, and failure-manifest preservation. Command: `.\.venv-visualizer\Scripts\python.exe -m unittest discover -s tests -v`. Original output is retained in `preexecution/correctness-tests.txt`.

Process preflight passed: three independent Windows-spawned processes loaded the real 15-stop network and all 24 OD matrices with numerical-library thread limits of one. No training was performed by preflight. See `preexecution/process-preflight.json`, `plan.json` and `checks.json`. The committed analysis script passed a Python syntax check.

Execution commit: recorded automatically in every runtime manifest; no retrospective substitution.
Post-execution checks passed for all 21 planned trained runs and the prespecified untrained diagnostic: unique IDs, completed counts/budgets/checkpoints, UTC timestamp ordering, resolved settings/seeds, finite numerical outputs, source/input hashes and archive copy hashes. The archive-only analysis regenerated identical comparison JSON bytes without learning. See `postexecution-checks.json` and `archive_checksums.json`.

Execution code commit: `d8885c7`. The later evidence archive is identified by annotated tag `research/EXP-002-v1`; the archive does not retroactively become the execution version.

Artifact policy: final Q-tables/checkpoints not saved; compact original numerical outputs retained.
Backup status: local Git only until an off-machine backup is explicitly verified. No external publication is implied.

## Execution deviation: Stage 3 timestamp anomaly

An independent post-run audit found that the first equal-time wave (seed 2027, all three treatments) spans approximately 7,392–7,393 UTC seconds while each worker records approximately 121–122 monotonic process seconds and approximately 120 training CPU seconds. The cause was not independently captured. No precise physical explanation is claimed. Original UTC/counter measurements are preserved, not corrected or backfilled.

This qualifies Stage 3: its recorded compute budgets were met, but it is not evidence of uninterrupted two-minute wall-calendar execution. Do not claim a six-minute uninterrupted Stage 3 turnaround from these observations. The whole study's recorded UTC span includes the discrepancy; it is not the active training duration.

The supplemental `analysis/audit_timestamps.py` and [timing review](timing_review.md) were added post hoc, with their diagnostic threshold disclosed. They neither change the primary calculations nor exclude/replace seeds. All originally planned observations remain reported. A separate amended repeat would be needed if uninterrupted calendar-time performance is required. Other protocol deviations/failures: none observed; no automatic reruns performed.

## Subsequent diagnosis and closeout

Windows Kernel-Power events subsequently showed idle-timeout entry into Modern Standby and exit over the long calendar gap. The captured events and interpretation are recorded in [closeout.md](closeout.md) and `summaries/standby_events.json`. This supplements the earlier unknown-cause audit rather than rewriting it. The study is closed with the timing qualification retained and the decision in EXP-002-D01 accepted. Off-machine backup remains pending.
