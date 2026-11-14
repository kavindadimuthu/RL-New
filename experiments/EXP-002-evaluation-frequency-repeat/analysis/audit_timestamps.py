"""Post-hoc audit of UTC spans versus perf-counter/CPU measurements.

Added after execution because a large timestamp discrepancy was observed.
This does not change, exclude, replace, or pool any training observations.
"""
from datetime import datetime
import json
from pathlib import Path

study=Path(__file__).resolve().parents[1]
root=study/'evidence'
runs=json.loads((root/'results.json').read_text())
records=[]
for run in runs:
    job=run['job']
    meta=json.loads((root/job['phase']/job['run_id']/'manifest.json').read_text())
    span=(datetime.fromisoformat(meta['finished_at'])-datetime.fromisoformat(meta['started_at'])).total_seconds()
    elapsed=run['process_wall_seconds_including_evaluation']
    difference=span-elapsed
    records.append(dict(run_id=job['run_id'],phase=job['phase'],training_seed=job['seed'],
                        utc_span_seconds=span,recorded_process_elapsed_seconds=elapsed,
                        training_seconds=run['training_seconds'],training_cpu_seconds=run['training_cpu_seconds'],
                        span_minus_elapsed_seconds=difference,flagged=abs(difference)>5))
output=dict(post_hoc=True,threshold_seconds=5,
            note='Diagnostic threshold chosen after observing a large discrepancy; not a prespecified exclusion rule. Start/end UTC also include setup. Cause is unknown. No observations excluded.',
            records=records)
(study/'summaries/timestamp_audit.json').write_text(json.dumps(output,indent=2)+'\n',encoding='utf-8')
flagged=[r for r in records if r['flagged']]
lines=['# Post-hoc timing review: EXP-002','',
       'The timestamp audit identified a discrepancy between wall-calendar UTC intervals and the recorded monotonic performance-counter/CPU measurements. The cause was not independently recorded. Do not attribute it to sleep, clock correction, or another cause as an established fact.','',
       'This audit was added after observing the discrepancy. A five-second diagnostic threshold allows ordinary setup overhead but is not a prespecified exclusion rule. Original observations/manifests are unchanged; no seed was silently removed or replaced.','',
       '| Run | UTC span seconds | Process elapsed seconds | Training seconds | Training CPU seconds |',
       '|---|---:|---:|---:|---:|']
for r in flagged:
    lines.append(f"| {r['run_id']} | {r['utc_span_seconds']:.2f} | {r['recorded_process_elapsed_seconds']:.2f} | {r['training_seconds']:.2f} | {r['training_cpu_seconds']:.2f} |")
lines+=['','## Interpretation','',
        f'{len(flagged)} of 21 trained runs were flagged. Consult summaries/timestamp_audit.json for all runs, including the unflagged ones.','',
        'The affected equal-time jobs met the recorded training-counter budget and each used approximately the same CPU time. This supports comparing their measured compute budgets, but it does not establish an uninterrupted two-minute wall-calendar experience. The recorded UTC study span includes this discrepancy and must not be presented as active training duration.','',
        'Treat Stage 3 as qualified evidence with a timing/provenance anomaly. Do not use it alone for a publication claim about wall-clock efficiency. Stage 1 provides serial timing measurements, and Stage 2 compares fixed episode counts; neither is automatically validated by this supplemental audit alone. If uninterrupted real-time behavior is a research requirement, run a separately identified, prospectively amended repeat rather than overwrite these runs.','',
        'This finding is a deviation/limitation of the execution record, not a reason to edit original outputs. Analysis tables retain all originally planned seeds. No additional training was performed for this audit.']
(study/'timing_review.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
print(f'Post-hoc timestamp audit: {len(flagged)} flagged runs; originals unchanged.')
