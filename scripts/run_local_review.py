#!/usr/bin/env python3
"""
Run code reviews locally using the same prompts as the droid-action review pipeline,
but without GitHub posting. Outputs structured JSON findings.

Usage:
    python3 scripts/run_local_review.py <run_name> [options]

Options:
    --repo <name>       Only review one repo (sentry, grafana, etc.)
    --pr <number>       Only review one PR (requires --repo)
    --parallel <N>      Max concurrent reviews (default: 5)
    --model <model>     Anthropic model to use (default: claude-sonnet-4-20250514)
    --no-validator      Skip the validator pass (single-pass mode)

Reads diffs from diffs/{repo}/pr{number}.diff (run generate_diffs.py first).
Writes findings to results/{run_name}/local_findings/{repo}_pr{number}.json.
"""

from __future__ import annotations

import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
from anthropic import Anthropic

BASE_DIR = Path(__file__).parent.parent
load_dotenv(BASE_DIR / ".env")
client = Anthropic()

DIFFS_DIR = BASE_DIR / "diffs"

REPO_CONFIGS = {
    "sentry": {"pr_range": range(6, 16), "full_repo": "droid-code-review-evals/droid-sentry"},
    "grafana": {"pr_range": range(1, 11), "full_repo": "droid-code-review-evals/droid-grafana"},
    "keycloak": {"pr_range": range(1, 11), "full_repo": "droid-code-review-evals/droid-keycloak"},
    "discourse": {"pr_range": range(1, 11), "full_repo": "droid-code-review-evals/droid-discourse"},
    "cal_dot_com": {"pr_range": range(1, 11), "full_repo": "droid-code-review-evals/droid-cal_dot_com"},
}


# ---------------------------------------------------------------------------
# Prompt templates -- ported verbatim from droid-action/src/create-prompt/templates/
# with file-read instructions replaced by inline content.
# ---------------------------------------------------------------------------

def generate_candidate_prompt(repo_full: str, pr_number: int, title: str, diff: str) -> str:
    """Port of review-candidates-prompt.ts, adapted for local execution.

    Changes from the original:
    - Diff, description, and existing-comments are inlined instead of file paths.
    - Parallel subagent / Task instructions removed (no Droid CLI locally).
    - GitHub posting instructions removed.
    """
    return f"""You are a senior staff software engineer and expert code reviewer.

Your task: Review PR #{pr_number} in {repo_full} and generate a JSON object with **high-confidence, actionable** review comments that pinpoint genuine issues.

<context>
Repo: {repo_full}
PR Number: {pr_number}
PR Title: {title}
</context>

<pr_description>
{title}
</pr_description>

<existing_comments>
[]
</existing_comments>

<pr_diff>
{diff}
</pr_diff>

<review_guidelines>
- Review ALL modified files in the diff.
- Focus on: functional correctness, syntax errors, logic bugs, broken dependencies/contracts/tests, security issues, and performance problems.
- High-signal bug patterns to actively check for (only comment when evidenced in the diff):
  - Null/undefined/Optional dereferences; missing-key errors on untrusted/external dict/JSON payloads
  - Resource leaks (unclosed files/streams/connections; missing cleanup on error paths)
  - Injection vulnerabilities (SQL injection, XSS, command/template injection) and auth/security invariant violations
  - OAuth/CSRF invariants: state must be per-flow unpredictable and validated; avoid deterministic/predictable state or missing state checks
  - Concurrency/race/atomicity hazards (TOCTOU, lost updates, unsafe shared state, process/thread lifecycle bugs)
  - Missing error handling for critical operations (network, persistence, auth, migrations, external APIs)
  - Wrong-variable/shadowing mistakes; contract mismatches (serializer/validated_data, interfaces/abstract methods)
  - Type-assumption bugs (e.g., numeric ops on datetime/strings, ordering key type mismatches)
  - Offset/cursor/pagination semantic mismatches (off-by-one, prev/next behavior, commit semantics)
- Only flag issues you are confident about—avoid speculative or stylistic nitpicks.
</review_guidelines>

<triage_phase>
**Step 1: Analyze the diff**

Read the entire diff above. Group modified files into logical clusters by functionality, risk, and dependencies. Document your grouping briefly.
</triage_phase>

<review_phase>
**Step 2: Review each group**

For each group of files, review the diff carefully. Look for the bug patterns listed in the guidelines. For each finding:
- Identify the exact file path and line number
- Describe the bug clearly and concisely
- Assess severity (P0=blocking/crash/exploit, P1=urgent correctness/security, P2=real bug limited impact, P3=minor but real)
</review_phase>

<output_spec>
**Step 3: Output findings**

Respond with ONLY a JSON object in this exact format:

```json
{{
  "version": 1,
  "meta": {{
    "repo": "{repo_full}",
    "prNumber": {pr_number},
    "generatedAt": "<ISO timestamp>"
  }},
  "comments": [
    {{
      "path": "src/index.ts",
      "body": "[P1] Title\\n\\n1 paragraph explanation.",
      "line": 42,
      "side": "RIGHT"
    }}
  ],
  "reviewSummary": {{
    "body": "1-3 sentence overall assessment"
  }}
}}
```

If no issues are found, return the same structure with an empty comments array.
</output_spec>

<critical_constraints>
Output ONLY the JSON—no additional commentary.
</critical_constraints>
"""


def generate_validator_prompt(repo_full: str, pr_number: int, title: str,
                               diff: str, candidates_json: str) -> str:
    """Port of review-validator-prompt.ts, adapted for local execution.

    Changes from the original:
    - Diff and candidates are inlined instead of file paths.
    - GitHub posting instructions removed.
    - Output goes to stdout as JSON instead of file + API calls.
    """
    return f"""You are validating candidate review comments for PR #{pr_number} in {repo_full}.

IMPORTANT: This is Phase 2 (validator) of a two-pass review pipeline.

### Context

* Repo: {repo_full}
* PR Number: {pr_number}
* PR Title: {title}

### Inputs

<pr_diff>
{diff}
</pr_diff>

<existing_comments>
[]
</existing_comments>

<candidates>
{candidates_json}
</candidates>

=======================

## CRITICAL REQUIREMENTS

1. You MUST validate **every** candidate.
2. For each candidate, confirm:
   * It is a real, actionable bug (not speculative)
   * There is a realistic trigger path and observable wrong behavior
   * The file path and line reference valid locations in the diff
3. Preserve ordering: keep results in the same order as candidates.

=======================

## Validation criteria

### Approve ONLY if at least one is true
* Definite runtime failure
* Incorrect logic with a concrete trigger path and wrong outcome
* Security vulnerability with realistic exploit
* Data corruption/loss
* Breaking contract change (discoverable in code/tests)

### Reject if
* It's speculative / "might" without a concrete trigger
* It's stylistic / naming / formatting
* It's not anchored to a valid changed line
* It's already reported (dedupe against existing comments)

### Deduplication (STRICT)

If two or more candidates describe the same underlying bug (same root cause, even if anchored to different lines or worded differently), approve only the ONE with the best anchor and clearest explanation. Reject the rest with reason "duplicate of candidate N".

=======================

## Output

Respond with ONLY a JSON object:

```json
{{
  "version": 1,
  "meta": {{
    "repo": "{repo_full}",
    "prNumber": {pr_number},
    "validatedAt": "<ISO timestamp>"
  }},
  "results": [
    {{
      "status": "approved",
      "comment": {{
        "path": "src/index.ts",
        "body": "[P1] Title\\n\\n1 paragraph.",
        "line": 42,
        "side": "RIGHT"
      }}
    }},
    {{
      "status": "rejected",
      "candidate": {{
        "path": "src/other.ts",
        "body": "[P2] ...",
        "line": 10,
        "side": "RIGHT"
      }},
      "reason": "Not a real bug because ..."
    }}
  ],
  "reviewSummary": {{
    "status": "approved",
    "body": "1-3 sentence overall assessment"
  }}
}}
```

`results` MUST have exactly one entry per candidate, in the same order.
Output ONLY the JSON—no additional commentary.
"""


# ---------------------------------------------------------------------------
# Execution logic
# ---------------------------------------------------------------------------

def get_pr_title(repo: str, pr_number: int) -> str:
    meta_file = DIFFS_DIR / repo / "meta.json"
    if meta_file.exists():
        with open(meta_file) as f:
            meta = json.load(f)
        info = meta.get(str(pr_number), {})
        return info.get("title", f"PR #{pr_number}")
    return f"PR #{pr_number}"


def parse_json_response(text: str) -> dict:
    text = text.strip()
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
        text = text.strip()
    return json.loads(text)


def run_candidate_pass(repo_full: str, pr_number: int, title: str,
                        diff: str, model: str) -> dict | None:
    prompt = generate_candidate_prompt(repo_full, pr_number, title, diff)

    max_retries = 2
    for attempt in range(max_retries + 1):
        try:
            response = client.messages.create(
                model=model,
                max_tokens=8192,
                messages=[{"role": "user", "content": prompt}],
            )
            text = response.content[0].text.strip()
            return parse_json_response(text)
        except json.JSONDecodeError:
            if attempt < max_retries:
                continue
            return None
        except Exception as e:
            if attempt < max_retries:
                time.sleep(2 ** attempt)
                continue
            raise


def run_validator_pass(repo_full: str, pr_number: int, title: str,
                        diff: str, candidates_json: str, model: str) -> dict | None:
    prompt = generate_validator_prompt(repo_full, pr_number, title, diff, candidates_json)

    max_retries = 2
    for attempt in range(max_retries + 1):
        try:
            response = client.messages.create(
                model=model,
                max_tokens=8192,
                messages=[{"role": "user", "content": prompt}],
            )
            text = response.content[0].text.strip()
            return parse_json_response(text)
        except json.JSONDecodeError:
            if attempt < max_retries:
                continue
            return None
        except Exception as e:
            if attempt < max_retries:
                time.sleep(2 ** attempt)
                continue
            raise


def extract_findings_from_candidates(candidates: dict) -> list[dict]:
    """Extract findings from candidate generation output."""
    findings = []
    for c in candidates.get("comments", []):
        body = c.get("body", "")
        severity = "P2"
        for s in ["P0", "P1", "P2", "P3"]:
            if f"[{s}]" in body:
                severity = s
                break
        findings.append({
            "file": c.get("path", "unknown"),
            "line": c.get("line"),
            "severity": severity,
            "comment": body,
        })
    return findings


def extract_findings_from_validated(validated: dict) -> list[dict]:
    """Extract only approved findings from validator output."""
    findings = []
    for r in validated.get("results", []):
        if r.get("status") != "approved":
            continue
        c = r.get("comment", {})
        body = c.get("body", "")
        severity = "P2"
        for s in ["P0", "P1", "P2", "P3"]:
            if f"[{s}]" in body:
                severity = s
                break
        findings.append({
            "file": c.get("path", "unknown"),
            "line": c.get("line"),
            "severity": severity,
            "comment": body,
        })
    return findings


def review_pr(repo: str, pr_number: int, model: str, use_validator: bool) -> dict | None:
    config = REPO_CONFIGS[repo]
    repo_full = config["full_repo"]
    diff_file = DIFFS_DIR / repo / f"pr{pr_number}.diff"

    if not diff_file.exists():
        print(f"  SKIP {repo} PR #{pr_number}: no diff file")
        return None

    diff = diff_file.read_text()
    if not diff.strip():
        print(f"  SKIP {repo} PR #{pr_number}: empty diff")
        return None

    title = get_pr_title(repo, pr_number)

    try:
        # Pass 1: Candidate generation
        candidates = run_candidate_pass(repo_full, pr_number, title, diff, model)
        if candidates is None:
            print(f"  ERROR {repo} PR #{pr_number}: candidate pass failed to parse")
            return {
                "repo": repo, "pr_number": pr_number, "pr_title": title,
                "model": model, "findings": [],
                "summary": "ERROR: candidate pass failed",
            }

        if not use_validator:
            findings = extract_findings_from_candidates(candidates)
            return {
                "repo": repo, "pr_number": pr_number, "pr_title": title,
                "model": model,
                "findings": findings,
                "summary": candidates.get("reviewSummary", {}).get("body", ""),
                "raw_candidates": candidates,
            }

        # Pass 2: Validator
        candidates_json = json.dumps(candidates, indent=2)
        validated = run_validator_pass(repo_full, pr_number, title, diff, candidates_json, model)
        if validated is None:
            # Fall back to unvalidated candidates
            print(f"  WARN {repo} PR #{pr_number}: validator pass failed, using raw candidates")
            findings = extract_findings_from_candidates(candidates)
            return {
                "repo": repo, "pr_number": pr_number, "pr_title": title,
                "model": model,
                "findings": findings,
                "summary": candidates.get("reviewSummary", {}).get("body", ""),
                "raw_candidates": candidates,
                "validator_error": True,
            }

        findings = extract_findings_from_validated(validated)
        return {
            "repo": repo, "pr_number": pr_number, "pr_title": title,
            "model": model,
            "findings": findings,
            "summary": validated.get("reviewSummary", {}).get("body", ""),
            "raw_candidates": candidates,
            "raw_validated": validated,
        }

    except Exception as e:
        print(f"  ERROR {repo} PR #{pr_number}: {e}")
        return {
            "repo": repo, "pr_number": pr_number, "pr_title": title,
            "model": model, "findings": [],
            "summary": f"ERROR: {str(e)}",
        }


def run_reviews(run_name: str, repo_filter: str | None, pr_filter: int | None,
                parallel: int, model: str, use_validator: bool):
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

    mode = "two-pass (candidates + validator)" if use_validator else "single-pass (candidates only)"
    print(f"Running {len(tasks)} reviews with model={model}, parallel={parallel}, mode={mode}")
    print(f"Output: {findings_dir}\n")

    completed = 0
    total = len(tasks)

    def _run(repo_pr):
        repo, pr_num = repo_pr
        result = review_pr(repo, pr_num, model, use_validator)
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
    use_validator = True

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
        elif args[i] == "--no-validator":
            use_validator = False
            i += 1
        else:
            i += 1

    run_reviews(run_name, repo_filter, pr_filter, parallel, model, use_validator)


if __name__ == "__main__":
    main()
