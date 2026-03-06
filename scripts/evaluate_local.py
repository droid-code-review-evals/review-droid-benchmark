#!/usr/bin/env python3
"""
Evaluate local review findings against golden comments.

Usage:
    python3 scripts/evaluate_local.py <run_name> [--tool <name>]

Reads findings from results/{run_name}/local_findings/{repo}_pr{number}.json
Writes eval to results/{run_name}/{tool}_local_eval.json
"""

import sys
from eval_common import run_local_evaluation


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 scripts/evaluate_local.py <run_name> [--tool <name>]")
        sys.exit(1)

    run_name = sys.argv[1]
    tool_name = "local_review"

    i = 2
    while i < len(sys.argv):
        if sys.argv[i] == "--tool" and i + 1 < len(sys.argv):
            tool_name = sys.argv[i + 1]
            i += 2
        else:
            i += 1

    print(f"=== Evaluating local findings for {run_name} ===")
    run_local_evaluation(tool_name, run_name)


if __name__ == "__main__":
    main()
