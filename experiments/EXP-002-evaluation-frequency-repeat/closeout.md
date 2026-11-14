# EXP-002 closeout

Date: 2026-11-14 (Asia/Colombo). Status: scientific comparison closed; no further training planned under this protocol. Off-machine backup remains an explicit pending archival task.

## Outcome

All 21 planned trained runs and the prespecified untrained diagnostic completed. Original numerical evidence and source provenance are retained, checksummed, and independently regenerable without retraining. The original evidence release `research/EXP-002-v1` remains fixed; later diagnosis/decision/closeout commits supplement it.

Accepted direction: [EXP-002-D01](decision.md). A remains default; B remains a candidate; C is deprioritized under the tested conditions. The results are a three-seed, fixed-demand, short-budget study, not proof of convergence or universal method superiority.

## Follow-up diagnosis of the timing anomaly

The initial timestamp review did not identify a physical cause. A subsequent Windows System log investigation found Kernel-Power event 506, idle-timeout entry into Modern Standby at **16:01:46**, and event 507 on exit at **18:07:46–47**, on 2026-11-14 in Asia/Colombo. See the captured [event evidence](summaries/standby_events.json).

This supports standby as the explanation for the long calendar gap rather than extra model computation. The exact behavior of all counters throughout standby was not independently instrumented. Preserve the original timing qualification: the affected Stage 3 wave is not an uninterrupted wall-calendar trial. No observations were replaced, excluded or retrospectively retimed.

## Handoff

The next study, EXP-003, investigates faster assignment implementation with unchanged outputs and unchanged every-action evaluation. It must use its own branch, protocol, baseline identity, verification and run IDs. Temporary sleep prevention and retained timing/power evidence are prerequisites for new performance runs.

The reference assignment and all A/B/C implementations remain available. Closing the study does not delete outputs, alter archived observations, adopt C, or claim off-machine backup. No remote publication is authorized by this closeout.
