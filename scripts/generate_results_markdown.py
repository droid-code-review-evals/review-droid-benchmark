#!/usr/bin/env python3
"""
Generate RESULTS.md and README.md from evaluation JSON.
Usage: python3 scripts/generate_results_markdown.py <run_name> [baseline_run_name]
Example: python3 scripts/generate_results_markdown.py run_2026-01-14-v2 run_2026-01-14
"""

import json
import os
import sys
from datetime import datetime

def load_eval_json(run_name: str) -> dict:
    """Load evaluation JSON for a run."""
    path = os.path.expanduser(f"~/review-droid-benchmark/results/{run_name}/sentry_eval.json")
    with open(path) as f:
        return json.load(f)

def generate_results_md(run_name: str, eval_data: dict, baseline_data: dict = None) -> str:
    """Generate RESULTS.md content."""
    
    lines = [
        f"# Evaluation Results - {run_name}",
        "",
        f"**Date:** {datetime.now().strftime('%Y-%m-%d')}",
        f"**Repository:** droid-sentry",
        f"**PRs Evaluated:** #6-15 (10 PRs)",
        "",
        "## Summary Metrics",
        ""
    ]
    
    summary = eval_data["summary"]
    
    if baseline_data:
        baseline_summary = baseline_data["summary"]
        lines.extend([
            "| Metric | This Run | Baseline | Change |",
            "|--------|----------|----------|--------|",
            f"| **True Positives (TP)** | {summary['total_tp']} | {baseline_summary['total_tp']} | {summary['total_tp'] - baseline_summary['total_tp']:+d} ({((summary['total_tp'] - baseline_summary['total_tp']) / baseline_summary['total_tp'] * 100) if baseline_summary['total_tp'] > 0 else 0:+.1f}%) |",
            f"| **False Positives (FP)** | {summary['total_fp']} | {baseline_summary['total_fp']} | {summary['total_fp'] - baseline_summary['total_fp']:+d} ({((summary['total_fp'] - baseline_summary['total_fp']) / baseline_summary['total_fp'] * 100) if baseline_summary['total_fp'] > 0 else 0:+.1f}%) |",
            f"| **False Negatives (FN)** | {summary['total_fn']} | {baseline_summary['total_fn']} | {summary['total_fn'] - baseline_summary['total_fn']:+d} ({((summary['total_fn'] - baseline_summary['total_fn']) / baseline_summary['total_fn'] * 100) if baseline_summary['total_fn'] > 0 else 0:+.1f}%) |",
            f"| **Precision** | {summary['precision']}% | {baseline_summary['precision']}% | {summary['precision'] - baseline_summary['precision']:+.1f}% |",
            f"| **Recall** | {summary['recall']}% | {baseline_summary['recall']}% | {summary['recall'] - baseline_summary['recall']:+.1f}% |",
            f"| **F-Score** | {summary['f_score']}% | {baseline_summary['f_score']}% | {summary['f_score'] - baseline_summary['f_score']:+.1f}% |",
        ])
    else:
        lines.extend([
            "| Metric | Value |",
            "|--------|-------|",
            f"| **True Positives (TP)** | {summary['total_tp']} |",
            f"| **False Positives (FP)** | {summary['total_fp']} |",
            f"| **False Negatives (FN)** | {summary['total_fn']} |",
            f"| **Precision** | {summary['precision']}% |",
            f"| **Recall** | {summary['recall']}% |",
            f"| **F-Score** | {summary['f_score']}% |",
        ])
    
    lines.extend([
        "",
        "## Per-PR Breakdown",
        ""
    ])
    
    if baseline_data:
        baseline_prs = {pr["pr_number"]: pr for pr in baseline_data["prs"]}
        lines.extend([
            "| PR # | Title | Golden | Droid | TP | FP | FN | Precision | Recall | v1 Precision | v1 Recall |",
            "|------|-------|--------|-------|----|----|-------|-----------|--------|--------------|-----------|"
        ])
        for pr in eval_data["prs"]:
            baseline_pr = baseline_prs.get(pr["pr_number"], {})
            baseline_metrics = baseline_pr.get("metrics", {})
            m = pr["metrics"]
            title_short = pr["pr_title"][:40] + "..." if len(pr["pr_title"]) > 40 else pr["pr_title"]
            
            baseline_prec = f"{baseline_metrics.get('precision', 0):.1f}%" if baseline_metrics else "N/A"
            baseline_rec = f"{baseline_metrics.get('recall', 0):.1f}%" if baseline_metrics else "N/A"
            
            lines.append(
                f"| {pr['pr_number']} | {title_short} | {pr['golden_count']} | {pr['droid_count']} | "
                f"{m['tp']} | {m['fp']} | {m['fn']} | {m['precision']:.1f}% | {m['recall']:.1f}% | "
                f"{baseline_prec} | {baseline_rec} |"
            )
    else:
        lines.extend([
            "| PR # | Title | Golden | Droid | TP | FP | FN | Precision | Recall |",
            "|------|-------|--------|-------|----|----|-------|-----------|--------|"
        ])
        for pr in eval_data["prs"]:
            m = pr["metrics"]
            title_short = pr["pr_title"][:50] + "..." if len(pr["pr_title"]) > 50 else pr["pr_title"]
            lines.append(
                f"| {pr['pr_number']} | {title_short} | {pr['golden_count']} | {pr['droid_count']} | "
                f"{m['tp']} | {m['fp']} | {m['fn']} | {m['precision']:.1f}% | {m['recall']:.1f}% |"
            )
    
    lines.extend([
        "",
        "## Detailed Analysis",
        "",
        "### By Performance",
        ""
    ])
    
    # Sort PRs by F-score
    sorted_prs = sorted(eval_data["prs"], key=lambda x: x["metrics"]["f_score"], reverse=True)
    
    lines.append("#### Top Performing PRs (by F-Score)")
    lines.append("")
    for pr in sorted_prs[:3]:
        m = pr["metrics"]
        lines.extend([
            f"**PR #{pr['pr_number']}: {pr['pr_title']}**",
            f"- F-Score: {m['f_score']:.1f}% (Precision: {m['precision']:.1f}%, Recall: {m['recall']:.1f}%)",
            f"- TP={m['tp']}, FP={m['fp']}, FN={m['fn']}",
            ""
        ])
    
    lines.append("#### Lowest Performing PRs (by F-Score)")
    lines.append("")
    for pr in sorted_prs[-3:]:
        m = pr["metrics"]
        lines.extend([
            f"**PR #{pr['pr_number']}: {pr['pr_title']}**",
            f"- F-Score: {m['f_score']:.1f}% (Precision: {m['precision']:.1f}%, Recall: {m['recall']:.1f}%)",
            f"- TP={m['tp']}, FP={m['fp']}, FN={m['fn']}",
            ""
        ])
    
    lines.extend([
        "## Raw Data",
        "",
        "Full evaluation data available in: `sentry_eval.json`",
        ""
    ])
    
    return "\n".join(lines)

def generate_readme_md(run_name: str, eval_data: dict, config_notes: str = None) -> str:
    """Generate README.md content."""
    
    summary = eval_data["summary"]
    
    lines = [
        f"# Run {run_name}",
        "",
        "## Overview",
        "",
        f"**Run Name:** {run_name}",
        f"**Date:** {datetime.now().strftime('%B %d, %Y')}",
        f"**Repository:** droid-code-review-evals/droid-sentry",
        f"**PRs Evaluated:** #6-15 (10 PRs total)",
        "",
        "## Configuration",
        ""
    ]
    
    if config_notes:
        lines.append(config_notes)
    else:
        lines.extend([
            "**Type:** Standard evaluation run",
            "",
            "This run evaluates the review droid's performance on the droid-sentry benchmark PRs.",
        ])
    
    lines.extend([
        "",
        "## Results Summary",
        "",
        "| Metric | Value |",
        "|--------|-------|",
        f"| **True Positives** | {summary['total_tp']} |",
        f"| **False Positives** | {summary['total_fp']} |",
        f"| **False Negatives** | {summary['total_fn']} |",
        f"| **Precision** | {summary['precision']}% |",
        f"| **Recall** | {summary['recall']}% |",
        f"| **F-Score** | {summary['f_score']}% |",
        "",
        "## Files in This Run",
        "",
        "```",
        f"{run_name}/",
        "├── README.md                           # This file",
        "├── RESULTS.md                          # Detailed analysis and per-PR breakdown",
        "├── sentry_eval.json                    # Full evaluation data",
        "├── golden_comments.json                # Golden comments for reference",
        "├── pr_*_comments.json                  # Raw PR comments from GitHub",
        "└── raw_comments/",
        "    ├── droid-sentry.json              # Consolidated droid comments",
        "    └── golden_sentry.json             # Golden comments in eval format",
        "```",
        "",
        "## Methodology",
        "",
        "1. **Reset PRs:** Remove all existing bot comments from PRs #6-15",
        "2. **Trigger Reviews:** Manual review triggering via `@droid review`",
        "3. **Fetch Comments:** Retrieve all comments via GitHub API",
        "4. **Transform Data:** Convert to evaluation format",
        "5. **Run Evaluation:** Use Claude to match comments against golden set",
        "6. **Generate Reports:** Create detailed analysis and metrics",
        "",
        "## Notes",
        "",
        "- Evaluation uses semantic matching via LLM, not exact string matching",
        "- Per-PR metrics calculated programmatically from TP/FP/FN counts",
        "- See RESULTS.md for detailed per-PR breakdown and analysis",
        ""
    ])
    
    return "\n".join(lines)

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 generate_results_markdown.py <run_name> [baseline_run_name]")
        sys.exit(1)
    
    run_name = sys.argv[1]
    baseline_name = sys.argv[2] if len(sys.argv) > 2 else None
    
    # Load evaluation data
    eval_data = load_eval_json(run_name)
    baseline_data = load_eval_json(baseline_name) if baseline_name else None
    
    # Generate RESULTS.md
    results_md = generate_results_md(run_name, eval_data, baseline_data)
    results_path = os.path.expanduser(f"~/review-droid-benchmark/results/{run_name}/RESULTS.md")
    with open(results_path, "w") as f:
        f.write(results_md)
    print(f"Generated: {results_path}")
    
    # Generate README.md
    readme_md = generate_readme_md(run_name, eval_data)
    readme_path = os.path.expanduser(f"~/review-droid-benchmark/results/{run_name}/README.md")
    with open(readme_path, "w") as f:
        f.write(readme_md)
    print(f"Generated: {readme_path}")
    
    print("\n✅ Documentation generated successfully")

if __name__ == "__main__":
    main()
