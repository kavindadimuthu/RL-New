# Research experiment and evidence standard

**Version:** 1.0 · **Effective:** 2026-11-14 · **Applies to:** all research contributors

This is the project's shared procedure for planning, recording, reporting and retaining research experiments. Its purpose is to make a reported result traceable without retaining large trained-model exports for every run.

## 1. Retention policy

**Keep the small evidence for every research run. Large trained artifacts are optional.**

| Item | Required retention | Location |
|---|---|---|
| Training, evaluation and analysis source | Exact version | Git |
| Protocol, complete resolved configuration, commands and seeds | Every research run | Git experiment record |
| Input data | Exact version when small and redistributable; otherwise a versioned reference, checksum and retrieval instructions | Git or accessible data archive |
| Environment | Python/platform and dependency versions; recreate instructions | Git experiment record |
| Numerical evidence | Per-episode metrics, final evaluations, relevant resource measurements and status | Git experiment record |
| Interpretation | Summary, per-seed comparisons, limitations and deviations | Git experiment record |
| Large Q-tables, model exports and checkpoints | Optional; retain only for a stated purpose | Outside ordinary Git |
| Generated PDFs | Outside Git, following the team's existing decision | Local or shared document storage |
| Temporary arrays, previews, duplicate exports and regenerable plots | Not required | Disposable working storage |

Do not require cloud storage or local long-term storage of large model outputs. If a selected checkpoint is needed for a publication, demonstration, independent inspection or expensive restart, record why it is retained and where it can be retrieved. A checksum without an accessible file does not preserve an artifact.

Small numerical metrics are original run outputs, and must be retained even when large model files are discarded. Never discard the only evidence supporting a reported number. Keep failed/interrupted research runs with their status and reason; a minimal failure record is sufficient when no metrics were produced. Disposable code smoke tests do not need independent experiment IDs, but relevant correctness-check commands/outcomes belong in the study record.

## 2. IDs and directory layout

Use one stable study ID per research question, such as `EXP-001-evaluation-frequency`. Its stages, treatments, independent training seeds and repeated executions are separate fields. A run ID might be `EXP-001-S2-A-seed2024-run01`. Do not reuse a run ID or overwrite an earlier execution.

```text
experiments/
  README.md                         # Study registry
  EXP-001-evaluation-frequency/
    protocol.md
    report.md
    configs/                        # Resolved settings per run
    runs/<run-id>/
      manifest.json
      metrics.jsonl                 # Or a compact CSV
      evaluation.json
      verification.md               # Checks, failure notes, deviations
    analysis/                       # Scripts used to produce published tables
    summaries/                      # Small numerical tables/selected figures
```

Use [the templates](../experiments/_template/) as starting points. `transit_rl/results/` is Git-ignored scratch/output storage, **not the permanent evidence archive**. Copy the selected small evidence into `experiments/<study-id>/` before considering a study archived. Verify that Git actually tracks the intended files. Avoid duplicate source snapshots when a clean code commit already identifies the exact implementation.

Target KiB-sized manifests and MiB-sized metric archives rather than full state/action dumps. Review unexpectedly large files before adding them. Keep machine-specific virtual environments out of Git. Do not place secrets or private/local-only data in public records; document lawful access to restricted inputs without exposing credentials.

## 3. Before running

1. Write the question, treatments, primary metric, evaluation procedure, seeds, budgets and stopping rules in `protocol.md`.
2. Specify what is held fixed and what changes. State the exploration schedule explicitly, including whether it follows episode count or training time.
3. Record the planned number of independent training seeds. Evaluation tie-breaking seeds do not count as additional independently trained models.
4. Test relevant invariants. For reward-timing comparisons, replay fixed actions and check matching final passenger outcomes and daily reward objectives.
5. Work on an appropriate feature/study branch. Keep alternative methods selectable by configuration where practical; do not create a branch for every seed.
6. Commit the runnable code, protocol and analysis implementation before new research runs. Record the exact execution commit. Save resolved settings, dependency versions and input hashes. Use unique output paths and check resources.

Existing runs performed with uncommitted changes are valid records of what occurred, but must be labelled honestly. Preserve their original source snapshots/patches and hashes, including untracked experiment scripts. Do not retroactively claim that a later commit was their execution version. A documented post-run archive commit can reference those snapshots.

## 4. During running

- Start a fresh independent learner per training seed unless transfer/resume is part of the protocol.
- Record timestamps (with timezone), episode counts, training steps, rewards, service metrics and relevant memory/assignment counts. Flush metrics periodically so interrupted work can be inspected.
- Define timing boundaries. Distinguish training elapsed time, process CPU time, evaluation time and total process elapsed time. Report episode-boundary overshoot for time budgets.
- Keep comparison hardware settings consistent. Record worker count, numerical-library thread limits, hardware, AC/power scheme when relevant, and whether jobs ran concurrently. Avoid comparing parallel elapsed times directly with a serial baseline as though resource use were identical.
- Evaluation must not update the training Q-table/visits or consume the training RNG. Use a common evaluator and recorded independent evaluation seeds.
- Record failures, memory guards and protocol deviations. Do not quietly exclude or replace a failed run. Give a rerun a new ID and link its predecessor.
- If settings/code need to change, stop and create a documented protocol revision/new run. Keep the old record.

## 5. After running and before reporting

1. Check completion status, expected run/episode counts, finite outputs, settings and relevant objective invariants. Explicitly label incomplete jobs.
2. Preserve per-run results, not just the best run or a combined mean. For repeated evaluation randomness, average within each trained model before aggregating across independent training seeds.
3. Generate summaries using retained analysis scripts. State whether uncertainty is a range, standard deviation, standard error or confidence interval, and how it was calculated. Three training seeds are a screening study, not automatic evidence of statistical superiority.
4. State whether evaluation uses training demand or held-out demand. For this raw-state learner, report unseen evaluation-state fractions alongside service quality when available.
5. Separate measured results, projections and explanations. Label added analyses as post-hoc. Negative findings and limitations are part of the record.
6. Copy the small evidence, analysis scripts, report and metadata from scratch storage into the tracked study folder. Check that tables can be regenerated from the retained evidence without retraining.
7. Verify that referenced inputs and exact code versions can be recovered. Missing data, dependencies or model checkpoints must be listed rather than assumed available.
8. Commit the evidence/report and update the registry. Record both the original code commit and the later evidence commit; they serve different purposes.
9. Push/back up the Git record to an agreed team repository. Local commits alone are not an off-machine backup. Do not publish or change access without the team's authorization.

## 6. Discarding large files

Large generated artifacts can be deleted after the small evidence has been verified and backed up, and after confirming they are not selected publication/demonstration/resume artifacts. Record `not_saved`, `retained`, `discarded` or `unavailable` for relevant artifact categories. If discarded, retain available filename/type, checksum, reason and regeneration command; do not invent missing historical hashes.

Deleting a trained checkpoint removes the ability to inspect that exact trained table. Rerunning produces a new execution and must receive a new run ID. Even with the same seed, timing-based schedules, hardware and dependency changes can alter outcomes. Reproducibility means the procedure and claims can be checked; it is not a promise of identical timing or model bytes.

This standard does not delete any files automatically. Existing training commands may still generate Q-table exports; retention rules are separate from output-generation behavior.

## 7. Review, releases and corrections

- Put retained small numerical evidence and protocols through normal peer review together with code. A useful review follows one headline result back to its run-level metrics.
- Experiment code and findings can be merged into master without adopting a tested method as the default.
- Tag reviewed milestones/publication versions. Treat released tags as fixed; use a new version for corrections. Back up/access-control any separately retained artifacts.
- Correct mistakes transparently. Preserve original observations, document the correction and regenerate derived summaries in a new commit. Do not rewrite historical runs to match new conclusions.
- For publication, include exact reproduction instructions, data access/licensing, suitable citation/license information and, when appropriate, an archival release with a persistent identifier.

## 8. Adopting this standard for existing work

Inventory existing studies separately from adoption of this standard. Mark evidence that remains in Git-ignored working directories as awaiting permanent archiving. Preserve source snapshots, manifests and any record of uncommitted execution changes. Archive related stages under one study ID while retaining their original provenance.

Adopting this guide does not itself migrate, commit, back up or delete existing outputs. Apply its verification and retention procedure before changing their storage.

## References

- [NeurIPS reproducibility checklist](https://neurips.cc/public/guides/PaperChecklist): settings, reproduction instructions, uncertainty and compute reporting.
- [DVC data/model versioning](https://doc.dvc.org/example-scenarios/versioning-data-and-models): optional approach for linking externally stored artifacts to Git.
- [GitHub research citation/archiving guidance](https://docs.github.com/en/repositories/archiving-a-github-repository/referencing-and-citing-content): archival releases and persistent identifiers.
