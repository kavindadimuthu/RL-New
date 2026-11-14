# Contributing to RL-New

Research contributors follow the [research experiment and evidence standard](docs/RESEARCH_EXPERIMENT_STANDARD.md).

- Plan studies and version their code/settings before new research runs.
- Retain small original metrics and evaluations for every research run, including failures.
- Keep large model exports optional and generated PDFs outside Git.
- Use independent training seeds, common evaluation procedures and honest limitations.
- Archive the evidence and back it up before discarding large generated outputs.

Use the [experiment registry and templates](experiments/README.md). Changes to this standard should be reviewed and versioned in Git so all contributors follow the same documented procedure.

Relevant correctness checks:

```powershell
python -m unittest discover -s tests -v
```

Use a Python environment with the project dependencies installed. Record the actual interpreter/environment used in experiment manifests.
