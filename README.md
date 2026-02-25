# Review Droid Benchmark

Benchmark suite for evaluating [Review Droid](https://github.com/factory-ai/droid-action) against a golden comment dataset.

## Overview

This project measures Droid's code review quality using the [AI Code Review Evaluations](https://github.com/ai-code-review-evaluations) dataset:

| Metric | Value |
|--------|-------|
| Repositories | 5 (Sentry, Grafana, Keycloak, Discourse, Cal.com) |
| Total PRs | 50 (10 per repo) |
| Golden Comments v1 | 145 (original dataset, includes false positives) |
| Golden Comments v3 | 167 (validated and expanded from v1, final benchmark data) |
| Languages | Python, Go, Java, Ruby, TypeScript |

## Getting Started

### First-Time Setup

Follow the **[Setup Guide](docs/SETUP.md)** to:
- Clone the benchmark repositories
- Create the `droid-code-review-evals` org and repos
- Set up the evaluation infrastructure

### Running Evaluations

See **[Running Evaluations](docs/EVALS.md)** for:
- Single repo evaluation (droid-sentry, 10 PRs)
- Full evaluation (all 5 repos, 50 PRs)
- Reset and re-trigger scripts
- Metrics calculation

### Ground Truth Validation

The **[Validation Playbook](docs/VALIDATION_PLAYBOOK.md)** provides a manual procedure for:
- Validating tool comments against actual code
- Auditing golden comment quality
- Establishing ground truth beyond string matching

Ground truth validation results are stored in `results/ground_truth_validation/`.

### Golden Comments v3 (Final Benchmark Data)

v3 is the validated and expanded golden comment dataset, built from v1 through rigorous manual review:

- False positives from v1 identified and removed
- All bugs validated with exact file/line locations
- All bugs classified by type (runtime_error, logic_bug, security, etc.)
- 31 additional true positive bugs added (discovered by Droid, validated manually)
- Total: 145 (v1) → 167 (v3) bugs

Golden comments live in: `target-repos/droid-golden_comments/v3/`

## Evaluation Results

See **[results/](results/)** for per-run evaluation data and ground truth validation outputs.

## Directory Structure

```
review-droid-benchmark/
├── README.md
├── docs/
│   ├── SETUP.md                  # First-time setup guide (Droid)
│   ├── SETUP_AUGMENT.md          # Setup guide for Augment
│   ├── SETUP_BUGBOT.md           # Setup guide for BugBot
│   ├── SETUP_CLAUDE_CODE.md      # Setup guide for Claude Code
│   ├── SETUP_CODEX.md            # Setup guide for Codex
│   ├── SETUP_GREPTILE.md         # Setup guide for Greptile
│   ├── EVALS.md                  # Running evaluations
│   └── VALIDATION_PLAYBOOK.md    # Manual validation procedure
├── scripts/                      # Evaluation scripts
│   ├── eval_common.py            # Shared evaluation utilities (LLM matching, metrics)
│   ├── evaluate_droid.py         # Evaluate Review Droid against v3 golden
│   ├── evaluate_augment.py       # Evaluate Augment against v3 golden
│   ├── evaluate_bugbot.py        # Evaluate BugBot against v3 golden
│   ├── evaluate_claude_code.py   # Evaluate Claude Code against v3 golden
│   ├── evaluate_codex.py         # Evaluate Codex against v3 golden
│   └── evaluate_greptile.py      # Evaluate Greptile against v3 golden
├── results/                      # Evaluation outputs by run
│   ├── *_run_*/                  # Per-tool evaluation runs
│   └── ground_truth_validation/  # Manual validation outputs
├── source-augment-repos/         # Mirror clones of original repos
│   └── golden_comments/          # Original golden comment dataset (v1)
└── target-repos/                 # Repos with PRs for each tool
    ├── {tool}-{repo}/            # Per-tool repo clones with PRs
    └── droid-golden_comments/    # Golden comments repo (v1 + v3)
```

## Quick Links

| Topic | Document |
|-------|----------|
| Setup infrastructure | [docs/SETUP.md](docs/SETUP.md) |
| Run evaluations | [docs/EVALS.md](docs/EVALS.md) |
| Manual validation | [docs/VALIDATION_PLAYBOOK.md](docs/VALIDATION_PLAYBOOK.md) |
| Results data | [results/](results/) |
