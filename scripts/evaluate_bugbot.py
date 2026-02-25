#!/usr/bin/env python3
"""
Fetch and evaluate Bugbot review comments against golden comments.
Usage: python3 scripts/evaluate_bugbot.py [run_name]

If run_name not provided, defaults to bugbot_run_YYYY-MM-DD.
"""

import os
import sys
from pathlib import Path
from eval_common import BASE_DIR, fetch_inline_comments, run_evaluation

ORG = "droid-code-review-evals"
REPO_PREFIX = "bugbot"
BOT_LOGIN = "cursor[bot]"
TOOL_NAME = "bugbot"


def main():
    if len(sys.argv) >= 2:
        run_name = sys.argv[1]
    else:
        run_name = f"bugbot_run_{os.popen('date +%Y-%m-%d').read().strip()}"

    run_dir = BASE_DIR / "results" / run_name
    run_dir.mkdir(parents=True, exist_ok=True)

    fetch_only = "--fetch-only" in sys.argv
    eval_only = "--eval-only" in sys.argv

    if not eval_only:
        print(f"=== Fetching {TOOL_NAME} comments ===")
        fetch_inline_comments(ORG, REPO_PREFIX, BOT_LOGIN, run_dir)

    if not fetch_only:
        print(f"\n=== Evaluating {TOOL_NAME} comments ===")
        run_evaluation(TOOL_NAME, REPO_PREFIX, run_name)


if __name__ == "__main__":
    main()
