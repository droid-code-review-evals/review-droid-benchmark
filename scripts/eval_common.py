#!/usr/bin/env python3
"""
Shared evaluation logic for comparing tool comments against golden comments.
Used by per-tool evaluation scripts.
"""

import json
import os
import subprocess
import sys
from pathlib import Path

from dotenv import load_dotenv
from anthropic import Anthropic

BASE_DIR = Path(__file__).parent.parent
load_dotenv(BASE_DIR / ".env")
client = Anthropic()

GOLDEN_DIR = BASE_DIR / "target-repos" / "droid-golden_comments" / "v3" / "detailed"

REPO_GOLDEN_NAMES = ["sentry", "grafana", "keycloak", "discourse", "cal_dot_com"]

SENTRY_PR_RANGE = range(6, 16)  # golden PR numbers for sentry
OTHER_PR_RANGE = range(1, 11)   # golden PR numbers for other repos

# Per-tool PR number offsets from golden PR numbers.
# E.g. augment-sentry benchmark PRs are 7-16 instead of 6-15 (offset +1).
TOOL_PR_OFFSETS = {
    "augment-sentry": 1,
}

# Golden PR numbers to skip per tool-repo (e.g. codex errored out on grafana PR 3).
TOOL_SKIP_PRS = {
    "codex-grafana": {3},
}


def gh_api(endpoint: str) -> str:
    result = subprocess.run(
        ["gh", "api", endpoint, "--paginate"],
        capture_output=True, text=True
    )
    return result.stdout


def _get_pr_range(repo_prefix: str, golden_name: str) -> tuple[list[int], list[int]]:
    """Return (actual_pr_numbers, golden_pr_numbers) for a given tool repo."""
    golden_range = list(SENTRY_PR_RANGE if golden_name == "sentry" else OTHER_PR_RANGE)
    skip = TOOL_SKIP_PRS.get(f"{repo_prefix}-{golden_name}", set())
    golden_range = [n for n in golden_range if n not in skip]
    offset = TOOL_PR_OFFSETS.get(f"{repo_prefix}-{golden_name}", 0)
    actual_range = [n + offset for n in golden_range]
    return actual_range, golden_range


def fetch_inline_comments(org: str, repo_prefix: str, bot_login: str, run_dir: Path):
    """Fetch inline PR review comments for tools that post them (bugbot, augment, codex)."""
    raw_dir = run_dir / "raw_comments"
    raw_dir.mkdir(parents=True, exist_ok=True)

    for golden_name in REPO_GOLDEN_NAMES:
        repo_name = f"{repo_prefix}-{golden_name}"
        full_repo = f"{org}/{repo_name}"
        actual_prs, golden_prs = _get_pr_range(repo_prefix, golden_name)

        print(f"Fetching {full_repo}...")
        prs = []
        for actual_num, golden_num in zip(actual_prs, golden_prs):
            pr_title_raw = subprocess.run(
                ["gh", "pr", "view", str(actual_num), "-R", full_repo, "--json", "title", "--jq", ".title"],
                capture_output=True, text=True
            )
            pr_title = pr_title_raw.stdout.strip()

            review_comments_raw = gh_api(f"repos/{full_repo}/pulls/{actual_num}/comments")
            try:
                all_comments = json.loads(review_comments_raw) if review_comments_raw.strip() else []
            except json.JSONDecodeError:
                all_comments = []

            bot_comments = [
                {
                    "id": c["id"],
                    "body": c["body"],
                    "path": c.get("path", ""),
                    "line": c.get("line"),
                    "side": c.get("side", ""),
                    "created_at": c.get("created_at", ""),
                    "html_url": c.get("html_url", ""),
                }
                for c in all_comments
                if c.get("user", {}).get("login") == bot_login
            ]

            # Store using golden_num so evaluation can match against golden comments
            prs.append({
                "number": golden_num,
                "actual_pr_number": actual_num,
                "title": pr_title,
                "review_comments": bot_comments,
                "issue_comments": [],
                "reviews": [],
            })
            print(f"  PR #{actual_num} (golden #{golden_num}): {len(bot_comments)} comments")

        output = {
            "repo": repo_name,
            "fetched_by": bot_login,
            "prs": prs,
        }
        out_file = raw_dir / f"{repo_prefix}-{golden_name}.json"
        with open(out_file, "w") as f:
            json.dump(output, f, indent=2)


def fetch_issue_comments(org: str, repo_prefix: str, bot_login: str, run_dir: Path):
    """Fetch issue comments for tools that post a single comment body (claude_code)."""
    raw_dir = run_dir / "raw_comments"
    raw_dir.mkdir(parents=True, exist_ok=True)

    for golden_name in REPO_GOLDEN_NAMES:
        repo_name = f"{repo_prefix}-{golden_name}"
        full_repo = f"{org}/{repo_name}"
        actual_prs, golden_prs = _get_pr_range(repo_prefix, golden_name)

        print(f"Fetching {full_repo}...")
        prs = []
        for actual_num, golden_num in zip(actual_prs, golden_prs):
            pr_title_raw = subprocess.run(
                ["gh", "pr", "view", str(actual_num), "-R", full_repo, "--json", "title", "--jq", ".title"],
                capture_output=True, text=True
            )
            pr_title = pr_title_raw.stdout.strip()

            issue_comments_raw = gh_api(f"repos/{full_repo}/issues/{actual_num}/comments")
            try:
                all_comments = json.loads(issue_comments_raw) if issue_comments_raw.strip() else []
            except json.JSONDecodeError:
                all_comments = []

            bot_comments = [
                {
                    "id": c["id"],
                    "body": c["body"],
                    "created_at": c.get("created_at", ""),
                    "html_url": c.get("html_url", ""),
                }
                for c in all_comments
                if c.get("user", {}).get("login") == bot_login
            ]

            prs.append({
                "number": golden_num,
                "actual_pr_number": actual_num,
                "title": pr_title,
                "issue_comments": bot_comments,
                "review_comments": [],
                "reviews": [],
            })
            print(f"  PR #{actual_num} (golden #{golden_num}): {len(bot_comments)} issue comments")

        output = {
            "repo": repo_name,
            "fetched_by": bot_login,
            "prs": prs,
        }
        out_file = raw_dir / f"{repo_prefix}-{golden_name}.json"
        with open(out_file, "w") as f:
            json.dump(output, f, indent=2)


def evaluate_match(comment_text: str, golden_comments: list[dict], max_retries: int = 2) -> dict:
    golden_list = "\n".join([
        f"[{i}] [{g['severity']}] {g['comment']}"
        for i, g in enumerate(golden_comments)
    ])

    prompt = f"""You are evaluating whether a code review comment from an AI reviewer matches any of the expected findings (golden comments) for a PR.

GOLDEN COMMENTS (expected findings, numbered 0 to {len(golden_comments) - 1}):
{golden_list}

REVIEWER'S COMMENT:
{comment_text}

Does the reviewer's comment match ANY of the golden comments? Two comments "match" if they describe the same bug/issue, even if worded differently.

Respond in this exact JSON format:
{{
  "matches": true or false,
  "matched_index": the index number (0, 1, 2, ...) of the matched golden comment, or null if no match,
  "confidence": "high", "medium", or "low",
  "reasoning": "brief explanation of why this is or isn't a match"
}}

Only output the JSON, nothing else."""

    original_prompt = prompt
    for attempt in range(max_retries + 1):
        response = client.messages.create(
            model="claude-opus-4-6",
            max_tokens=500,
            messages=[{"role": "user", "content": prompt}]
        )
        text = response.content[0].text.strip()
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
            text = text.strip()
        try:
            parsed = json.loads(text)
            if isinstance(parsed, list) and len(parsed) == 1 and isinstance(parsed[0], dict):
                parsed = parsed[0]
            if isinstance(parsed, dict):
                return parsed
            raise json.JSONDecodeError("Expected JSON object", text, 0)
        except json.JSONDecodeError:
            if attempt < max_retries:
                prompt = f"Your previous response was not valid JSON. Please respond with ONLY valid JSON, no markdown or extra text.\n\n{original_prompt}"
            else:
                return {
                    "matches": False, "matched_index": None,
                    "confidence": "low",
                    "reasoning": f"Failed to parse after {max_retries + 1} attempts: {text[:200]}"
                }


def split_issue_comment_into_findings(body: str) -> list[str]:
    """Split a single large issue comment (e.g. Claude Code) into individual findings.

    Splits on markdown headings that look like numbered findings (### 1., ### 2., etc.)
    """
    import re
    # Split on ### N. or ## N. patterns (numbered findings)
    parts = re.split(r'(?=^###?\s+\d+\.)', body, flags=re.MULTILINE)
    findings = [p.strip() for p in parts if p.strip()]
    # Filter out preamble sections that don't contain actual findings
    result = []
    for f in findings:
        if re.match(r'^###?\s+\d+\.', f):
            result.append(f)
    return result if result else [body]


def evaluate_pr(pr_data: dict, golden_comments: list[dict], use_issue_comments: bool = False) -> dict:
    results = {
        "pr_number": pr_data["number"],
        "pr_title": pr_data["title"],
        "golden_count": len(golden_comments),
        "evaluations": [],
        "true_positives": [],
        "false_positives": [],
        "false_negatives": [],
        "duplicates": [],
    }

    comments_to_eval = []

    if use_issue_comments:
        for ic in pr_data.get("issue_comments", []):
            findings = split_issue_comment_into_findings(ic["body"])
            for finding in findings:
                comments_to_eval.append({"body": finding, "path": "issue_comment", "line": None})
    else:
        for c in pr_data.get("review_comments", []):
            comments_to_eval.append(c)

    results["droid_count"] = len(comments_to_eval)
    matched_golden_indices = set()

    for comment in comments_to_eval:
        eval_result = evaluate_match(comment["body"], golden_comments)
        eval_result["comment_text"] = comment["body"][:500]
        eval_result["file"] = comment.get("path", "unknown")
        eval_result["line"] = comment.get("line", "unknown")
        results["evaluations"].append(eval_result)

        if eval_result["matches"]:
            matched_idx = eval_result.get("matched_index")
            if matched_idx is not None and isinstance(matched_idx, int) and 0 <= matched_idx < len(golden_comments):
                eval_result["matched_golden_comment"] = golden_comments[matched_idx]["comment"]
                eval_result["matched_severity"] = golden_comments[matched_idx]["severity"]
                if matched_idx in matched_golden_indices:
                    results["duplicates"].append(eval_result)
                else:
                    results["true_positives"].append(eval_result)
                    matched_golden_indices.add(matched_idx)
            else:
                eval_result["warning"] = f"Match claimed but invalid index: {matched_idx}"
                results["false_positives"].append(eval_result)
        else:
            results["false_positives"].append(eval_result)

    for idx, golden in enumerate(golden_comments):
        if idx not in matched_golden_indices:
            results["false_negatives"].append({
                "golden_comment": golden["comment"],
                "severity": golden["severity"],
            })

    tp = len(matched_golden_indices)
    fp = len(results["false_positives"])
    fn = len(results["false_negatives"])
    precision = (tp / (tp + fp)) if (tp + fp) > 0 else 0.0
    recall = (tp / (tp + fn)) if (tp + fn) > 0 else 0.0
    f_score = (2 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0.0

    results["metrics"] = {
        "tp": tp, "fp": fp, "fn": fn,
        "duplicates": len(results["duplicates"]),
        "precision": round(precision * 100, 1),
        "recall": round(recall * 100, 1),
        "f_score": round(f_score * 100, 1),
    }
    return results


def run_local_evaluation(tool_name: str, run_name: str):
    """Run evaluation for local findings (from run_local_review.py) against golden comments."""
    run_dir = BASE_DIR / "results" / run_name
    findings_dir = run_dir / "local_findings"

    if not findings_dir.exists():
        print(f"ERROR: {findings_dir} not found. Run run_local_review.py first.")
        return

    all_results = {
        "run_name": run_name,
        "tool": tool_name,
        "mode": "local",
        "repos": [],
        "overall_summary": {"total_tp": 0, "total_fp": 0, "total_fn": 0},
    }

    for golden_name in REPO_GOLDEN_NAMES:
        golden_file = GOLDEN_DIR / f"{golden_name}.json"
        if not golden_file.exists():
            print(f"WARNING: {golden_file} not found, skipping")
            continue

        with open(golden_file) as f:
            golden_data = json.load(f)

        golden_by_number = {}
        for g in golden_data:
            golden_by_number[g["pr_number"]] = [
                {"comment": bug["description"], "severity": bug.get("severity", "medium").title()}
                for bug in g["bugs"]
            ]

        repo_results = {
            "repo": golden_name,
            "prs": [],
            "summary": {"total_tp": 0, "total_fp": 0, "total_fn": 0},
        }

        print(f"\nEvaluating {golden_name}...")

        for pr_number, golden_comments in sorted(golden_by_number.items()):
            findings_file = findings_dir / f"{golden_name}_pr{pr_number}.json"
            if not findings_file.exists():
                print(f"  PR #{pr_number}: no local findings file, skipping")
                continue

            with open(findings_file) as f:
                local_data = json.load(f)

            findings = local_data.get("findings", [])
            pr_data = {
                "number": pr_number,
                "title": local_data.get("pr_title", f"PR #{pr_number}"),
                "review_comments": [
                    {
                        "body": finding["comment"],
                        "path": finding.get("file", "unknown"),
                        "line": finding.get("line"),
                    }
                    for finding in findings
                ],
            }

            print(f"  PR #{pr_number}: {len(golden_comments)} golden, {len(findings)} findings")
            result = evaluate_pr(pr_data, golden_comments)
            repo_results["prs"].append(result)

            repo_results["summary"]["total_tp"] += len(result["true_positives"])
            repo_results["summary"]["total_fp"] += len(result["false_positives"])
            repo_results["summary"]["total_fn"] += len(result["false_negatives"])

        tp = repo_results["summary"]["total_tp"]
        fp = repo_results["summary"]["total_fp"]
        fn = repo_results["summary"]["total_fn"]
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0
        f_score = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0
        repo_results["summary"]["precision"] = round(precision * 100, 1)
        repo_results["summary"]["recall"] = round(recall * 100, 1)
        repo_results["summary"]["f_score"] = round(f_score * 100, 1)

        all_results["repos"].append(repo_results)
        all_results["overall_summary"]["total_tp"] += repo_results["summary"]["total_tp"]
        all_results["overall_summary"]["total_fp"] += repo_results["summary"]["total_fp"]
        all_results["overall_summary"]["total_fn"] += repo_results["summary"]["total_fn"]

    tp = all_results["overall_summary"]["total_tp"]
    fp = all_results["overall_summary"]["total_fp"]
    fn = all_results["overall_summary"]["total_fn"]
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0
    f_score = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0
    all_results["overall_summary"]["precision"] = round(precision * 100, 1)
    all_results["overall_summary"]["recall"] = round(recall * 100, 1)
    all_results["overall_summary"]["f_score"] = round(f_score * 100, 1)

    out_file = run_dir / f"{tool_name}_local_eval.json"
    with open(out_file, "w") as f:
        json.dump(all_results, f, indent=2)

    print(f"\n{'='*70}")
    print(f"{tool_name.upper()} LOCAL EVAL RESULTS")
    print(f"{'='*70}")
    for repo_result in all_results["repos"]:
        s = repo_result["summary"]
        print(f"{repo_result['repo']:30} | TP={s['total_tp']:2} FP={s['total_fp']:2} FN={s['total_fn']:2} | P={s['precision']:5.1f}% R={s['recall']:5.1f}% F={s['f_score']:5.1f}%")
    print(f"{'='*70}")
    print(f"{'OVERALL':30} | TP={tp:2} FP={fp:2} FN={fn:2} | P={all_results['overall_summary']['precision']:5.1f}% R={all_results['overall_summary']['recall']:5.1f}% F={all_results['overall_summary']['f_score']:5.1f}%")
    print(f"\nResults saved to {out_file}")


def run_evaluation(tool_name: str, repo_prefix: str, run_name: str, use_issue_comments: bool = False):
    """Run evaluation for a tool against golden comments."""
    run_dir = BASE_DIR / "results" / run_name
    raw_dir = run_dir / "raw_comments"

    all_results = {
        "run_name": run_name,
        "tool": tool_name,
        "repos": [],
        "overall_summary": {"total_tp": 0, "total_fp": 0, "total_fn": 0},
    }

    for golden_name in REPO_GOLDEN_NAMES:
        repo_key = f"{repo_prefix}-{golden_name}"
        raw_file = raw_dir / f"{repo_key}.json"

        if not raw_file.exists():
            print(f"WARNING: {raw_file} not found, skipping")
            continue

        with open(raw_file) as f:
            tool_data = json.load(f)

        golden_file = GOLDEN_DIR / f"{golden_name}.json"
        with open(golden_file) as f:
            golden_data = json.load(f)

        golden_by_number = {}
        for g in golden_data:
            golden_by_number[g["pr_number"]] = [
                {"comment": bug["description"], "severity": bug.get("severity", "medium").title()}
                for bug in g["bugs"]
            ]

        repo_results = {
            "repo": repo_key,
            "prs": [],
            "summary": {"total_tp": 0, "total_fp": 0, "total_fn": 0},
        }

        print(f"\nEvaluating {repo_key}...")

        for pr in tool_data["prs"]:
            golden_comments = golden_by_number.get(pr["number"], [])
            if use_issue_comments:
                comment_count = len(pr.get("issue_comments", []))
            else:
                comment_count = len(pr.get("review_comments", []))

            if not golden_comments and comment_count == 0:
                print(f"  PR #{pr['number']}: 0 golden, 0 comments — skipping")
                continue

            print(f"  PR #{pr['number']}: {len(golden_comments)} golden, {comment_count} comments")
            result = evaluate_pr(pr, golden_comments, use_issue_comments=use_issue_comments)
            repo_results["prs"].append(result)

            repo_results["summary"]["total_tp"] += len(result["true_positives"])
            repo_results["summary"]["total_fp"] += len(result["false_positives"])
            repo_results["summary"]["total_fn"] += len(result["false_negatives"])

        tp = repo_results["summary"]["total_tp"]
        fp = repo_results["summary"]["total_fp"]
        fn = repo_results["summary"]["total_fn"]
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0
        f_score = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0
        repo_results["summary"]["precision"] = round(precision * 100, 1)
        repo_results["summary"]["recall"] = round(recall * 100, 1)
        repo_results["summary"]["f_score"] = round(f_score * 100, 1)

        all_results["repos"].append(repo_results)
        all_results["overall_summary"]["total_tp"] += repo_results["summary"]["total_tp"]
        all_results["overall_summary"]["total_fp"] += repo_results["summary"]["total_fp"]
        all_results["overall_summary"]["total_fn"] += repo_results["summary"]["total_fn"]

    tp = all_results["overall_summary"]["total_tp"]
    fp = all_results["overall_summary"]["total_fp"]
    fn = all_results["overall_summary"]["total_fn"]
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0
    f_score = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0
    all_results["overall_summary"]["precision"] = round(precision * 100, 1)
    all_results["overall_summary"]["recall"] = round(recall * 100, 1)
    all_results["overall_summary"]["f_score"] = round(f_score * 100, 1)

    out_file = run_dir / f"{tool_name}_eval.json"
    with open(out_file, "w") as f:
        json.dump(all_results, f, indent=2)

    print(f"\n{'='*70}")
    print(f"{tool_name.upper()} RESULTS ACROSS ALL REPOS")
    print(f"{'='*70}")
    for repo_result in all_results["repos"]:
        s = repo_result["summary"]
        print(f"{repo_result['repo']:30} | TP={s['total_tp']:2} FP={s['total_fp']:2} FN={s['total_fn']:2} | P={s['precision']:5.1f}% R={s['recall']:5.1f}% F={s['f_score']:5.1f}%")
    print(f"{'='*70}")
    print(f"{'OVERALL':30} | TP={tp:2} FP={fp:2} FN={fn:2} | P={all_results['overall_summary']['precision']:5.1f}% R={all_results['overall_summary']['recall']:5.1f}% F={all_results['overall_summary']['f_score']:5.1f}%")
    print(f"\nResults saved to {out_file}")
