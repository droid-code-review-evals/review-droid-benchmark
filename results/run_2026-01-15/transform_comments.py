#!/usr/bin/env python3
"""Transform individual PR comment files into the format expected by evaluation script."""

import json
from datetime import datetime

# PR titles mapping
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

result = {
    "repo": "droid-sentry",
    "fetched_at": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
    "prs": []
}

for pr_num in range(6, 16):
    with open(f"pr_{pr_num}_comments.json") as f:
        comments = json.load(f)
    
    # Filter only factory-droid bot comments
    review_comments = [
        {
            "body": c["body"],
            "created_at": c["created_at"],
            "html_url": c["html_url"],
            "id": c["id"],
            "line": c.get("line"),
            "path": c["path"],
            "side": c.get("side", "RIGHT")
        }
        for c in comments
        if c["user"]["login"] == "factory-droid[bot]"
    ]
    
    pr_data = {
        "number": pr_num,
        "title": pr_titles[pr_num],
        "issue_comments": [],
        "review_comments": review_comments,
        "reviews": []
    }
    
    result["prs"].append(pr_data)

# Save to the expected location
with open("raw_comments/droid-sentry.json", "w") as f:
    json.dump(result, f, indent=2)

print(f"Transformed comments for {len(result['prs'])} PRs")
print(f"Total review comments: {sum(len(pr['review_comments']) for pr in result['prs'])}")
