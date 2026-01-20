#!/usr/bin/env python3
"""
Create v2 golden comments in multiple formats for droid-golden_comments repo.

Generates:
1. v2/code_review_benchmarks/{repo}.json - Compatible format (same as v1)
2. v2/detailed/{repo}.json - Extended format with file/line info
"""

import json
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
INPUT_PATH = BASE_DIR / "results" / "golden_comments_v2.json"
OUTPUT_DIR = BASE_DIR / "work" / "droid-golden_comments"
V1_DIR = BASE_DIR / "repos" / "golden_comments" / "code_review_benchmarks"

REPOS = ["sentry", "grafana", "keycloak", "discourse", "cal_dot_com"]


def load_golden_v2():
    with open(INPUT_PATH) as f:
        return json.load(f)


def load_v1_repo(repo: str):
    filepath = V1_DIR / f"{repo}.json"
    with open(filepath) as f:
        return json.load(f)


def severity_to_title_case(severity: str) -> str:
    """Convert 'high' to 'High', 'medium' to 'Medium', etc."""
    if severity.lower() == "critical":
        return "Critical"
    elif severity.lower() == "high":
        return "High"
    elif severity.lower() == "medium":
        return "Medium"
    elif severity.lower() == "low":
        return "Low"
    return severity.title()


def create_compatible_format(repo_data: dict) -> list:
    """Create v1-compatible format (pr_title + comments with comment/severity)."""
    output = []
    
    for pr in repo_data.get("prs", []):
        comments = []
        for bug in pr.get("bugs", []):
            comments.append({
                "comment": bug["description"],
                "severity": severity_to_title_case(bug.get("severity", "Medium"))
            })
        
        output.append({
            "pr_title": pr["pr_title"],
            "comments": comments
        })
    
    return output


def create_detailed_format(repo_data: dict) -> list:
    """Create detailed format with file/line/bug_type info."""
    output = []
    
    for pr in repo_data.get("prs", []):
        bugs = []
        for bug in pr.get("bugs", []):
            bugs.append({
                "id": bug.get("id"),
                "file": bug.get("file", ""),
                "line": bug.get("line"),
                "description": bug["description"],
                "severity": bug.get("severity", "medium"),
                "bug_type": bug.get("bug_type", "unknown")
            })
        
        output.append({
            "pr_number": pr["pr_number"],
            "pr_title": pr["pr_title"],
            "bug_count": len(bugs),
            "bugs": bugs
        })
    
    return output


def generate_changelog(v2_data: dict) -> str:
    """Generate changelog comparing v1 and v2."""
    lines = [
        "# Changelog: v1 to v2",
        "",
        "This document summarizes the changes between the original golden comments (v1) and our validated version (v2).",
        "",
        "## Summary",
        "",
    ]
    
    # Load v1 stats
    v1_total = 0
    v1_by_repo = {}
    for repo in REPOS:
        v1_data = load_v1_repo(repo)
        count = sum(len(pr.get("comments", [])) for pr in v1_data)
        v1_by_repo[repo] = count
        v1_total += count
    
    v2_total = v2_data["stats"]["total_bugs"]
    
    lines.extend([
        f"| Metric | v1 (Original) | v2 (Validated) |",
        f"|--------|---------------|----------------|",
        f"| Total Comments/Bugs | {v1_total} | {v2_total} |",
        f"| False Positives Removed | - | ~{v1_total - v2_total + 19} |",
        f"| Bugs Rejected During Revalidation | - | 19 |",
        f"| Has File/Line Info | No | Yes |",
        f"| Has Bug Type | No | Yes |",
        f"| Manually Validated | No | Yes |",
        "",
        "## Changes by Repository",
        "",
    ])
    
    for repo in REPOS:
        v1_count = v1_by_repo[repo]
        v2_count = v2_data["repos"][repo]["bug_count"]
        diff = v2_count - v1_count
        sign = "+" if diff > 0 else ""
        
        lines.extend([
            f"### {repo}",
            f"- v1: {v1_count} comments",
            f"- v2: {v2_count} bugs ({sign}{diff})",
            "",
        ])
    
    lines.extend([
        "## Validation Process",
        "",
        "v2 was created through a rigorous validation process:",
        "",
        "1. **Initial Validation**: Each PR was reviewed using the VALIDATION_PLAYBOOK.md",
        "2. **Ground Truth Establishment**: Real bugs were identified with exact file/line locations",
        "3. **False Positive Identification**: Original golden comments that weren't real bugs were flagged",
        "4. **Revalidation**: All bugs and false positives were re-examined using REVALIDATION_PLAYBOOK.md",
        "5. **Final Review**: Bugs were confirmed, modified, or rejected based on code evidence",
        "",
        "## Bug Types in v2",
        "",
    ])
    
    for bug_type, count in sorted(v2_data["stats"]["bugs_by_type"].items(), key=lambda x: -x[1]):
        lines.append(f"- {bug_type}: {count}")
    
    lines.extend([
        "",
        "## Severity Distribution in v2",
        "",
    ])
    
    for severity in ["critical", "high", "medium", "low"]:
        count = v2_data["stats"]["bugs_by_severity"].get(severity, 0)
        if count > 0:
            lines.append(f"- {severity.title()}: {count}")
    
    return "\n".join(lines)


def main():
    print("Creating v2 golden comments formats...")
    
    v2_data = load_golden_v2()
    
    # Generate per-repo files
    for repo in REPOS:
        print(f"\nProcessing {repo}...")
        repo_data = v2_data["repos"][repo]
        
        # Compatible format
        compatible = create_compatible_format(repo_data)
        compatible_path = OUTPUT_DIR / "v2" / "code_review_benchmarks" / f"{repo}.json"
        with open(compatible_path, "w") as f:
            json.dump(compatible, f, indent=2)
        print(f"  Created {compatible_path}")
        
        # Detailed format
        detailed = create_detailed_format(repo_data)
        detailed_path = OUTPUT_DIR / "v2" / "detailed" / f"{repo}.json"
        with open(detailed_path, "w") as f:
            json.dump(detailed, f, indent=2)
        print(f"  Created {detailed_path}")
    
    # Generate changelog
    print("\nGenerating CHANGELOG.md...")
    changelog = generate_changelog(v2_data)
    changelog_path = OUTPUT_DIR / "CHANGELOG.md"
    with open(changelog_path, "w") as f:
        f.write(changelog)
    print(f"  Created {changelog_path}")
    
    print("\nDone!")


if __name__ == "__main__":
    main()
