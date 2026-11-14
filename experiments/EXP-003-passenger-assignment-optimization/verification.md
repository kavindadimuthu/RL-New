# EXP-003 foundation verification

Frozen reference metadata: baseline.json. Production assignment must remain unchanged during foundation.

Foundation checks passed: **50 unit tests** and **67 strict assignment comparisons** across nine fixture groups. See `preexecution/correctness-tests.txt`, `fixture-verification.json` and `checks.json`. The exact package versions are in `preexecution/requirements-lock.txt`.

The unchanged production implementation matched the independently loaded frozen source for every exercised field, array, derived metric, cache counter and input-immutability check. Negative controls verified detection of altered scalar/array outputs and writable output arrays. This establishes the harness, not universal equivalence or an optimization result.

The Windows scoped sleep request was actually acquired and restored during the short correctness preflight. Injected-API tests covered restoration on benchmark failure, rejected requests and disabled operation. No global power scheme/display setting was changed. Future timing runs still require their own power-state/event evidence; this short check does not guarantee immunity to all forms of sleep or OS policy.

`git diff --exit-code a2f9c04 -- transit_rl/environment/passenger_assignment.py` confirmed the production assignment source was unchanged during foundation. Its byte-preserved reference hash is verified whenever the frozen class is loaded.

Candidate code changes: none. Performance comparisons: not started. Training comparisons: not started. No speedup, memory reduction or equivalence beyond the exercised cases is claimed.

## Stage 1: real workload and baseline profile

The registered procedure executed from clean commit `d08842d` after 52 passing tests. It captured four short real-data episodes for workload construction; these instrumented capture durations are not ordinary training-speed evidence. Three baseline workload scenarios were measured serially with three repetitions each; cProfile was run separately.

The run completed with the scoped sleep request restored, no recorded standby events, and approximately 0.003 seconds UTC/counter discrepancy. Source/input/workload hashes, configuration, scenario hit/miss counts and all capture identities were verified. Archive-only verification replayed 6,119 exact output hashes and regenerated the baseline report identically. See `stage1-verification.json` and `stage1-checksums.json`.

The archive/replay helper is post-execution verification; primary capture/timing/report code was committed before measurements. No original outputs were altered. No performance improvement or candidate training-equivalence result exists yet. See [stage1-results.md](stage1-results.md) for observations and limitations.

Next action is implementation and strict differential validation of registered C01, then commit its exact candidate/analysis before paired timing. Off-machine backup remains pending; no files are deleted automatically.

## C01 implementation and trial

Completed from clean execution commit `19b9284` after 58 passing tests, 67 fixture comparisons, 6,119 exact real-output hashes and six matching training-episode pairs. Development initially found a float16 signed-zero discrepancy, corrected by limiting the fast path to native float64 before any timing. The failed development version/log and corrected precheck are retained.

All 30 registered serial timing blocks completed in fresh worker processes. Sleep request restoration, clock agreement and empty standby-event record were verified. Raw samples and strict trajectory checks are preserved. C01 did not meet its 10% miss/mixed advancement targets and is not adopted or advanced to training-speed measurement. See [C01-results.md](C01-results.md), `C01-checksums.json` and `C01-verification.json`.

No performance threshold or original numerical output was changed after seeing the result. Archive-only verification regenerates the paired comparison/report byte-for-byte without learning. A future C02 requires its own prospective plan. Off-machine backup is pending.
