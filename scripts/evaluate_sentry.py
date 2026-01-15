#!/usr/bin/env python3
"""
Evaluate Droid review comments against golden comments using LLM-as-judge.
"""

import json
import os
from anthropic import Anthropic

# Load data
with open(os.path.expanduser("~/review-droid-benchmark/results/run_2026-01-13/raw_comments/droid-sentry.json")) as f:
    droid_data = json.load(f)

with open(os.path.expanduser("~/review-droid-benchmark/results/run_2026-01-13/raw_comments/golden_sentry.json")) as f:
    golden_data = json.load(f)

# Build title -> golden comments mapping
golden_by_title = {g["pr_title"]: g["comments"] for g in golden_data}

# Initialize Anthropic client
client = Anthropic()

def evaluate_match(droid_comment: str, golden_comments: list[dict]) -> dict:
    """Use Claude to determine if a Droid comment matches any golden comment."""
    
    golden_list = "\n".join([
        f"- [{g['severity']}] {g['comment']}" 
        for g in golden_comments
    ])
    
    prompt = f"""You are evaluating whether a code review comment from an AI reviewer matches any of the expected findings (golden comments) for a PR.

GOLDEN COMMENTS (expected findings):
{golden_list}

DROID'S COMMENT:
{droid_comment}

Does Droid's comment match ANY of the golden comments? Two comments "match" if they describe the same bug/issue, even if worded differently.

Respond in this exact JSON format:
{{
  "matches": true or false,
  "matched_golden_comment": "the golden comment text that matches, or null if no match",
  "matched_severity": "the severity of the matched golden comment, or null",
  "confidence": "high", "medium", or "low",
  "reasoning": "brief explanation of why this is or isn't a match"
}}

Only output the JSON, nothing else."""

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=500,
        messages=[{"role": "user", "content": prompt}]
    )
    
    try:
        return json.loads(response.content[0].text)
    except json.JSONDecodeError:
        return {
            "matches": False,
            "matched_golden_comment": None,
            "matched_severity": None,
            "confidence": "low",
            "reasoning": f"Failed to parse response: {response.content[0].text[:200]}"
        }

def evaluate_pr(pr_data: dict, golden_comments: list[dict]) -> dict:
    """Evaluate all Droid comments for a single PR."""
    
    results = {
        "pr_number": pr_data["number"],
        "pr_title": pr_data["title"],
        "golden_count": len(golden_comments),
        "droid_count": len(pr_data["review_comments"]),
        "evaluations": [],
        "true_positives": [],
        "false_positives": [],
        "false_negatives": []
    }
    
    matched_golden = set()
    
    # Evaluate each Droid comment
    for comment in pr_data["review_comments"]:
        eval_result = evaluate_match(comment["body"], golden_comments)
        eval_result["droid_comment"] = comment["body"]
        eval_result["file"] = comment.get("path", "unknown")
        eval_result["line"] = comment.get("line", "unknown")
        results["evaluations"].append(eval_result)
        
        if eval_result["matches"]:
            results["true_positives"].append(eval_result)
            if eval_result["matched_golden_comment"]:
                matched_golden.add(eval_result["matched_golden_comment"])
        else:
            results["false_positives"].append(eval_result)
    
    # Find false negatives (golden comments not matched)
    for golden in golden_comments:
        if golden["comment"] not in matched_golden:
            # Check if any TP matched this golden comment
            matched = False
            for tp in results["true_positives"]:
                if tp.get("matched_golden_comment") == golden["comment"]:
                    matched = True
                    break
            if not matched:
                results["false_negatives"].append({
                    "golden_comment": golden["comment"],
                    "severity": golden["severity"]
                })
    
    return results

# Run evaluation
all_results = {
    "repo": "droid-sentry",
    "prs": [],
    "summary": {
        "total_tp": 0,
        "total_fp": 0,
        "total_fn": 0,
        "precision": 0,
        "recall": 0,
        "f_score": 0
    }
}

print("Evaluating Droid comments against golden comments...\n")

for pr in droid_data["prs"]:
    title = pr["title"]
    golden_comments = golden_by_title.get(title, [])
    
    if not golden_comments:
        print(f"WARNING: No golden comments found for PR #{pr['number']}: {title}")
        continue
    
    print(f"Evaluating PR #{pr['number']}: {title}")
    print(f"  Golden comments: {len(golden_comments)}, Droid comments: {len(pr['review_comments'])}")
    
    result = evaluate_pr(pr, golden_comments)
    all_results["prs"].append(result)
    
    all_results["summary"]["total_tp"] += len(result["true_positives"])
    all_results["summary"]["total_fp"] += len(result["false_positives"])
    all_results["summary"]["total_fn"] += len(result["false_negatives"])
    
    print(f"  TP: {len(result['true_positives'])}, FP: {len(result['false_positives'])}, FN: {len(result['false_negatives'])}")
    print()

# Calculate final metrics
tp = all_results["summary"]["total_tp"]
fp = all_results["summary"]["total_fp"]
fn = all_results["summary"]["total_fn"]

precision = tp / (tp + fp) if (tp + fp) > 0 else 0
recall = tp / (tp + fn) if (tp + fn) > 0 else 0
f_score = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0

all_results["summary"]["precision"] = round(precision * 100, 1)
all_results["summary"]["recall"] = round(recall * 100, 1)
all_results["summary"]["f_score"] = round(f_score * 100, 1)

# Save results
output_path = os.path.expanduser("~/review-droid-benchmark/results/run_2026-01-13/evaluations/droid-sentry_eval.json")
os.makedirs(os.path.dirname(output_path), exist_ok=True)
with open(output_path, "w") as f:
    json.dump(all_results, f, indent=2)

# Print summary
print("=" * 60)
print("SUMMARY")
print("=" * 60)
print(f"Total True Positives:  {tp}")
print(f"Total False Positives: {fp}")
print(f"Total False Negatives: {fn}")
print()
print(f"Precision: {all_results['summary']['precision']}%")
print(f"Recall:    {all_results['summary']['recall']}%")
print(f"F-score:   {all_results['summary']['f_score']}%")
print()
print(f"Results saved to: {output_path}")
