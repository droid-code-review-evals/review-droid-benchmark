#!/usr/bin/env python3
"""
Fetch and evaluate Claude Code review comments against golden comments.
Usage: python3 scripts/evaluate_claude_code.py [run_name]

If run_name not provided, defaults to claude_code_run_YYYY-MM-DD.

Note: Claude Code posts a single issue comment per PR (not inline review comments).
The comment body is split into individual findings by numbered markdown headings.
"""

import os
import sys
from pathlib import Path
from eval_common import BASE_DIR, fetch_issue_comments, run_evaluation

ORG = "droid-code-review-evals"
REPO_PREFIX = "claude_code"
BOT_LOGIN = "claude[bot]"
TOOL_NAME = "claude_code"


def main():
    if len(sys.argv) >= 2:
        run_name = sys.argv[1]
    else:
        run_name = f"claude_code_run_{os.popen('date +%Y-%m-%d').read().strip()}"

    run_dir = BASE_DIR / "results" / run_name
    run_dir.mkdir(parents=True, exist_ok=True)

    fetch_only = "--fetch-only" in sys.argv
    eval_only = "--eval-only" in sys.argv

    if not eval_only:
        print(f"=== Fetching {TOOL_NAME} comments ===")
        fetch_issue_comments(ORG, REPO_PREFIX, BOT_LOGIN, run_dir)

    if not fetch_only:
        print(f"\n=== Evaluating {TOOL_NAME} comments ===")
        run_evaluation(TOOL_NAME, REPO_PREFIX, run_name, use_issue_comments=True)


if __name__ == "__main__":
    main()
