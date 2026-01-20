# Golden Comments v2 Plan

**Purpose:** Create a comprehensive, fully-validated `golden_comments_v2.json` from our ground truth validation results.

**Created:** 2026-01-20

---

## Overview

We have validated ground truth data across **5 repos x 10 PRs = 50 PRs** in `results/ground_truth_validation/run_2026-01-15/`. This plan outlines how to:
1. Generate a draft from existing completeness files
2. Fully revalidate all bugs (not just disputed ones)
3. Produce a final, high-confidence golden comments file

---

## Phase 1: Generate Draft Golden Comments v2

### Step 1.1: Extract and Consolidate

Create a script that parses all 50 `pr_{N}_completeness.json` files and generates a draft per repo containing:
- All ground truth bugs with file/line/severity/type
- Original source attribution (`found_by: both|golden_only|droid_only`)
- Original golden false positives (for re-checking)

### Step 1.2: Output Draft Files

Location:
```
results/ground_truth_validation/run_2026-01-15/{repo}/golden_comments_v2_draft.json
```

Schema:
```json
{
  "repo": "sentry",
  "generated_from": "ground_truth_validation/run_2026-01-15",
  "prs": [
    {
      "pr_number": 6,
      "pr_title": "Enhanced Pagination...",
      "ground_truth_bugs": [
        {
          "id": 1,
          "description": "member None AttributeError",
          "file": "src/sentry/api/endpoints/organization_auditlogs.py",
          "line": 71,
          "severity": "high",
          "bug_type": "runtime_error",
          "found_by": "both"
        }
      ],
      "original_false_positives": [
        {
          "comment": "Importing non-existent OptimizedCursorPaginator",
          "reasoning": "OptimizedCursorPaginator exists at line 819"
        }
      ]
    }
  ]
}
```

### Artifacts

| File | Purpose |
|------|---------|
| `scripts/generate_v2_draft.py` | Extract/consolidate from completeness files |
| `{repo}/golden_comments_v2_draft.json` | Draft with all bugs for review |

---

## Phase 2: Full Revalidation (Manual)

### Step 2.1: Create Revalidation Playbook

New document: `docs/REVALIDATION_PLAYBOOK.md`

For each PR, review **everything**:

| Category | Action |
|----------|--------|
| **All Ground Truth Bugs** | Confirm each is a real bug at the stated file/line |
| **Claimed False Positives** | Confirm these original golden comments are truly NOT bugs |
| **Bug Descriptions** | Verify descriptions are accurate and specific |
| **Severities** | Confirm severity ratings are appropriate |
| **File/Line Locations** | Verify exact locations are correct |

### Step 2.2: Revalidation Session Format

```
"Follow the revalidation playbook for {REPO_NAME}"
```

This processes all 10 PRs for that repo, producing one output file per PR.

### Step 2.3: Revalidation Output Schema

Location:
```
results/ground_truth_validation/run_2026-01-15/{repo}/pr_{N}_revalidation.json
```

Schema:
```json
{
  "pr_number": 6,
  "pr_title": "Enhanced Pagination...",
  "revalidation_date": "2026-01-20",
  
  "bug_verdicts": [
    {
      "bug_id": 1,
      "original_description": "member None AttributeError",
      "file": "src/sentry/api/endpoints/organization_auditlogs.py",
      "line": 71,
      "original_severity": "high",
      "original_source": "both",
      
      "verdict": "confirmed|rejected|modified",
      "verified_file": "src/sentry/api/endpoints/organization_auditlogs.py",
      "verified_line": 71,
      "verified_severity": "high",
      "verified_description": "organization_context.member can be None for API key auth, causing AttributeError on .has_global_access access",
      "notes": "Re-verified by checking auth middleware"
    }
  ],
  
  "false_positive_verdicts": [
    {
      "original_comment": "Importing non-existent OptimizedCursorPaginator",
      "original_reasoning": "OptimizedCursorPaginator exists at line 819",
      "verdict": "confirmed_false_positive|actually_real_bug",
      "notes": "Re-verified: class exists"
    }
  ],
  
  "newly_discovered_bugs": []
}
```

### Step 2.4: Repo-Level Summary

After completing all 10 PRs for a repo:
```
results/ground_truth_validation/run_2026-01-15/{repo}/revalidation_summary.json
```

Schema:
```json
{
  "repo": "sentry",
  "revalidation_date": "2026-01-20",
  "total_bugs_reviewed": 28,
  "confirmed": 26,
  "rejected": 1,
  "modified": 1,
  "false_positives_confirmed": 5,
  "false_positives_reversed": 0,
  "newly_discovered": 0
}
```

### Artifacts

| File | Purpose |
|------|---------|
| `docs/REVALIDATION_PLAYBOOK.md` | Instructions for full revalidation |
| `{repo}/pr_{N}_revalidation.json` | Per-PR revalidation verdicts |
| `{repo}/revalidation_summary.json` | Per-repo summary stats |

---

## Phase 3: Finalize Golden Comments v2

### Step 3.1: Merge All Revalidation Results

Script reads all `pr_{N}_revalidation.json` files and:
- Includes only bugs with `verdict: confirmed|modified`
- Uses `verified_*` fields for final data
- Excludes rejected bugs
- Adds any newly discovered bugs
- Excludes confirmed false positives

### Step 3.2: Generate Final Output

Location:
```
results/golden_comments_v2.json
```

Schema:
```json
{
  "version": "2.0",
  "generated_date": "2026-01-20",
  "source": "ground_truth_validation/run_2026-01-15 + revalidation",
  "repos": {
    "sentry": {
      "prs": [
        {
          "pr_number": 6,
          "pr_title": "Enhanced Pagination...",
          "bug_count": 4,
          "bugs": [
            {
              "id": 1,
              "file": "src/sentry/api/endpoints/organization_auditlogs.py",
              "line": 71,
              "description": "organization_context.member can be None for API key auth, causing AttributeError on .has_global_access access",
              "severity": "high",
              "bug_type": "runtime_error"
            }
          ]
        }
      ]
    }
  }
}
```

### Artifacts

| File | Purpose |
|------|---------|
| `scripts/finalize_v2.py` | Merge revalidation into final |
| `results/golden_comments_v2.json` | Final comprehensive golden comments |

---

## Workload Estimate

| Repo | PRs | Est. Bugs to Review | Est. False Positives |
|------|-----|---------------------|----------------------|
| sentry | 10 (PRs 6-15) | ~25-30 | ~5-8 |
| grafana | 10 (PRs 1-10) | ~20-25 | ~5-7 |
| keycloak | 10 (PRs 1-10) | ~20-25 | ~4-6 |
| discourse | 10 (PRs 1-10) | ~20-25 | ~3-5 |
| cal_dot_com | 10 (PRs 1-10) | ~25-30 | ~3-5 |
| **Total** | **50** | **~110-135** | **~20-31** |

---

## File Summary

| Phase | File | Purpose |
|-------|------|---------|
| 1 | `scripts/generate_v2_draft.py` | Extract/consolidate from completeness files |
| 1 | `{repo}/golden_comments_v2_draft.json` | Draft with all bugs for review |
| 1 | `docs/REVALIDATION_PLAYBOOK.md` | Instructions for full revalidation |
| 2 | `{repo}/pr_{N}_revalidation.json` | Per-PR revalidation verdicts |
| 2 | `{repo}/revalidation_summary.json` | Per-repo summary stats |
| 3 | `scripts/finalize_v2.py` | Merge revalidation into final |
| 3 | `results/golden_comments_v2.json` | Final comprehensive golden comments |

---

## Next Steps

1. [ ] Create `scripts/generate_v2_draft.py` and run it
2. [ ] Create `docs/REVALIDATION_PLAYBOOK.md`
3. [ ] Run revalidation for each repo (manual sessions)
4. [ ] Create `scripts/finalize_v2.py` and generate final output
