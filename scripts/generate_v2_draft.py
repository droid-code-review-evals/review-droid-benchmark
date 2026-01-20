#!/usr/bin/env python3
"""
Generate Golden Comments v2 Draft files from completeness data.

Reads all pr_{N}_completeness.json files and generates a consolidated
golden_comments_v2_draft.json per repo for revalidation.
"""

import json
import os
from pathlib import Path
from typing import Any

BASE_DIR = Path(__file__).parent.parent
VALIDATION_DIR = BASE_DIR / "results" / "ground_truth_validation" / "run_2026-01-15"
MANIFEST_PATH = BASE_DIR / "manifest.json"

REPOS = ["sentry", "grafana", "keycloak", "discourse", "cal_dot_com"]


def load_manifest() -> dict[str, Any]:
    with open(MANIFEST_PATH) as f:
        return json.load(f)


def get_pr_title(manifest: dict, repo: str, pr_number: int) -> str:
    """Get PR title from manifest."""
    prs = manifest["projects"][repo]["prs"]
    for pr in prs:
        if pr["number"] == pr_number:
            return pr["title"]
    return f"PR #{pr_number}"


def load_completeness_file(repo: str, pr_number: int) -> dict[str, Any] | None:
    """Load a completeness file for a given repo and PR."""
    filepath = VALIDATION_DIR / repo / f"pr_{pr_number}_completeness.json"
    if not filepath.exists():
        print(f"  Warning: {filepath} not found")
        return None
    with open(filepath) as f:
        return json.load(f)


def get_pr_numbers_for_repo(repo: str) -> list[int]:
    """Get PR numbers for a repo based on manifest."""
    manifest = load_manifest()
    prs = manifest["projects"][repo]["prs"]
    return sorted([pr["number"] for pr in prs])


def generate_draft_for_repo(repo: str) -> dict[str, Any]:
    """Generate draft golden comments v2 for a single repo."""
    manifest = load_manifest()
    pr_numbers = get_pr_numbers_for_repo(repo)
    
    draft = {
        "repo": repo,
        "generated_from": "ground_truth_validation/run_2026-01-15",
        "total_bugs": 0,
        "total_false_positives": 0,
        "prs": []
    }
    
    for pr_number in pr_numbers:
        completeness = load_completeness_file(repo, pr_number)
        if not completeness:
            continue
        
        pr_title = completeness.get("pr_title") or get_pr_title(manifest, repo, pr_number)
        
        # Extract ground truth bugs with source attribution
        bugs = []
        ground_truth_bugs = completeness.get("ground_truth_bugs", [])
        droid_found = set(completeness.get("droid_metrics", {}).get("bugs_found", []))
        golden_found = set(completeness.get("golden_metrics", {}).get("bugs_found", []))
        
        for bug in ground_truth_bugs:
            bug_id = bug.get("id")
            
            # Determine source
            if bug.get("found_by"):
                found_by = bug["found_by"]
            else:
                in_droid = bug_id in droid_found
                in_golden = bug_id in golden_found
                if in_droid and in_golden:
                    found_by = "both"
                elif in_droid:
                    found_by = "droid_only"
                elif in_golden:
                    found_by = "golden_only"
                else:
                    found_by = "unknown"
            
            bugs.append({
                "id": bug_id,
                "description": bug.get("description", ""),
                "file": bug.get("file", ""),
                "line": bug.get("line"),
                "severity": bug.get("severity", "medium"),
                "bug_type": bug.get("bug_type") or bug.get("type", "unknown"),
                "found_by": found_by,
                "details": bug.get("details", "")
            })
        
        # Extract false positives
        false_positives = completeness.get("golden_false_positives", [])
        
        pr_entry = {
            "pr_number": pr_number,
            "pr_title": pr_title,
            "bug_count": len(bugs),
            "false_positive_count": len(false_positives),
            "ground_truth_bugs": bugs,
            "original_false_positives": false_positives
        }
        
        draft["prs"].append(pr_entry)
        draft["total_bugs"] += len(bugs)
        draft["total_false_positives"] += len(false_positives)
    
    return draft


def save_draft(repo: str, draft: dict[str, Any]) -> Path:
    """Save draft to file."""
    output_path = VALIDATION_DIR / repo / "golden_comments_v2_draft.json"
    with open(output_path, "w") as f:
        json.dump(draft, f, indent=2)
    return output_path


def print_summary(drafts: dict[str, dict]) -> None:
    """Print summary statistics."""
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    
    total_bugs = 0
    total_fps = 0
    total_prs = 0
    
    for repo, draft in drafts.items():
        bugs = draft["total_bugs"]
        fps = draft["total_false_positives"]
        prs = len(draft["prs"])
        total_bugs += bugs
        total_fps += fps
        total_prs += prs
        
        print(f"\n{repo}:")
        print(f"  PRs: {prs}")
        print(f"  Total bugs: {bugs}")
        print(f"  False positives to re-check: {fps}")
        
        # Count by source
        both = sum(1 for pr in draft["prs"] for b in pr["ground_truth_bugs"] if b["found_by"] == "both")
        droid_only = sum(1 for pr in draft["prs"] for b in pr["ground_truth_bugs"] if b["found_by"] == "droid_only")
        golden_only = sum(1 for pr in draft["prs"] for b in pr["ground_truth_bugs"] if b["found_by"] == "golden_only")
        
        print(f"  Found by both: {both}")
        print(f"  Droid-only (added): {droid_only}")
        print(f"  Golden-only: {golden_only}")
    
    print("\n" + "-" * 60)
    print(f"TOTAL: {total_prs} PRs, {total_bugs} bugs, {total_fps} false positives to re-check")
    print("=" * 60)


def main():
    print("Generating Golden Comments v2 Draft files...")
    print(f"Reading from: {VALIDATION_DIR}")
    
    drafts = {}
    
    for repo in REPOS:
        print(f"\nProcessing {repo}...")
        draft = generate_draft_for_repo(repo)
        output_path = save_draft(repo, draft)
        drafts[repo] = draft
        print(f"  Saved to: {output_path}")
    
    print_summary(drafts)
    
    print("\nDraft files generated. Next step: Run revalidation playbook for each repo.")


if __name__ == "__main__":
    main()
