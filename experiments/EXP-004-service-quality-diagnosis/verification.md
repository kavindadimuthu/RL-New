# EXP-004 verification

2026-11-17 instrumentation development: initial four diagnostic tests passed, including two matched real-data training episodes. An explicit per-action trace equality check was then added. Final full-suite outcome recorded after execution below. No scientific treatment or production-default changes.

Tests cover separate no-path/capacity categories, transfer eligibility, trip cutoff, forced discard, action counts and exact training/operational-cache equivalence. Diagnostic helper uses private production route/path APIs intentionally, so future changes must rerun these checks.

Final instrumentation gate: `python -m unittest discover -s tests -v` using existing `.venv-visualizer` interpreter: **62 tests passed**, 4.144 seconds test runtime. Includes exact per-action traces for both real-data episodes. Runner additionally asserts complete Q/visit dictionaries and learner RNG unchanged across its three read-only evaluations.

Preflight source `da64b82`: completed;120hourly records, two training episodes, three evaluation ties. Accounting, visit/action counts, fleet identities, capacity bounds and clock consistency verified by `analysis/summarise_preflight.py`. Raw files hashed in `preflight-verification.json`. Read-only evaluation Q/visits/RNG checks passed in runner. No failed preflight run. Analysis implementation is post-execution and does not retrain.

Full-baseline registration: 63 tests passed (3.995s), including digest mutation detection and diagnostic summary accounting in addition to prior exact trajectory checks. Full stage source, protocol and analysis are committed before execution; use clean isolated worktree. See `stage1-baseline.md` for the final budget/checkpoint/retention procedure.
