# Ground Truth Revalidation Playbook

**Purpose:** Fully revalidate all ground truth bugs and false positives to ensure high confidence in the final Golden Comments v2.

**Usage:** Open a Droid session and say: "Follow the revalidation playbook for {REPO_NAME} PR #{PR_NUMBER}"

Examples:
- "Follow the revalidation playbook for sentry PR #6"
- "Follow the revalidation playbook for grafana PR #1"
- "Follow the revalidation playbook for keycloak PR #5"

**Important:** Run ONE PR per session to avoid context overflow and mistakes.

---

## Overview

This playbook reviews **everything** from the initial ground truth validation:

| Category | Action |
|----------|--------|
| **All Ground Truth Bugs** | Confirm each is a real bug at the stated file/line |
| **Claimed False Positives** | Confirm these original golden comments are truly NOT bugs |
| **Bug Descriptions** | Verify descriptions are accurate and specific |
| **Severities** | Confirm severity ratings are appropriate |
| **File/Line Locations** | Verify exact locations are correct |

---

## Setup

**Repositories:**
- sentry: `/Users/user/review-droid-benchmark/work/droid-sentry` (PRs #6-15)
- grafana: `/Users/user/review-droid-benchmark/work/droid-grafana` (PRs #1-10)
- keycloak: `/Users/user/review-droid-benchmark/work/droid-keycloak` (PRs #1-10)
- discourse: `/Users/user/review-droid-benchmark/work/droid-discourse` (PRs #1-10)
- cal_dot_com: `/Users/user/review-droid-benchmark/work/droid-cal_dot_com` (PRs #1-10)

**Input Files:**
- Draft: `/Users/user/review-droid-benchmark/results/ground_truth_validation/run_2026-01-15/{REPO_NAME}/golden_comments_v2_draft.json`

**Output Directory:**
- `/Users/user/review-droid-benchmark/results/ground_truth_validation/run_2026-01-15/{REPO_NAME}/`

---

## Part 1: Load Draft and Checkout PR

### Step 1.1: Load the Draft File
Load from: `/Users/user/review-droid-benchmark/results/ground_truth_validation/run_2026-01-15/{REPO_NAME}/golden_comments_v2_draft.json`

Find the entry for PR #{PR_NUMBER}. It contains:
- `ground_truth_bugs`: All bugs to verify for this PR
- `original_false_positives`: Claims to re-check for this PR

### Step 1.2: Checkout the PR Code
```bash
cd /Users/user/review-droid-benchmark/work/droid-{REPO_NAME}

# Get PR's actual base branch
BASE_BRANCH=$(gh pr view {PR_NUMBER} --json baseRefName --jq '.baseRefName')

# Fetch and checkout
git fetch origin $BASE_BRANCH
git fetch origin pull/{PR_NUMBER}/head:pr-{PR_NUMBER}
git checkout pr-{PR_NUMBER}

# Get diff against base
git diff origin/$BASE_BRANCH...HEAD
```

---

## Part 2: Verify Each Ground Truth Bug

For each bug in `ground_truth_bugs`, perform the following:

### Step 2.1: Locate and Examine the Code
1. Navigate to `{file}` at line `{line}`
2. Read the full file context (not just the line)
3. Understand the function/class this code is in
4. Check imports and dependencies
5. Trace execution paths if needed

### Step 2.2: Determine Verdict

**Verdict Options:**
- `confirmed`: Bug is real, description accurate, location correct
- `modified`: Bug is real but needs corrections (description, severity, file, line)
- `rejected`: Not actually a bug upon re-examination

### Step 2.3: Record Bug Verdict

```json
{
  "bug_id": 1,
  "original_description": "member None AttributeError",
  "file": "src/sentry/api/endpoints/organization_auditlogs.py",
  "line": 71,
  "original_severity": "high",
  "original_source": "both",
  
  "verdict": "confirmed|modified|rejected",
  "verified_file": "src/sentry/api/endpoints/organization_auditlogs.py",
  "verified_line": 71,
  "verified_severity": "high",
  "verified_bug_type": "runtime_error",
  "verified_description": "organization_context.member can be None for API key auth, causing AttributeError on .has_global_access access",
  "notes": "Re-verified by checking auth middleware - member is set to None for org auth tokens"
}
```

**If Modified:**
- Update `verified_*` fields with corrections
- Explain what changed in `notes`

**If Rejected:**
- Set `verdict: "rejected"`
- Explain why in `notes`

---

## Part 3: Re-check False Positives

For each item in `original_false_positives`, verify it's truly NOT a bug:

### Step 3.1: Re-examine the Original Claim
1. Read the original golden comment
2. Read the original reasoning for why it's a false positive
3. Search the PR diff for the referenced issue
4. Examine the actual code

### Step 3.2: Determine Verdict

**Verdict Options:**
- `confirmed_false_positive`: Original reasoning holds, not a bug
- `actually_real_bug`: Upon re-examination, this IS a real bug

### Step 3.3: Record False Positive Verdict

```json
{
  "original_comment": "Importing non-existent OptimizedCursorPaginator",
  "original_reasoning": "OptimizedCursorPaginator exists at line 819",
  "verdict": "confirmed_false_positive|actually_real_bug",
  "notes": "Re-verified: class exists at src/sentry/api/paginator.py:819"
}
```

**If actually_real_bug:**
- Create a new bug entry to add to the ground truth
- Include full details (file, line, severity, description)

---

## Part 4: Check for Newly Discovered Bugs

While reviewing the PR, note any bugs you discover that weren't in the draft:

```json
{
  "description": "New bug description",
  "file": "path/to/file.py",
  "line": 123,
  "severity": "medium",
  "bug_type": "runtime_error",
  "notes": "Discovered during revalidation - not in original draft"
}
```

---

## Part 5: Save Revalidation Results

### Step 5.1: Save Per-PR Revalidation File
Save to: `/Users/user/review-droid-benchmark/results/ground_truth_validation/run_2026-01-15/{REPO_NAME}/pr_{PR_NUMBER}_revalidation.json`

```json
{
  "pr_number": 6,
  "pr_title": "feat(workflow_engine): Add in hook for...",
  "revalidation_date": "2026-01-20",
  
  "bug_verdicts": [
    {
      "bug_id": 1,
      "original_description": "...",
      "file": "...",
      "line": 71,
      "original_severity": "medium",
      "original_source": "both",
      "verdict": "confirmed",
      "verified_file": "...",
      "verified_line": 71,
      "verified_severity": "high",
      "verified_bug_type": "runtime_error",
      "verified_description": "...",
      "notes": "..."
    }
  ],
  
  "false_positive_verdicts": [
    {
      "original_comment": "...",
      "original_reasoning": "...",
      "verdict": "confirmed_false_positive",
      "notes": "..."
    }
  ],
  
  "newly_discovered_bugs": []
}
```

### Step 5.2: Repo Summary (After All PRs Complete)
**Note:** The repo summary is generated AFTER all PRs for a repo have been revalidated in separate sessions. 

Once all `pr_{N}_revalidation.json` files exist for a repo, run:
```
"Generate revalidation summary for {REPO_NAME}"
```

This will create: `/Users/user/review-droid-benchmark/results/ground_truth_validation/run_2026-01-15/{REPO_NAME}/revalidation_summary.json`

```json
{
  "repo": "sentry",
  "revalidation_date": "2026-01-20",
  "prs_reviewed": [6, 7, 8, 9, 10, 11, 12, 13, 14, 15],
  "total_bugs_reviewed": 30,
  "confirmed": 28,
  "modified": 1,
  "rejected": 1,
  "false_positives_confirmed": 9,
  "false_positives_reversed": 1,
  "newly_discovered": 0,
  "notes": "Any overall observations"
}
```

---

## Part 6: Cleanup

### Step 6.1: Return to Default Branch
```bash
cd /Users/user/review-droid-benchmark/work/droid-{REPO_NAME}
git checkout $(git symbolic-ref refs/remotes/origin/HEAD | sed 's@^refs/remotes/origin/@@')
```

### Step 6.2: Verify All Files Created
Check that you created:
- `pr_{N}_revalidation.json` for each PR
- `revalidation_summary.json` for the repo

---

## Severity Guidelines

When verifying severity:

| Severity | Criteria |
|----------|----------|
| **critical** | Production crash, data corruption, security breach |
| **high** | Runtime error in common code paths, significant data loss |
| **medium** | Edge case errors, performance issues, partial functionality loss |
| **low** | Minor issues, code quality, documentation errors |

---

## Bug Type Guidelines

| Type | Description |
|------|-------------|
| `runtime_error` | Would raise exception (AttributeError, TypeError, KeyError, etc.) |
| `logic_bug` | Incorrect behavior, wrong results, broken logic |
| `security` | Security vulnerability, data exposure |
| `performance` | Performance degradation, inefficiency |
| `data_corruption` | Data integrity issues |
| `race_condition` | Concurrency issues |
| `documentation` | Incorrect/missing documentation |

---

## Workload by Repo

| Repo | PRs | Bugs to Verify | False Positives to Re-check |
|------|-----|----------------|----------------------------|
| sentry | 10 (PRs 6-15) | 30 | 10 |
| grafana | 10 (PRs 1-10) | 23 | 5 |
| keycloak | 10 (PRs 1-10) | 20 | 6 |
| discourse | 10 (PRs 1-10) | 36 | 5 |
| cal_dot_com | 10 (PRs 1-10) | 43 | 2 |
| **Total** | **50** | **152** | **28** |

---

## Example Session

```
User: Follow the revalidation playbook for sentry PR #6

Droid:
1. Loading draft from golden_comments_v2_draft.json...
   ✓ Found PR #6: feat(workflow_engine)...
   ✓ 4 bugs to verify, 1 false positive to re-check

2. Checking out PR #6...
   ✓ Checked out pr-6 branch
   ✓ Got diff against base branch
   
3. Verifying bug 1/4: member None AttributeError
   - File: src/sentry/api/endpoints/organization_auditlogs.py:71
   - Examining code... checking auth middleware...
   ✅ CONFIRMED: Bug is real, upgrading severity to HIGH
   
4. Verifying bug 2/4: BasePaginator negative slicing
   - File: src/sentry/api/paginator.py:186
   - Examining queryset slicing logic...
   ✅ CONFIRMED: Real bug, negative index causes AssertionError

5. Verifying bug 3/4: OptimizedCursorPaginator negative slicing
   ...
   ✅ CONFIRMED

6. Verifying bug 4/4: datetime TypeError in get_item_key
   ...
   ✅ CONFIRMED
   
7. Re-checking false positive 1/1: "Importing non-existent OptimizedCursorPaginator"
   - Searching for class definition...
   ✅ CONFIRMED FALSE POSITIVE: Class exists at line 819

8. Saving pr_6_revalidation.json...
   ✓ Saved to results/ground_truth_validation/run_2026-01-15/sentry/

9. Returning to default branch...
   ✓ Done!

Summary for PR #6:
- Bugs: 4 confirmed, 0 modified, 0 rejected
- False positives: 1 confirmed
```

---

## Ready to Start?

**To revalidate a single PR, say:**
> "Follow the revalidation playbook for {REPO_NAME} PR #{PR_NUMBER}"

**After all PRs for a repo are done, say:**
> "Generate revalidation summary for {REPO_NAME}"

---

## PR Checklist

### sentry (PRs 6-15)
- [ ] PR #6 (4 bugs, 1 FP)
- [ ] PR #7 (7 bugs, 0 FPs)
- [ ] PR #8 (2 bugs, 1 FP)
- [ ] PR #9 (3 bugs, 0 FPs)
- [ ] PR #10 (2 bugs, 1 FP)
- [ ] PR #11 (6 bugs, 1 FP)
- [ ] PR #12 (2 bugs, 2 FPs)
- [ ] PR #13 (1 bug, 1 FP)
- [ ] PR #14 (1 bug, 3 FPs)
- [ ] PR #15 (2 bugs, 0 FPs)

### grafana (PRs 1-10)
- [ ] PR #1 (4 bugs, 2 FPs)
- [ ] PR #2 (1 bug, 1 FP)
- [ ] PR #3 (2 bugs, 0 FPs)
- [ ] PR #4 (1 bug, 0 FPs)
- [ ] PR #5 (3 bugs, 0 FPs)
- [ ] PR #6 (2 bugs, 0 FPs)
- [ ] PR #7 (1 bug, 1 FP)
- [ ] PR #8 (2 bugs, 0 FPs)
- [ ] PR #9 (2 bugs, 1 FP)
- [ ] PR #10 (5 bugs, 0 FPs)

### keycloak (PRs 1-10)
- [ ] PR #1 (1 bug, 1 FP)
- [ ] PR #2 (2 bugs, 0 FPs)
- [ ] PR #3 (4 bugs, 0 FPs)
- [ ] PR #4 (4 bugs, 0 FPs)
- [ ] PR #5 (2 bugs, 0 FPs)
- [ ] PR #6 (3 bugs, 0 FPs)
- [ ] PR #7 (1 bug, 0 FPs)
- [ ] PR #8 (2 bugs, 1 FP)
- [ ] PR #9 (2 bugs, 1 FP)
- [ ] PR #10 (1 bug, 3 FPs)

### discourse (PRs 1-10)
- [ ] PR #1 (3 bugs, 0 FPs)
- [ ] PR #2 (4 bugs, 0 FPs)
- [ ] PR #3 (5 bugs, 1 FP)
- [ ] PR #4 (4 bugs, 0 FPs)
- [ ] PR #5 (3 bugs, 1 FP)
- [ ] PR #6 (2 bugs, 1 FP)
- [ ] PR #7 (4 bugs, 1 FP)
- [ ] PR #8 (4 bugs, 0 FPs)
- [ ] PR #9 (4 bugs, 0 FPs)
- [ ] PR #10 (3 bugs, 1 FP)

### cal_dot_com (PRs 1-10)
- [ ] PR #1 (5 bugs, 1 FP)
- [ ] PR #2 (5 bugs, 0 FPs)
- [ ] PR #3 (4 bugs, 0 FPs)
- [ ] PR #4 (5 bugs, 0 FPs)
- [ ] PR #5 (4 bugs, 0 FPs)
- [ ] PR #6 (4 bugs, 0 FPs)
- [ ] PR #7 (4 bugs, 0 FPs)
- [ ] PR #8 (4 bugs, 0 FPs)
- [ ] PR #9 (4 bugs, 1 FP)
- [ ] PR #10 (4 bugs, 0 FPs)
