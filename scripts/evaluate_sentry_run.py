#!/usr/bin/env python3
"""
Evaluate Droid review comments against golden comments for droid-sentry.
Usage: ANTHROPIC_API_KEY="sk-..." python3 scripts/evaluate_sentry_run.py <run_name>
Example: ANTHROPIC_API_KEY="sk-..." python3 scripts/evaluate_sentry_run.py run_2026-01-14-v3
"""

import json
import os
import sys
from anthropic import Anthropic

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
        "droid_count": len(pr_data.get("review_comments", [])),
        "evaluations": [],
        "true_positives": [],
        "false_positives": [],
        "false_negatives": [],
        "duplicates": []
    }
    
    matched_golden = set()
    
    for comment in pr_data.get("review_comments", []):
        eval_result = evaluate_match(comment["body"], golden_comments)
        eval_result["droid_comment"] = comment["body"]
        eval_result["file"] = comment.get("path", "unknown")
        eval_result["line"] = comment.get("line", "unknown")
        results["evaluations"].append(eval_result)
        
        if eval_result["matches"]:
            # Normalize the matched golden comment by removing severity prefix for comparison
            matched_text = eval_result["matched_golden_comment"]
            # The LLM returns "[Severity] comment text", but we need just the comment text
            # Find the matching golden comment by checking if matched_text contains the comment
            matched_golden_key = None
            for gc in golden_comments:
                # Check if the matched text (which may have [severity] prefix) contains the actual comment
                if gc["comment"] in matched_text or matched_text in f"[{gc['severity']}] {gc['comment']}":
                    matched_golden_key = gc["comment"]
                    break
            
            # Check if this golden comment was already matched by another droid comment
            if matched_golden_key and matched_golden_key in matched_golden:
                # This is a duplicate - same golden issue found by multiple droid comments
                results["duplicates"].append(eval_result)
            elif matched_golden_key:
                # First droid comment to match this golden issue
                results["true_positives"].append(eval_result)
                matched_golden.add(matched_golden_key)
        else:
            results["false_positives"].append(eval_result)
    
    for golden in golden_comments:
        if golden["comment"] not in matched_golden:
            results["false_negatives"].append({
                "golden_comment": golden["comment"],
                "severity": golden["severity"]
            })
    
    # Calculate per-PR metrics
    # TP = number of unique golden comments matched (not number of droid comments that matched)
    tp = len(matched_golden)
    fp = len(results["false_positives"])
    fn = len(results["false_negatives"])
    
    precision = (tp / (tp + fp)) if (tp + fp) > 0 else 0.0
    recall = (tp / (tp + fn)) if (tp + fn) > 0 else 0.0
    f_score = (2 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0.0
    
    results["metrics"] = {
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "duplicates": len(results["duplicates"]),
        "precision": round(precision * 100, 1),
        "recall": round(recall * 100, 1),
        "f_score": round(f_score * 100, 1)
    }
    
    return results

def main():
    if len(sys.argv) < 2:
        run_name = f"run_{os.popen('date +%Y-%m-%d').read().strip()}-v3"
    else:
        run_name = sys.argv[1]
    
    base_path = os.path.expanduser(f"~/review-droid-benchmark/results/{run_name}/raw_comments")
    output_path = os.path.expanduser(f"~/review-droid-benchmark/results/{run_name}")
    
    print(f"Evaluating run: {run_name}")
    
    # Load data
    with open(f"{base_path}/droid-sentry.json") as f:
        droid_data = json.load(f)
    
    with open(f"{base_path}/golden_sentry.json") as f:
        golden_data = json.load(f)
    
    golden_by_title = {g["pr_title"]: g["comments"] for g in golden_data}
    
    all_results = {
        "repo": "droid-sentry",
        "prs": [],
        "summary": {"total_tp": 0, "total_fp": 0, "total_fn": 0}
    }
    
    print(f"\nEvaluating droid-sentry...")
    
    for pr in droid_data["prs"]:
        golden_comments = golden_by_title.get(pr["title"], [])
        if not golden_comments:
            print(f"  WARNING: No golden comments for PR #{pr['number']}: {pr['title']}")
            continue
        
        print(f"  PR #{pr['number']}: {len(golden_comments)} golden, {len(pr.get('review_comments', []))} droid")
        result = evaluate_pr(pr, golden_comments)
        all_results["prs"].append(result)
        
        all_results["summary"]["total_tp"] += len(result["true_positives"])
        all_results["summary"]["total_fp"] += len(result["false_positives"])
        all_results["summary"]["total_fn"] += len(result["false_negatives"])
    
    tp, fp, fn = all_results["summary"]["total_tp"], all_results["summary"]["total_fp"], all_results["summary"]["total_fn"]
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0
    f_score = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0
    
    all_results["summary"]["precision"] = round(precision * 100, 1)
    all_results["summary"]["recall"] = round(recall * 100, 1)
    all_results["summary"]["f_score"] = round(f_score * 100, 1)
    
    with open(f"{output_path}/sentry_eval.json", "w") as f:
        json.dump(all_results, f, indent=2)
    
    print(f"\n{'='*50}")
    print(f"RESULTS: TP={tp}, FP={fp}, FN={fn}")
    print(f"Precision: {all_results['summary']['precision']}%")
    print(f"Recall: {all_results['summary']['recall']}%")
    print(f"F-score: {all_results['summary']['f_score']}%")
    print(f"\nResults saved to {output_path}/sentry_eval.json")

if __name__ == "__main__":
    main()
