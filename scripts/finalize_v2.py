#!/usr/bin/env python3
"""
Finalize Golden Comments v2 from revalidation results.

1. Generates revalidation_summary.json for each repo
2. Creates the final golden_comments_v2.json with all validated bugs
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any

BASE_DIR = Path(__file__).parent.parent
VALIDATION_DIR = BASE_DIR / "results" / "ground_truth_validation" / "run_2026-01-15"
MANIFEST_PATH = BASE_DIR / "manifest.json"
OUTPUT_PATH = BASE_DIR / "results" / "golden_comments_v2.json"

REPOS = ["sentry", "grafana", "keycloak", "discourse", "cal_dot_com"]

# PR ranges per repo
PR_RANGES = {
    "sentry": range(6, 16),      # PRs 6-15
    "grafana": range(1, 11),     # PRs 1-10
    "keycloak": range(1, 11),    # PRs 1-10
    "discourse": range(1, 11),   # PRs 1-10
    "cal_dot_com": range(1, 11), # PRs 1-10
}


def load_manifest() -> dict[str, Any]:
    with open(MANIFEST_PATH) as f:
        return json.load(f)


def load_revalidation_file(repo: str, pr_number: int) -> dict[str, Any] | None:
    filepath = VALIDATION_DIR / repo / f"pr_{pr_number}_revalidation.json"
    if not filepath.exists():
        print(f"  Warning: {filepath} not found")
        return None
    with open(filepath) as f:
        return json.load(f)


def generate_repo_summary(repo: str) -> dict[str, Any]:
    """Generate revalidation summary for a repo."""
    pr_numbers = list(PR_RANGES[repo])
    
    summary = {
        "repo": repo,
        "revalidation_date": datetime.now().strftime("%Y-%m-%d"),
        "prs_reviewed": [],
        "total_bugs_reviewed": 0,
        "confirmed": 0,
        "modified": 0,
        "rejected": 0,
        "false_positives_confirmed": 0,
        "false_positives_reversed": 0,
        "newly_discovered": 0,
    }
    
    for pr_number in pr_numbers:
        reval = load_revalidation_file(repo, pr_number)
        if not reval:
            continue
        
        summary["prs_reviewed"].append(pr_number)
        
        for bug in reval.get("bug_verdicts", []):
            summary["total_bugs_reviewed"] += 1
            verdict = bug.get("verdict", "")
            if verdict == "confirmed":
                summary["confirmed"] += 1
            elif verdict == "modified":
                summary["modified"] += 1
            elif verdict == "rejected":
                summary["rejected"] += 1
        
        for fp in reval.get("false_positive_verdicts", []):
            verdict = fp.get("verdict", "")
            if verdict == "confirmed_false_positive":
                summary["false_positives_confirmed"] += 1
            elif verdict == "actually_real_bug":
                summary["false_positives_reversed"] += 1
        
        summary["newly_discovered"] += len(reval.get("newly_discovered_bugs", []))
    
    return summary


def save_repo_summary(repo: str, summary: dict[str, Any]) -> Path:
    output_path = VALIDATION_DIR / repo / "revalidation_summary.json"
    with open(output_path, "w") as f:
        json.dump(summary, f, indent=2)
    return output_path


def build_golden_comments_v2() -> dict[str, Any]:
    """Build the final golden_comments_v2.json from all revalidation files."""
    manifest = load_manifest()
    
    output = {
        "version": "2.0",
        "generated_date": datetime.now().strftime("%Y-%m-%d"),
        "source": "ground_truth_validation/run_2026-01-15 + revalidation",
        "stats": {
            "total_repos": len(REPOS),
            "total_prs": 0,
            "total_bugs": 0,
            "bugs_by_verdict": {"confirmed": 0, "modified": 0},
            "bugs_by_type": {},
            "bugs_by_severity": {},
        },
        "repos": {}
    }
    
    for repo in REPOS:
        pr_numbers = list(PR_RANGES[repo])
        repo_data = {
            "pr_count": 0,
            "bug_count": 0,
            "prs": []
        }
        
        # Get PR titles from manifest
        pr_titles = {}
        for pr in manifest["projects"][repo]["prs"]:
            pr_titles[pr["number"]] = pr["title"]
        
        for pr_number in pr_numbers:
            reval = load_revalidation_file(repo, pr_number)
            if not reval:
                continue
            
            pr_title = reval.get("pr_title") or pr_titles.get(pr_number, f"PR #{pr_number}")
            
            # Collect confirmed/modified bugs only
            bugs = []
            for bug in reval.get("bug_verdicts", []):
                verdict = bug.get("verdict", "")
                if verdict in ("confirmed", "modified"):
                    bug_entry = {
                        "id": bug.get("bug_id"),
                        "file": bug.get("verified_file") or bug.get("file"),
                        "line": bug.get("verified_line") or bug.get("line"),
                        "description": bug.get("verified_description") or bug.get("original_description"),
                        "severity": bug.get("verified_severity") or bug.get("original_severity", "medium"),
                        "bug_type": bug.get("verified_bug_type") or bug.get("original_bug_type", "unknown"),
                    }
                    bugs.append(bug_entry)
                    
                    # Update stats
                    output["stats"]["bugs_by_verdict"][verdict] = output["stats"]["bugs_by_verdict"].get(verdict, 0) + 1
                    
                    bug_type = bug_entry["bug_type"]
                    output["stats"]["bugs_by_type"][bug_type] = output["stats"]["bugs_by_type"].get(bug_type, 0) + 1
                    
                    severity = bug_entry["severity"]
                    output["stats"]["bugs_by_severity"][severity] = output["stats"]["bugs_by_severity"].get(severity, 0) + 1
            
            # Add any newly discovered bugs
            for new_bug in reval.get("newly_discovered_bugs", []):
                bug_entry = {
                    "id": f"new_{len(bugs) + 1}",
                    "file": new_bug.get("file"),
                    "line": new_bug.get("line"),
                    "description": new_bug.get("description"),
                    "severity": new_bug.get("severity", "medium"),
                    "bug_type": new_bug.get("bug_type", "unknown"),
                    "newly_discovered": True
                }
                bugs.append(bug_entry)
                
                bug_type = bug_entry["bug_type"]
                output["stats"]["bugs_by_type"][bug_type] = output["stats"]["bugs_by_type"].get(bug_type, 0) + 1
                
                severity = bug_entry["severity"]
                output["stats"]["bugs_by_severity"][severity] = output["stats"]["bugs_by_severity"].get(severity, 0) + 1
            
            # Add reversed false positives as bugs
            for fp in reval.get("false_positive_verdicts", []):
                if fp.get("verdict") == "actually_real_bug":
                    bug_entry = {
                        "id": f"fp_reversed_{len(bugs) + 1}",
                        "file": fp.get("file", ""),
                        "line": fp.get("line"),
                        "description": fp.get("original_comment"),
                        "severity": fp.get("severity", "medium"),
                        "bug_type": fp.get("bug_type", "unknown"),
                        "from_reversed_false_positive": True
                    }
                    bugs.append(bug_entry)
            
            if bugs:
                pr_entry = {
                    "pr_number": pr_number,
                    "pr_title": pr_title,
                    "bug_count": len(bugs),
                    "bugs": bugs
                }
                repo_data["prs"].append(pr_entry)
                repo_data["bug_count"] += len(bugs)
                repo_data["pr_count"] += 1
        
        output["repos"][repo] = repo_data
        output["stats"]["total_prs"] += repo_data["pr_count"]
        output["stats"]["total_bugs"] += repo_data["bug_count"]
    
    return output


def print_summary(repo_summaries: dict[str, dict], golden: dict) -> None:
    """Print final summary."""
    print("\n" + "=" * 70)
    print("REVALIDATION SUMMARY BY REPO")
    print("=" * 70)
    
    for repo, summary in repo_summaries.items():
        print(f"\n{repo}:")
        print(f"  PRs reviewed: {len(summary['prs_reviewed'])}")
        print(f"  Bugs: {summary['confirmed']} confirmed, {summary['modified']} modified, {summary['rejected']} rejected")
        print(f"  False positives: {summary['false_positives_confirmed']} confirmed, {summary['false_positives_reversed']} reversed")
        if summary['newly_discovered'] > 0:
            print(f"  Newly discovered: {summary['newly_discovered']}")
    
    print("\n" + "=" * 70)
    print("GOLDEN COMMENTS V2 STATS")
    print("=" * 70)
    
    stats = golden["stats"]
    print(f"\nTotal: {stats['total_prs']} PRs, {stats['total_bugs']} bugs")
    
    print("\nBy verdict:")
    for verdict, count in sorted(stats["bugs_by_verdict"].items()):
        print(f"  {verdict}: {count}")
    
    print("\nBy severity:")
    for severity, count in sorted(stats["bugs_by_severity"].items(), key=lambda x: ["critical", "high", "medium", "low"].index(x[0]) if x[0] in ["critical", "high", "medium", "low"] else 99):
        print(f"  {severity}: {count}")
    
    print("\nBy type:")
    for bug_type, count in sorted(stats["bugs_by_type"].items(), key=lambda x: -x[1]):
        print(f"  {bug_type}: {count}")
    
    print("\n" + "=" * 70)


def main():
    print("Finalizing Golden Comments v2...")
    print(f"Reading from: {VALIDATION_DIR}")
    
    # Step 1: Generate repo summaries
    print("\n--- Generating Repo Summaries ---")
    repo_summaries = {}
    for repo in REPOS:
        print(f"\nProcessing {repo}...")
        summary = generate_repo_summary(repo)
        output_path = save_repo_summary(repo, summary)
        repo_summaries[repo] = summary
        print(f"  Saved summary to: {output_path}")
    
    # Step 2: Build golden_comments_v2.json
    print("\n--- Building Golden Comments v2 ---")
    golden = build_golden_comments_v2()
    
    with open(OUTPUT_PATH, "w") as f:
        json.dump(golden, f, indent=2)
    print(f"\nSaved to: {OUTPUT_PATH}")
    
    # Print summary
    print_summary(repo_summaries, golden)
    
    print(f"\nDone! Final output: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
