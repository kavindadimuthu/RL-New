# EXP-002-D01: Evaluation strategy for subsequent work

Date: 2026-11-14 (Asia/Colombo).
Status: accepted project direction, based on the research project owner's decision after reviewing EXP-002.
Evidence: [report](report.md), [per-seed summaries](summaries/comparison.json), and [timing qualification](timing_review.md). Original evidence release: `research/EXP-002-v1`.

## Decision

- **A — every-action evaluation:** retain as the current default and reference baseline for subsequent experiments.
- **B — committed-change evaluation:** retain as a candidate for further investigation. Do not claim equivalence to A; assess service quality, runtime and repeatability in a later protocol.
- **C — hour-end evaluation:** deprioritize for the present research direction because it performed poorly under this study's tested settings and budgets. Preserve its implementation and evidence. This is not a general rejection of hour-end rewards in reinforcement learning.

## Basis and limits

A had the highest mean final reward and passenger coverage in both learning stages of the repeat. B reduced assignment cost but had lower mean quality; it remains a plausible computational trade-off. C's many additional episodes did not compensate for delayed feedback in the equal-time protocol.

This decision is a practical next-step choice from a short-budget, three-training-seed study on fixed demand. It is not a proof of long-run superiority, convergence, or held-out generalization. Stage 3's timing qualification remains applicable. The decision does not change original observations, the prespecified protocol, analysis calculations, or the existing evidence tag.

## Moving to the next experiment

1. Keep EXP-002 as a closed evidence record; add dated follow-up decisions rather than rewriting its findings.
2. Define the next research question under a new study ID and branch based on the reviewed code version. Commit its protocol, configurations, correctness checks and analysis before running.
3. Carry A as the default reference. Include B when the new question concerns the quality/runtime trade-off; it need not be rerun in unrelated experiments. Do not include C by default unless a new hypothesis justifies it.
4. For timing studies, first arrange temporary sleep prevention and record power state/sleep-resume evidence. Keep timing boundaries explicit and preserve any interruptions as deviations.
5. A possible next question is whether passenger assignment can be accelerated without changing results under A. This is a candidate topic, not an executed or approved protocol. Validate identical-action passenger/reward outcomes before comparing speed.
6. Record each later study's outcome and its own decision. Revisit this choice if new evidence changes the trade-off.

No new training, algorithm change, merge to master or remote publication is performed by this decision record.
