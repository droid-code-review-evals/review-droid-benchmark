# Review Droid Benchmark

Benchmark suite for evaluating [Droid](https://github.com/factory-ai/droid-action) code review against a golden comment dataset.

## Overview

This project measures Droid's code review quality using the [AI Code Review Evaluations](https://github.com/ai-code-review-evaluations) dataset:

| Metric | Value |
|--------|-------|
| Repositories | 5 (Sentry, Grafana, Keycloak, Discourse, Cal.com) |
| Total PRs | 50 (10 per repo) |
| Golden Comments | 145 |
| Languages | Python, Go, Java, Ruby, TypeScript |

### Current Performance (droid-sentry)

| Metric | Value |
|--------|-------|
| Precision | 52.6% |
| Recall | 23.8% |
| F-Score | 32.8% |

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
- Validating droid comments against actual code
- Auditing golden comment quality
- Establishing ground truth beyond string matching

Ground truth validation results are stored in `results/ground_truth_validation/`.

## Analysis & Results

### Architecture

**[Architecture](docs/ARCHITECTURE.md)** - System design for the evaluation loop, semantic matching approaches, and improvement recommendations.

### Performance Analysis

- **[Trace Analysis](docs/analysis/TRACE_ANALYSIS.md)** - Deep dive into why droid achieves current metrics
- **[False Positives](docs/analysis/FALSE_POSITIVES.md)** - Categorization of 63 false positive comments
- **[Missed Issues](docs/analysis/MISSED_ISSUES.md)** - Categorization of 131 missed bugs
- **[Ground Truth Validation Design](docs/analysis/GROUND_TRUTH_VALIDATION_DESIGN.md)** - Plan for automated validation

### Evaluation Results

See **[results/](results/)** for:
- Per-run evaluation data (`run_YYYY-MM-DD/`)
- Run comparisons (`COMPARISON_SUMMARY.md`, `CORRECTED_COMPARISON.md`)
- Ground truth validation outputs (`ground_truth_validation/`)

## Directory Structure

```
review-droid-benchmark/
├── README.md                 # This file
├── docs/
│   ├── SETUP.md              # First-time setup guide
│   ├── EVALS.md              # Running evaluations
│   ├── VALIDATION_PLAYBOOK.md # Manual validation procedure
│   ├── ARCHITECTURE.md       # System design
│   └── analysis/             # Performance analysis docs
├── scripts/                  # Evaluation scripts
│   ├── evaluate_sentry_run.py
│   ├── generate_results_markdown.py
│   └── ...
├── results/                  # Evaluation outputs by run
│   ├── run_2026-01-14/
│   ├── run_2026-01-15/
│   └── ground_truth_validation/
├── repos/                    # Local clones
│   ├── augment-*.git/        # Mirror clones
│   └── golden_comments/      # Golden comment dataset
├── work/                     # Working directories
│   └── droid-*/              # Clones for PR creation
└── PLAN_ARCHIVE.md           # Historical planning document
```

## Quick Links

| Topic | Document |
|-------|----------|
| Setup infrastructure | [docs/SETUP.md](docs/SETUP.md) |
| Run evaluations | [docs/EVALS.md](docs/EVALS.md) |
| Manual validation | [docs/VALIDATION_PLAYBOOK.md](docs/VALIDATION_PLAYBOOK.md) |
| System design | [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) |
| Performance analysis | [docs/analysis/TRACE_ANALYSIS.md](docs/analysis/TRACE_ANALYSIS.md) |
| Results data | [results/](results/) |
