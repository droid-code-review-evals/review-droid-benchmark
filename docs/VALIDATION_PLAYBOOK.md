# Ground Truth Validation Playbook

**Purpose:** Manually validate droid comments and golden comments against actual PR code using full Droid agent capabilities.

**Usage:** Open a Droid session and say: "Follow the validation playbook for {REPO_NAME} PR #{PR_NUMBER}"

Examples:
- "Follow the validation playbook for sentry PR #6"
- "Follow the validation playbook for grafana PR #1"
- "Follow the validation playbook for keycloak PR #5"

---

## Setup

**Repositories:**
- sentry: `/Users/user/review-droid-benchmark/work/droid-sentry` (PRs #6-15)
- grafana: `/Users/user/review-droid-benchmark/work/droid-grafana` (PRs #1-10)
- keycloak: `/Users/user/review-droid-benchmark/work/droid-keycloak` (PRs #1-10)
- discourse: `/Users/user/review-droid-benchmark/work/droid-discourse` (PRs #1-10)
- cal_dot_com: `/Users/user/review-droid-benchmark/work/droid-cal_dot_com` (PRs #1-10)

**Results Directory:** `/Users/user/review-droid-benchmark/results/run_2026-01-15/{REPO_NAME}/`

**Output Directory:** `/Users/user/review-droid-benchmark/results/ground_truth_validation/run_2026-01-15/{REPO_NAME}/`

**Note:** Replace `{REPO_NAME}` with: sentry, grafana, keycloak, discourse, or cal_dot_com

---

## Bug Counting & Deduplication Rules

When counting bugs for metrics calculation:

1. **Count by required fixes**: Same bug pattern in different locations = separate bugs (each needs its own fix)
2. **No location specificity required for credit**: A vague golden comment like "negative slicing issue" can get credit for all instances of that bug type in the PR
3. **Golden can have false positives**: Treat golden as fallible, not as perfect ground truth

**Example:**
- PR has negative slicing bug in `BasePaginator` (line 186) AND `OptimizedCursorPaginator` (line 877)
- These count as **2 bugs** (separate fixes needed)
- A single golden comment "Django querysets do not support negative slicing" gets credit for **both**
- Droid comments pointing to each specific location also each get credit

---

## Part 1: Checkout PR and Prepare

### Step 1.1: Navigate to Repository
```bash
cd /Users/user/review-droid-benchmark/work/droid-{REPO_NAME}
```
Replace `{REPO_NAME}` with: sentry, grafana, keycloak, discourse, or cal_dot_com

### Step 1.2: Get PR Base Branch and Checkout
```bash
# Get PR's actual base branch (not always master/main!)
BASE_BRANCH=$(gh pr view {PR_NUMBER} --json baseRefName --jq '.baseRefName')

# Fetch the base branch
git fetch origin $BASE_BRANCH

# Fetch PR (replace {PR_NUMBER} with actual number)
git fetch origin pull/{PR_NUMBER}/head:pr-{PR_NUMBER}

# Checkout PR branch
git checkout pr-{PR_NUMBER}

# Verify you're on the right branch
git branch --show-current
git log --oneline -1
```

### Step 1.3: Get PR Diff
```bash
# Get full diff against the PR's base branch
git diff origin/$BASE_BRANCH...HEAD

# List changed files
git diff --name-status origin/$BASE_BRANCH...HEAD
```

---

## Part 2: Validate Droid Comments

### Step 2.1: Load Droid Comments
Load from: `/Users/user/review-droid-benchmark/results/run_2026-01-15/{REPO_NAME}/pr_{PR_NUMBER}_comments.json`

Each comment has:
- `id`: Comment ID
- `path`: File path
- `line`: Line number
- `body`: Comment text
- `diff_hunk`: Code snippet

### Step 2.2: Validate Each Droid Comment

**For each droid comment, perform the following analysis:**

#### A. Locate the Code
1. Navigate to the file: `{path}`
2. Go to line: `{line}`
3. Read the full file (not just the diff hunk)
4. Understand the function/class context
5. Check imports and dependencies
6. Look for related code in other files if needed

#### B. Analyze the Issue
Ask yourself:
1. **Is this a real bug?**
   - Would it cause a runtime error (AttributeError, TypeError, KeyError, etc.)?
   - Would it cause incorrect behavior or logic bugs?
   - Are there performance/security implications?

2. **What's the severity?**
   - Critical: Production crash, data corruption
   - High: Runtime error in common code paths
   - Medium: Edge case errors, performance issues
   - Low: Code quality, potential future issues
   - None: False positive

3. **What's your confidence?**
   - High: You're certain after exploring the code
   - Medium: Likely but need more context
   - Low: Uncertain or ambiguous

4. **What type of bug?**
   - runtime_error
   - logic_bug
   - performance
   - security
   - false_positive
   - unclear

#### C. Document Your Analysis
Create a validation entry:

```json
{
  "comment_id": 2695944051,
  "file": "src/sentry/api/endpoints/organization_auditlogs.py",
  "line": 71,
  "droid_comment": "[Full comment text]",
  "validation": {
    "is_valid_bug": true,
    "confidence": "high",
    "severity": "high",
    "bug_type": "runtime_error",
    "impact": "Would raise AttributeError when organization_context.member is None for API key authentication",
    "reasoning": "Explored the code: organization_context.member can be None for requests authenticated with API keys (no user_id). Line 71 directly accesses .has_global_access without checking if member exists. This will crash when optimized_pagination=true is used with API key auth.",
    "code_evidence": "Lines 70-71 show the issue. Verified by checking auth middleware in src/sentry/api/authentication.py where member can be set to None for org-level auth tokens.",
    "files_explored": [
      "src/sentry/api/endpoints/organization_auditlogs.py",
      "src/sentry/api/authentication.py"
    ]
  }
}
```

### Step 2.3: Save Droid Validation Results
Save all droid validations to:
`/Users/user/review-droid-benchmark/results/ground_truth_validation/run_2026-01-15/{REPO_NAME}/pr_{PR_NUMBER}_droid_validations.json`

Format:
```json
[
  { validation entry 1 },
  { validation entry 2 },
  ...
]
```

---

## Part 3: Audit Golden Comments

### Step 3.1: Load Golden Comments
Load from: `/Users/user/review-droid-benchmark/results/run_2026-01-15/{REPO_NAME}/golden_comments.json`

Find the entry matching this PR number in the golden comments file.

### Step 3.2: Audit Each Golden Comment

**For each golden comment, perform the following analysis:**

#### A. Find the Bug in Code
1. Read the golden comment
2. Search the PR diff for this issue
3. Try to locate the exact file and line
4. Explore the codebase to understand the issue

#### B. Evaluate Quality

**1. Is this a real bug?**
- Yes: Verified in code, would cause real problems
- No: Not actually a bug, false alarm
- Confidence: high/medium/low

**2. Rate Specificity (1-5):**
- 5: Has exact file, line number, variable names
- 4: Has file and general area
- 3: Has file but no line details
- 2: Describes bug but no location
- 1: Completely vague, no actionable info

**3. Rate Clarity (1-5):**
- 5: Crystal clear what the bug is, no ambiguity
- 4: Clear but could be slightly more specific
- 3: Understandable but some interpretation needed
- 2: Vague, could mean multiple things
- 1: Unclear what bug is being described

**4. Bug Location:**
- If found: `{"file": "path/to/file.py", "line": 123}`
- If not found: `null`

**5. Match with Droid:**
- Did droid catch this bug?
- If yes, which droid comment ID?

#### C. Document Your Audit
Create an audit entry:

```json
{
  "golden_comment": "Django querysets do not support negative slicing",
  "severity": "High",
  "audit": {
    "is_real_bug": true,
    "confidence": "high",
    "bug_location": {
      "file": "src/sentry/api/paginator.py",
      "line": 186
    },
    "is_specific": false,
    "is_clear": true,
    "clarity_score": 4,
    "specificity_score": 2,
    "matched_by_droid": true,
    "droid_comment_id": 2695944394,
    "missing_details": [
      "file path",
      "line number",
      "which paginator class (there are 2 affected)"
    ],
    "vagueness_issues": [
      "Could apply to multiple locations in the PR"
    ],
    "code_evidence": "Found in BasePaginator.get_result() at line 186: queryset[start_offset:stop] where start_offset can be negative when cursor.is_prev=True",
    "reasoning": "Real bug confirmed. Golden comment is clear about the issue (negative slicing) but lacks file/line specificity. Found it by searching for QuerySet slicing in changed files. Droid caught the exact same bug with more specific file/line info.",
    "files_explored": [
      "src/sentry/api/paginator.py"
    ]
  }
}
```

### Step 3.3: Save Golden Audit Results
Save all golden audits to:
`/Users/user/review-droid-benchmark/results/ground_truth_validation/run_2026-01-15/{REPO_NAME}/pr_{PR_NUMBER}_golden_audits.json`

Format:
```json
[
  { audit entry 1 },
  { audit entry 2 },
  ...
]
```

---

## Part 4: Ground Truth & Metrics Calculation

### Step 4.1: Establish Ground Truth Bug List
After validating both droid and golden comments, compile the **true list of unique bugs** in this PR:
- Include all validated droid bugs (is_valid_bug=true, confidence=high/medium)
- Include all validated golden bugs (is_real_bug=true, confidence=high/medium)
- Deduplicate: if droid and golden describe the same bug, count it once
- Remember: same pattern in different locations = separate bugs

### Step 4.2: Calculate Precision & Recall

**For Droid:**
```
droid_precision = valid_droid_comments / total_droid_comments
droid_recall = bugs_found_by_droid / total_ground_truth_bugs
droid_f1 = 2 * (precision * recall) / (precision + recall)
```

**For Golden:**
```
golden_precision = valid_golden_comments / total_golden_comments
golden_recall = bugs_found_by_golden / total_ground_truth_bugs
golden_f1 = 2 * (precision * recall) / (precision + recall)
```

**Note:** A single comment can cover multiple bugs (e.g., "negative slicing" covers 2 locations), which affects recall but not precision.

### Step 4.3: Identify Coverage Gaps
- **Droid missed**: Bugs found only by golden
- **Golden missed**: Bugs found only by droid
- **Golden false positives**: Golden comments that aren't real bugs

### Step 4.4: Save Analysis
Save to:
`/Users/user/review-droid-benchmark/results/ground_truth_validation/run_2026-01-15/{REPO_NAME}/pr_{PR_NUMBER}_completeness.json`

Format:
```json
{
  "pr_number": 6,
  "ground_truth_bugs": [
    {"id": 1, "description": "member None AttributeError", "file": "...", "line": 71},
    {"id": 2, "description": "BasePaginator negative slicing", "file": "...", "line": 186},
    {"id": 3, "description": "OptimizedCursorPaginator negative slicing", "file": "...", "line": 877},
    {"id": 4, "description": "datetime TypeError in get_item_key", "file": "...", "line": 838}
  ],
  "droid_metrics": {
    "total_comments": 3,
    "valid_comments": 3,
    "bugs_found": [1, 2, 3],
    "precision": 1.0,
    "recall": 0.75,
    "f1": 0.857
  },
  "golden_metrics": {
    "total_comments": 4,
    "valid_comments": 3,
    "bugs_found": [1, 2, 3, 4],
    "precision": 0.75,
    "recall": 1.0,
    "f1": 0.857
  },
  "golden_false_positives": [
    {
      "golden_comment": "Comment text",
      "reasoning": "Why it's not a real bug"
    }
  ],
  "droid_missed": [4],
  "golden_missed": []
}
```

---

## Part 5: Generate PR Summary

### Step 5.1: Compile Final Summary
Combine all analysis into a final summary with:
- Ground truth bug count
- Precision, Recall, F1 for both droid and golden
- Coverage gaps (what each missed)
- Quality scores for golden (clarity, specificity)

### Step 5.2: Save PR Summary
Save to:
`/Users/user/review-droid-benchmark/results/ground_truth_validation/run_2026-01-15/{REPO_NAME}/pr_{PR_NUMBER}_summary.json`

Format:
```json
{
  "pr_number": 6,
  "pr_title": "Enhanced Pagination Performance for High-Volume Audit Logs",
  "ground_truth_bug_count": 4,
  "droid_analysis": {
    "total_comments": 3,
    "true_positives": 3,
    "false_positives": 0,
    "precision": 1.0,
    "recall": 0.75,
    "f1": 0.857
  },
  "golden_analysis": {
    "total_comments": 4,
    "true_positives": 3,
    "false_positives": 1,
    "precision": 0.75,
    "recall": 1.0,
    "f1": 0.857,
    "avg_clarity_score": 4.5,
    "avg_specificity_score": 3.0
  },
  "coverage": {
    "bugs_found_by_both": 3,
    "bugs_found_only_by_droid": 0,
    "bugs_found_only_by_golden": 1,
    "droid_missed": ["datetime TypeError in get_item_key"],
    "golden_missed": []
  }
}
```

---

## Part 6: Cleanup

### Step 6.1: Return to Base Branch
```bash
cd /Users/user/review-droid-benchmark/work/droid-{REPO_NAME}
# Return to whatever branch you were on, or the repo's default
git checkout $(git symbolic-ref refs/remotes/origin/HEAD | sed 's@^refs/remotes/origin/@@')
```

### Step 6.2: Verify All Files Saved
Check that you created:
- `pr_{PR_NUMBER}_droid_validations.json`
- `pr_{PR_NUMBER}_golden_audits.json`
- `pr_{PR_NUMBER}_completeness.json`
- `pr_{PR_NUMBER}_summary.json`

---

## Tips for Effective Validation

### Code Exploration Best Practices
1. **Don't trust the diff hunk alone** - read the full file
2. **Follow imports** - check where classes/functions come from
3. **Check related files** - authentication, middleware, config
4. **Search for patterns** - use grep to find similar code
5. **Test your hypothesis** - mentally trace execution paths
6. **Be thorough** - explore until you're confident

### Common Pitfalls to Avoid
1. **Surface-level analysis** - go deeper than just the changed lines
2. **Assuming context** - verify your assumptions by checking code
3. **Missing edge cases** - think about when assumptions break
4. **Over-reliance on comments** - trust the code, not just descriptions

### What Makes a Real Bug?
✅ **Real bugs:**
- Would raise exceptions in production
- Would cause incorrect behavior
- Would create security vulnerabilities
- Would cause performance degradation

❌ **False positives:**
- Overly defensive concerns
- Hypothetical scenarios that can't happen
- Misunderstanding of the code
- Style/preference issues without real impact

---

## Example Session

```
User: Follow the validation playbook for sentry PR #6

Droid:
1. Checking out sentry PR #6...
   ✓ Navigated to droid-sentry repository
   ✓ Fetched and checked out pr-6 branch
   
2. Loading droid comments...
   ✓ Found 3 droid comments from sentry/pr_6_comments.json
   
3. Validating droid comment 1/3:
   - File: src/sentry/api/endpoints/organization_auditlogs.py:71
   - Comment: "organization_context.member can be None"
   - Exploring code...
   [Reads file, checks auth middleware, traces execution]
   - ✅ REAL BUG: Confirmed AttributeError when member=None
   - Confidence: HIGH, Severity: HIGH
   
... [continues for all comments]

4. Auditing golden comments...
   ✓ Found 4 golden comments
   
... [continues validation process]

5. Completeness analysis:
   - Golden missed: 1 bug
   - Golden false positives: 0
   - Completeness score: 75%
   
6. Saved all results to ground_truth_validation/run_2026-01-15/sentry/
   ✓ Done! Returning to main branch.
```

---

## Ready to Start?

**To validate a PR, say:**
> "Follow the validation playbook for {REPO_NAME} PR #{PR_NUMBER}"

**Examples:**
- "Follow the validation playbook for sentry PR #6"
- "Follow the validation playbook for grafana PR #1"
- "Follow the validation playbook for keycloak PR #5"

**For parallel validation across all 50 PRs:**
Open multiple Droid sessions and assign PRs to each:
- Sentry: PRs #6-15 (10 PRs)
- Grafana: PRs #1-10 (10 PRs)
- Keycloak: PRs #1-10 (10 PRs)
- Discourse: PRs #1-10 (10 PRs)
- Cal.com: PRs #1-10 (10 PRs)
