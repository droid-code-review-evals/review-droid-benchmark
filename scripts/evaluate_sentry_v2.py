#!/usr/bin/env python3
"""
One-off evaluation script for droid-sentry v2 results.
Compares new Droid review comments against golden comments.
"""

import json
import os
import subprocess
from anthropic import Anthropic

# Config
REPO = "droid-code-review-evals/droid-sentry"
PRS = [6, 7, 8, 9, 10, 11, 12, 13, 14, 15]
OUTPUT_DIR = "results/run_2026-01-13-v2"
GOLDEN_FILE = "results/run_2026-01-13/raw_comments/golden_sentry.json"

def fetch_droid_comments():
    """Fetch all Droid comments from the PRs."""
    all_comments = {}
    
    for pr_num in PRS:
        print(f"Fetching comments for PR #{pr_num}...")
        comments = []
        
        # Get issue comments
        result = subprocess.run(
            ["gh", "api", f"repos/{REPO}/issues/{pr_num}/comments", "--paginate"],
            capture_output=True, text=True
        )
        if result.returncode == 0:
            issue_comments = json.loads(result.stdout)
            for c in issue_comments:
                if c.get("user", {}).get("login") == "factory-droid[bot]":
                    comments.append({"type": "issue", "body": c["body"], "id": c["id"]})
        
        # Get review comments (inline)
        result = subprocess.run(
            ["gh", "api", f"repos/{REPO}/pulls/{pr_num}/comments", "--paginate"],
            capture_output=True, text=True
        )
        if result.returncode == 0:
            review_comments = json.loads(result.stdout)
            for c in review_comments:
                if c.get("user", {}).get("login") == "factory-droid[bot]":
                    comments.append({
                        "type": "inline",
                        "body": c["body"],
                        "path": c.get("path"),
                        "line": c.get("line"),
                        "id": c["id"]
                    })
        
        # Get reviews
        result = subprocess.run(
            ["gh", "api", f"repos/{REPO}/pulls/{pr_num}/reviews", "--paginate"],
            capture_output=True, text=True
        )
        if result.returncode == 0:
            reviews = json.loads(result.stdout)
            for r in reviews:
                if r.get("user", {}).get("login") == "factory-droid[bot]":
                    body = r.get("body", "").strip()
                    if body and body != "....":
                        comments.append({"type": "review", "body": body, "id": r["id"]})
        
        all_comments[pr_num] = comments
    
    return all_comments

def extract_findings(comments):
    """Extract individual findings from Droid comments."""
    findings = []
    for c in comments:
        body = c.get("body", "")
        if not body or body == "....":
            continue
        # Skip "Droid is working" messages
        if "Droid is working" in body:
            continue
        # Each inline comment is typically one finding
        if c["type"] == "inline":
            findings.append({
                "body": body,
                "path": c.get("path"),
                "line": c.get("line")
            })
        # Review summaries may contain multiple findings or just summary
        elif c["type"] == "review":
            # Usually review body is summary, not findings
            pass
    return findings

def evaluate_with_llm(droid_findings, golden_comments, pr_title):
    """Use Claude to match Droid findings against golden comments."""
    client = Anthropic()
    
    if not droid_findings:
        return {
            "matches": [],
            "false_positives": [],
            "false_negatives": [{"golden_comment": g["comment"], "severity": g["severity"]} for g in golden_comments]
        }
    
    prompt = f"""You are evaluating an AI code reviewer's performance.

PR Title: {pr_title}

## Golden Comments (expected findings):
{json.dumps(golden_comments, indent=2)}

## Droid's Findings:
{json.dumps(droid_findings, indent=2)}

For each Droid finding, determine if it matches any golden comment (same underlying issue, even if worded differently).
For each golden comment, determine if Droid found it.

Return JSON:
{{
  "matches": [
    {{"droid_finding": "...", "golden_comment": "...", "golden_severity": "...", "confidence": "high/medium/low", "reasoning": "..."}}
  ],
  "false_positives": [
    {{"droid_finding": "...", "reasoning": "why this doesn't match any golden comment"}}
  ],
  "false_negatives": [
    {{"golden_comment": "...", "severity": "..."}}
  ]
}}

Be generous in matching - if Droid identifies the same root cause even with different wording, it's a match."""

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=4096,
        messages=[{"role": "user", "content": prompt}]
    )
    
    text = response.content[0].text
    # Extract JSON from response
    try:
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0]
        elif "```" in text:
            text = text.split("```")[1].split("```")[0]
        return json.loads(text)
    except:
        print(f"Failed to parse LLM response: {text[:200]}")
        return {"matches": [], "false_positives": [], "false_negatives": []}

def main():
    # Load golden comments
    with open(GOLDEN_FILE) as f:
        golden_data = json.load(f)
    
    # Create PR title -> golden comments mapping
    golden_by_title = {item["pr_title"]: item["comments"] for item in golden_data}
    
    # PR number -> title mapping (from manifest)
    pr_titles = {
        6: "Enhanced Pagination Performance for High-Volume Audit Logs",
        7: "Optimize spans buffer insertion with eviction during insert",
        8: "feat(upsampling) - Support upsampled error count with performance optimizations",
        9: "GitHub OAuth Security Enhancement",
        10: "Replays Self-Serve Bulk Delete System",
        11: "Span Buffer Multiprocess Enhancement with Health Monitoring",
        12: "feat(ecosystem): Implement cross-system issue synchronization",
        13: "ref(crons): Reorganize incident creation / issue occurrence logic",
        14: "feat(uptime): Add ability to use queues to manage parallelism",
        15: "feat(workflow_engine): Add in hook for producing occurrences from the stateful detector"
    }
    
    # Fetch new comments
    print("Fetching Droid comments...")
    droid_comments = fetch_droid_comments()
    
    # Save raw comments
    with open(f"{OUTPUT_DIR}/raw_comments/droid-sentry.json", "w") as f:
        json.dump(droid_comments, f, indent=2)
    print(f"Saved raw comments to {OUTPUT_DIR}/raw_comments/droid-sentry.json")
    
    # Evaluate each PR
    results = []
    total_tp, total_fp, total_fn = 0, 0, 0
    
    for pr_num in PRS:
        title = pr_titles[pr_num]
        golden = golden_by_title.get(title, [])
        findings = extract_findings(droid_comments.get(pr_num, []))
        
        print(f"\nEvaluating PR #{pr_num}: {title}")
        print(f"  Golden: {len(golden)} comments, Droid: {len(findings)} findings")
        
        eval_result = evaluate_with_llm(findings, golden, title)
        
        tp = len(eval_result.get("matches", []))
        fp = len(eval_result.get("false_positives", []))
        fn = len(eval_result.get("false_negatives", []))
        
        total_tp += tp
        total_fp += fp
        total_fn += fn
        
        print(f"  TP: {tp}, FP: {fp}, FN: {fn}")
        
        results.append({
            "pr_number": pr_num,
            "pr_title": title,
            "golden_count": len(golden),
            "droid_count": len(findings),
            "true_positives": tp,
            "false_positives": fp,
            "false_negatives": fn,
            "details": eval_result
        })
    
    # Calculate metrics
    precision = (total_tp / (total_tp + total_fp) * 100) if (total_tp + total_fp) > 0 else 0
    recall = (total_tp / (total_tp + total_fn) * 100) if (total_tp + total_fn) > 0 else 0
    f_score = (2 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0
    
    summary = {
        "total_tp": total_tp,
        "total_fp": total_fp,
        "total_fn": total_fn,
        "precision": round(precision, 1),
        "recall": round(recall, 1),
        "f_score": round(f_score, 1),
        "prs": results
    }
    
    # Save results
    with open(f"{OUTPUT_DIR}/sentry_eval.json", "w") as f:
        json.dump(summary, f, indent=2)
    
    print(f"\n{'='*50}")
    print(f"RESULTS SUMMARY (droid-sentry v2)")
    print(f"{'='*50}")
    print(f"True Positives:  {total_tp}")
    print(f"False Positives: {total_fp}")
    print(f"False Negatives: {total_fn}")
    print(f"Precision: {precision:.1f}%")
    print(f"Recall:    {recall:.1f}%")
    print(f"F-Score:   {f_score:.1f}%")
    print(f"\nResults saved to {OUTPUT_DIR}/sentry_eval.json")

if __name__ == "__main__":
    main()
