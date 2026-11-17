# EXP-004 verification

2026-11-17 instrumentation development: initial four diagnostic tests passed, including two matched real-data training episodes. An explicit per-action trace equality check was then added. Final full-suite outcome recorded after execution below. No scientific treatment or production-default changes.

Tests cover separate no-path/capacity categories, transfer eligibility, trip cutoff, forced discard, action counts and exact training/operational-cache equivalence. Diagnostic helper uses private production route/path APIs intentionally, so future changes must rerun these checks.

Final instrumentation gate: `python -m unittest discover -s tests -v` using existing `.venv-visualizer` interpreter: **62 tests passed**, 4.144 seconds test runtime. Includes exact per-action traces for both real-data episodes. Runner additionally asserts complete Q/visit dictionaries and learner RNG unchanged across its three read-only evaluations.
