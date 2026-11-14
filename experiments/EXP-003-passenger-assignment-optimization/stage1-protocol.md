# EXP-003 stage 1 protocol v1.0: Real workload capture and baseline profile

Date: 2026-11-14 (Asia/Colombo). This amendment registers the next stage before execution. The foundation protocol remains applicable. This stage does not implement or benchmark an optimized candidate.

## Fixed capture

- Use the byte-frozen baseline assignment, actual repository network/OD data and every-action evaluation A.
- Capture two consecutive complete 24-hour episodes for each seed **2030, 2031**, with fresh learners/environments per seed and the original 10,000-episode exploration schedule. Four short episodes are trace generation, not a learning-quality experiment.
- Record every assignment request in order from episode reset onward, including hour, exact ordered plan/kept flags, cache-hit status, seed/episode and digest of every output field. Capture action sequences and episode outcomes. No sampling based on observed runtime, output score or candidate behavior.
- Retain a deduplicated plan table, ordered queries/actions and input/config/source hashes. Repeated operational keys can reuse their deterministic output digests during capture. Instrumented capture times are not ordinary training-speed measurements.

## Prespecified workloads

1. **training_stream:** full mixed-hit/miss query sequence, default result cache, fresh assigner for each repetition.
2. **miss_stream:** up to 512 unique (hour, ordered routes/frequencies) queries with result caching disabled. Select the first representative of each observed (hour, route-count) bucket, then fill the remaining slots evenly across the other unique queries. Retain original sequence order. Route-table cache may warm within a repetition; this is not a new process per query.
3. **warm_hits:** prepopulate the same selected queries outside timing, then replay that ordered sample four times. Assert every timed request is a cache hit.

The selection code and scenario tests must be committed before capture. These workloads represent the recorded early-training conditions, not all future learned policies. Do not claim universal representativeness or select alternative samples after viewing speed.

## Measurement and profiling

- One serial process, one numerical-library thread, no GPU. Scoped Windows sleep-prevention request for the entire active operation; release previous thread flags afterward. Record actual hardware/power/AC information, exact packages and power events. Do not change global power settings.
- Verify all replay output digests before timing. Do a separate 16-request disposable warm-up, then use fresh assigners for measured repetitions. Serialization, output hashing, setup, warm-cache prefill and verification are excluded from timed loops.
- Three unprofiled repetitions per scenario. Prespecified order: miss/training/hits; hits/training/miss; training/miss/hits. Report individual values, median/range, calls, hit/miss counts, CPU/elapsed time and worker memory. These are baseline costs, not speedup estimates.
- Separately profile miss_stream and training_stream once each with cProfile. Retain cumulative/self-time tables and function-level numeric records. Profile overhead must not be presented as ordinary runtime; cumulative times overlap.
- Guards: at most 5,952 captured assignment requests (four episodes at configured step limits), 240 seconds total active stage time checked between measured blocks, 1.5 GiB working set and 4 GiB minimum free RAM checked before each repetition. Do not silently repeat/replace failed work. Preserve failure metadata and partial measurements. A new attempt requires a new run ID/protocol note.
- Record timezone-aware UTC, monotonic elapsed and process CPU measurements. Flag >5-second global UTC/counter disagreement, sleep/resume events, or unavailable power-event evidence as timing-qualified. A request to stay awake is not an absolute guarantee against explicit sleep or OS policy.

## Decision rule for the next stage

Select and separately prerecord C01 only after this baseline profile is available, prioritizing repeated work with a small, clearly bounded invariance risk. Possible targets are segment-load access, capacity queries or route-topology reuse. Do not yet claim that any is faster. State exact cache lifetime/invalidation, memory bounds and equality tests before implementing the candidate.

Before candidate timings, prerecord repeat counts, balanced baseline/candidate order, acceptance threshold and allowed memory/warm-hit regression. The default remains exact output equality; no tolerance has been approved. Only a candidate that passes strict synthetic/real-data checks can advance to bounded end-to-end training verification. A remains the evaluation schedule throughout.

## Commands and evidence

Before running, tests must pass and protocol, capture, measurement and report-generation code must be committed with a clean worktree:

```powershell
.\.venv-visualizer\Scripts\python.exe -m unittest discover -s tests -v
.\.venv-visualizer\Scripts\python.exe -u -m transit_rl.experiment.assignment_profile --run --output transit_rl/results/EXP-003-S1-baseline-profile-run01
```

Use run ID `EXP-003-S1-baseline-profile-run01`. The command refuses existing outputs and dirty worktrees. Preserve its small evidence, hashes, profiles, derived report, verification and analysis implementation in the tracked study after completion. No full Q-table, checkpoint or PDF is generated. Local Git backup remains distinct from off-machine backup; do not delete scratch evidence or publish remotely without authorization.
