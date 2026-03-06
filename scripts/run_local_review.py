#!/usr/bin/env python3
"""
Run code reviews locally using an LLM, without GitHub.

Usage:
    python3 scripts/run_local_review.py <run_name> [options]

Options:
    --repo <name>       Only review one repo (sentry, grafana, etc.)
    --pr <number>       Only review one PR (requires --repo)
    --parallel <N>      Max concurrent reviews (default: 5)
    --model <model>     Anthropic model to use (default: claude-sonnet-4-20250514)
    --tool <name>       Tool name for output labeling (default: local_review)

Reads diffs from diffs/{repo}/pr{number}.diff (run generate_diffs.py first).
Writes findings to results/{run_name}/local_findings/{repo}_pr{number}.json.
"""

from __future__ import annotations

import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from dotenv import load_dotenv
from anthropic import Anthropic

BASE_DIR = Path(__file__).parent.parent
load_dotenv(BASE_DIR / ".env")
client = Anthropic()

DIFFS_DIR = BASE_DIR / "diffs"

GOLDEN_DIR = BASE_DIR / "target-repos" / "droid-golden_comments" / "v3" / "detailed"

REPO_CONFIGS = {
    "sentry": {"pr_range": range(6, 16)},
    "grafana": {"pr_range": range(1, 11)},
    "keycloak": {"pr_range": range(1, 11)},
    "discourse": {"pr_range": range(1, 11)},
    "cal_dot_com": {"pr_range": range(1, 11)},
}

REVIEW_SYSTEM_PROMPT = """You are a senior staff software engineer performing an automated code review.

Your task: Review the provided PR diff and identify **high-confidence, actionable bugs**.

## What to look for

- **Definite runtime failures** (TypeError, KeyError, AttributeError, ImportError, NullPointerException)
- **Incorrect logic** with a clear trigger path and observable wrong result
- **Security vulnerabilities** with a realistic exploit path
- **Data corruption or loss**
- **Concurrency/race conditions** with identifiable shared state
- **Breaking contract changes** (API / response / schema changes)

## What NOT to report

- Test code hygiene unless it causes test failure
- Defensive "what-if" scenarios without a realistic trigger
- Cosmetic issues (naming, formatting, style)
- Suggestions to "add guards" or "be safer" without a concrete failure path

## Bug patterns to check

- Null/undefined/Optional dereferences without guards
- Missing-key errors on untrusted dict/JSON payloads
- Resource leaks (unclosed files/streams/connections)
- Injection vulnerabilities (SQL, XSS, command injection)
- OAuth/CSRF: state must be per-flow unpredictable and validated
- Concurrency hazards (TOCTOU, lost updates, unsafe shared state)
- Wrong-variable/shadowing mistakes
- Type-assumption bugs (numeric ops on datetime/strings)
- Offset/cursor/pagination semantic mismatches
- async forEach/map with unawaited callbacks (JS/TS)

## Output format

Respond with ONLY a JSON object in this exact format:

```json
{
  "findings": [
    {
      "file": "path/to/file.ext",
      "line": 42,
      "severity": "P0|P1|P2|P3",
      "comment": "Clear description of the bug and how it manifests"
    }
  ],
  "summary": "1-3 sentence overall assessment"
}
```

If no issues are found, return: `{"findings": [], "summary": "No significant issues found."}`

## Severity levels

- **P0**: Blocking / crash / exploit
- **P1**: Urgent correctness or security issue
- **P2**: Real bug with limited impact
- **P3**: Minor but real bug"""


def get_pr_title(repo: str, pr_number: int) -> str:
    meta_file = DIFFS_DIR / repo / "meta.json"
    if meta_file.exists():
        with open(meta_file) as f:
            meta = json.load(f)
        info = meta.get(str(pr_number), {})
        return info.get("title", f"PR #{pr_number}")
    return f"PR #{pr_number}"


def review_pr(repo: str, pr_number: int, model: str) -> dict | None:
    diff_file = DIFFS_DIR / repo / f"pr{pr_number}.diff"
    if not diff_file.exists():
        print(f"  SKIP {repo} PR #{pr_number}: no diff file")
        return None

    diff = diff_file.read_text()
    if not diff.strip():
        print(f"  SKIP {repo} PR #{pr_number}: empty diff")
        return None

    title = get_pr_title(repo, pr_number)

    user_prompt = f"""## PR Information

- Repository: {repo}
- PR #{pr_number}: {title}

## Diff

```diff
{diff}
```

Review this diff and identify all high-confidence bugs. Respond with ONLY the JSON output."""

    max_retries = 2
    for attempt in range(max_retries + 1):
        try:
            response = client.messages.create(
                model=model,
                max_tokens=4096,
                system=REVIEW_SYSTEM_PROMPT,
                messages=[{"role": "user", "content": user_prompt}],
            )
            text = response.content[0].text.strip()

            if text.startswith("```"):
                text = text.split("```")[1]
                if text.startswith("json"):
                    text = text[4:]
                text = text.strip()

            parsed = json.loads(text)
            return {
                "repo": repo,
                "pr_number": pr_number,
                "pr_title": title,
                "model": model,
                "findings": parsed.get("findings", []),
                "summary": parsed.get("summary", ""),
            }
        except json.JSONDecodeError:
            if attempt < max_retries:
                continue
            print(f"  ERROR {repo} PR #{pr_number}: failed to parse JSON after {max_retries + 1} attempts")
            return {
                "repo": repo,
                "pr_number": pr_number,
                "pr_title": title,
                "model": model,
                "findings": [],
                "summary": f"ERROR: failed to parse model output",
                "raw_output": text[:2000] if 'text' in dir() else "",
            }
        except Exception as e:
            if attempt < max_retries:
                time.sleep(2 ** attempt)
                continue
            print(f"  ERROR {repo} PR #{pr_number}: {e}")
            return {
                "repo": repo,
                "pr_number": pr_number,
                "pr_title": title,
                "model": model,
                "findings": [],
                "summary": f"ERROR: {str(e)}",
            }


def run_reviews(run_name: str, repo_filter: str | None, pr_filter: int | None,
                parallel: int, model: str, tool_name: str):
    run_dir = BASE_DIR / "results" / run_name
    findings_dir = run_dir / "local_findings"
    findings_dir.mkdir(parents=True, exist_ok=True)

    tasks = []
    for repo, config in REPO_CONFIGS.items():
        if repo_filter and repo != repo_filter:
            continue
        for pr_num in config["pr_range"]:
            if pr_filter is not None and pr_num != pr_filter:
                continue
            tasks.append((repo, pr_num))

    print(f"Running {len(tasks)} reviews with model={model}, parallel={parallel}")
    print(f"Output: {findings_dir}\n")

    completed = 0
    total = len(tasks)

    def _run(repo_pr):
        repo, pr_num = repo_pr
        result = review_pr(repo, pr_num, model)
        if result:
            out_file = findings_dir / f"{repo}_pr{pr_num}.json"
            with open(out_file, "w") as f:
                json.dump(result, f, indent=2)
        return repo, pr_num, result

    with ThreadPoolExecutor(max_workers=parallel) as executor:
        futures = {executor.submit(_run, t): t for t in tasks}
        for future in as_completed(futures):
            repo, pr_num, result = future.result()
            completed += 1
            if result:
                n_findings = len(result.get("findings", []))
                print(f"  [{completed}/{total}] {repo} PR #{pr_num}: {n_findings} findings")
            else:
                print(f"  [{completed}/{total}] {repo} PR #{pr_num}: skipped")

    print(f"\nDone. {completed} reviews completed.")
    print(f"Results in {findings_dir}")


def main():
    args = sys.argv[1:]
    if not args:
        print("Usage: python3 scripts/run_local_review.py <run_name> [options]")
        sys.exit(1)

    run_name = args[0]
    repo_filter = None
    pr_filter = None
    parallel = 5
    model = "claude-sonnet-4-20250514"
    tool_name = "local_review"

    i = 1
    while i < len(args):
        if args[i] == "--repo" and i + 1 < len(args):
            repo_filter = args[i + 1]
            i += 2
        elif args[i] == "--pr" and i + 1 < len(args):
            pr_filter = int(args[i + 1])
            i += 2
        elif args[i] == "--parallel" and i + 1 < len(args):
            parallel = int(args[i + 1])
            i += 2
        elif args[i] == "--model" and i + 1 < len(args):
            model = args[i + 1]
            i += 2
        elif args[i] == "--tool" and i + 1 < len(args):
            tool_name = args[i + 1]
            i += 2
        else:
            i += 1

    run_reviews(run_name, repo_filter, pr_filter, parallel, model, tool_name)


if __name__ == "__main__":
    main()
