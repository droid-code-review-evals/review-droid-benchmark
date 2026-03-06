#!/usr/bin/env python3
"""
Generate and cache PR diffs locally from the droid-code-review-evals GitHub repos.

Usage:
    python3 scripts/generate_diffs.py              # generate all diffs
    python3 scripts/generate_diffs.py --repo sentry # generate diffs for one repo only

Diffs are saved to diffs/{repo}/pr{number}.diff and only fetched once (cached).
Use --force to re-fetch all diffs.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
DIFFS_DIR = BASE_DIR / "diffs"
ORG = "droid-code-review-evals"

GOLDEN_DIR = BASE_DIR / "target-repos" / "droid-golden_comments" / "v3" / "detailed"

REPO_CONFIGS = {
    "sentry": {"prefix": "droid", "pr_range": range(6, 16)},
    "grafana": {"prefix": "droid", "pr_range": range(1, 11)},
    "keycloak": {"prefix": "droid", "pr_range": range(1, 11)},
    "discourse": {"prefix": "droid", "pr_range": range(1, 11)},
    "cal_dot_com": {"prefix": "droid", "pr_range": range(1, 11)},
}


def fetch_diff(org: str, repo: str, pr_number: int) -> str:
    result = subprocess.run(
        ["gh", "api", f"repos/{org}/{repo}/pulls/{pr_number}",
         "-H", "Accept: application/vnd.github.v3.diff"],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        print(f"  ERROR fetching {repo} PR #{pr_number}: {result.stderr.strip()}")
        return ""
    return result.stdout


def fetch_pr_title(org: str, repo: str, pr_number: int) -> str:
    result = subprocess.run(
        ["gh", "pr", "view", str(pr_number), "-R", f"{org}/{repo}",
         "--json", "title", "--jq", ".title"],
        capture_output=True, text=True
    )
    return result.stdout.strip()


def generate_diffs(repo_filter: str | None = None, force: bool = False):
    for golden_name, config in REPO_CONFIGS.items():
        if repo_filter and golden_name != repo_filter:
            continue

        repo_name = f"{config['prefix']}-{golden_name}"
        repo_diff_dir = DIFFS_DIR / golden_name
        repo_diff_dir.mkdir(parents=True, exist_ok=True)

        meta_file = repo_diff_dir / "meta.json"
        meta = {}
        if meta_file.exists() and not force:
            with open(meta_file) as f:
                meta = json.load(f)

        print(f"\n=== {golden_name} ({repo_name}) ===")

        for pr_num in config["pr_range"]:
            diff_file = repo_diff_dir / f"pr{pr_num}.diff"

            if diff_file.exists() and not force:
                print(f"  PR #{pr_num}: cached ({diff_file.stat().st_size} bytes)")
                continue

            title = fetch_pr_title(ORG, repo_name, pr_num)
            diff = fetch_diff(ORG, repo_name, pr_num)

            if diff:
                with open(diff_file, "w") as f:
                    f.write(diff)
                meta[str(pr_num)] = {"title": title, "diff_lines": diff.count("\n")}
                print(f"  PR #{pr_num}: fetched ({diff.count(chr(10))} lines) - {title}")
            else:
                print(f"  PR #{pr_num}: FAILED - {title}")

        with open(meta_file, "w") as f:
            json.dump(meta, f, indent=2)

    print("\nDone. Diffs cached in", DIFFS_DIR)


def main():
    repo_filter = None
    force = False

    for arg in sys.argv[1:]:
        if arg == "--force":
            force = True
        elif arg == "--repo":
            pass
        elif sys.argv[sys.argv.index(arg) - 1] == "--repo":
            repo_filter = arg

    generate_diffs(repo_filter=repo_filter, force=force)


if __name__ == "__main__":
    main()
