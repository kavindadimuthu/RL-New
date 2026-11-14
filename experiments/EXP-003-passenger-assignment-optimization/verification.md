# EXP-003 foundation verification

Frozen reference metadata: baseline.json. Production assignment must remain unchanged during foundation.

Foundation checks passed: **50 unit tests** and **67 strict assignment comparisons** across nine fixture groups. See `preexecution/correctness-tests.txt`, `fixture-verification.json` and `checks.json`. The exact package versions are in `preexecution/requirements-lock.txt`.

The unchanged production implementation matched the independently loaded frozen source for every exercised field, array, derived metric, cache counter and input-immutability check. Negative controls verified detection of altered scalar/array outputs and writable output arrays. This establishes the harness, not universal equivalence or an optimization result.

The Windows scoped sleep request was actually acquired and restored during the short correctness preflight. Injected-API tests covered restoration on benchmark failure, rejected requests and disabled operation. No global power scheme/display setting was changed. Future timing runs still require their own power-state/event evidence; this short check does not guarantee immunity to all forms of sleep or OS policy.

`git diff --exit-code a2f9c04 -- transit_rl/environment/passenger_assignment.py` confirmed the production assignment source was unchanged during foundation. Its byte-preserved reference hash is verified whenever the frozen class is loaded.

Candidate code changes: none. Performance comparisons: not started. Training comparisons: not started. No speedup, memory reduction or equivalence beyond the exercised cases is claimed.

Next action is prospective registration of workload capture/profiling and a specific candidate, followed by differential validation. Off-machine backup remains pending; no files are deleted automatically.
