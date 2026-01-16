# Eval Loop Design: Automated Benchmarking for Review Droid

## Overview

This document captures design ideas for setting up an automated evaluation loop to benchmark Review Droid against the `ai-code-review-evaluations` dataset (50 PRs across 5 repos: sentry, grafana, keycloak, discourse, cal.com).

The goal is to calculate metrics comparable to Augment's blog post:
- **True Positives (TP)**: Droid comments that match a golden comment
- **False Positives (FP)**: Droid comments that don't match any golden comment
- **False Negatives (FN)**: Golden comments that Droid missed
- **Precision**: TP / (TP + FP) - How trustworthy the tool is
- **Recall**: TP / (TP + FN) - How comprehensive it is
- **F-score**: 2 * (Precision * Recall) / (Precision + Recall) - Overall quality

---

## Current Architecture Understanding

### droid-action Overview

The `droid-action` GitHub Action:
1. Triggers on `@droid review` comments (or automatic review on PR open)
2. Checks out the PR branch
3. Generates a review prompt with context (PR diff, base branch, etc.)
4. Runs Droid CLI with MCP tools for GitHub interaction
5. Posts inline comments via `github_inline_comment___create_inline_comment`
6. Submits reviews via `github_pr___submit_review`

### Review Output Format

Droid posts:
- Inline PR review comments (on specific lines) with format:
  ```
  **[P0/P1] Clear title (≤ 80 chars, imperative mood)**
  
  Explanation of why this is a problem (1 paragraph max).
  ```
- A summary comment/review body

### Golden Comments Format

From `ai-code-review-evaluations/golden_comments`:
```json
{
  "pr_title": "Anonymous: Add configurable device limit",
  "comments": [
    {
      "comment": "Race condition: Multiple concurrent requests could pass the device count check...",
      "severity": "High"
    }
  ]
}
```

---

## Key Challenges

### 1. Semantic Matching

Golden comments are natural language descriptions of bugs. Droid's output will use different wording. Need semantic similarity matching (likely LLM-based).

### 2. Severity Mapping

| Golden Severity | Droid Priority |
|-----------------|----------------|
| High            | P0, P1         |
| Medium          | P1, P2         |
| Low             | P2, P3         |

Note: Droid's prompt says "Only post P0 and P1 findings as inline comments. Do NOT post P2 or P3 findings." This means Low severity golden comments may intentionally not be flagged.

### 3. Comment Extraction

Need to programmatically fetch all review comments Droid posted on a PR using GitHub API.

### 4. Triggering at Scale

Running 50 PRs sequentially with `@droid review` is slow (~2-5 min each = 100-250 min total). Need parallel or batch approach.

### 5. Version Pinning

When testing a dev branch, need to ensure the droid-action uses that specific version, not `@v1`.

---

## When Should Eval Run?

### Problem with Post-Merge Eval

If eval only runs after merging to dev, you lose the ability to catch regressions before they land.

### Preferred: Pre-Merge Eval

Eval should run on **any PR to dev** (or on-demand) to validate changes before merge.

---

## Proposed Architecture Options

### Option 1: Dynamic Action Reference in Benchmark Repos

Update benchmark repos' `droid.yml` to accept the droid-action ref as a workflow input:

```yaml
# In droid-code-review-evals/droid-*/droid.yml
name: Droid Review (Eval)

on:
  workflow_dispatch:
    inputs:
      droid_action_ref:
        description: 'Branch/tag/SHA of droid-action to test'
        required: true
        default: 'v1'

jobs:
  review:
    runs-on: ubuntu-latest
    permissions:
      contents: write
      pull-requests: write
      issues: write
      id-token: write
      actions: read
    steps:
      - name: Checkout repository
        uses: actions/checkout@v5
        with:
          fetch-depth: 1

      - name: Run Droid Review
        uses: Factory-AI/droid-action@${{ inputs.droid_action_ref }}
        with:
          factory_api_key: ${{ secrets.FACTORY_API_KEY }}
          automatic_review: true
```

Trigger with:
```bash
gh workflow run droid.yml -R droid-code-review-evals/droid-sentry \
  -f droid_action_ref=my-feature-branch
```

**Pros:**
- Simple to implement
- Each benchmark repo controls its own workflow

**Cons:**
- Need to update all 5 benchmark repos
- Orchestration logic lives outside droid-action

### Option 2: Eval Workflow in droid-action Repo

Add a workflow in `droid-action/.github/workflows/eval.yml` that:
1. Triggers on PR to dev (or manual dispatch)
2. Uses the **current PR's branch** as the action ref
3. Dispatches review runs to the benchmark repos with that ref
4. Collects results and posts back to the PR

```yaml
# In droid-action/.github/workflows/eval.yml
name: Benchmark Evaluation

on:
  pull_request:
    branches: [dev, main]
  workflow_dispatch:
    inputs:
      run_full_eval:
        description: 'Run full 50 PR eval (vs quick 10 PR subset)'
        type: boolean
        default: false

jobs:
  trigger-benchmarks:
    runs-on: ubuntu-latest
    steps:
      - name: Get PR branch ref
        id: ref
        run: echo "ref=${{ github.head_ref || github.ref_name }}" >> $GITHUB_OUTPUT
      
      - name: Trigger benchmark reviews
        run: |
          REPOS="droid-sentry droid-grafana droid-keycloak droid-discourse droid-cal_dot_com"
          for repo in $REPOS; do
            gh workflow run eval.yml -R droid-code-review-evals/$repo \
              -f droid_action_ref=${{ steps.ref.outputs.ref }}
          done
        env:
          GH_TOKEN: ${{ secrets.EVAL_DISPATCH_TOKEN }}
      
      - name: Wait for completions
        run: |
          # Poll workflow runs until all complete
          # ...
      
      - name: Collect results
        run: |
          # Fetch review comments from all benchmark PRs
          # ...
      
      - name: Evaluate against golden comments
        run: |
          # Run semantic matching
          # Calculate TP/FP/FN/precision/recall/F-score
          # ...
      
      - name: Post results to PR
        run: |
          # Create comment with metrics table
          # ...
```

**Pros:**
- Eval runs as part of PR CI in droid-action
- Results posted directly to the PR being tested
- Single source of truth for eval logic

**Cons:**
- Requires cross-repo workflow dispatch (needs PAT with appropriate permissions)
- More complex orchestration

### Option 3: Self-Contained Eval (No External Triggers)

Run the eval entirely within the droid-action PR's CI:
1. Check out benchmark repo code locally (or use cached clones)
2. Run the review logic directly (not via GitHub Action trigger)
3. Mock the GitHub API or use a test environment
4. Compare output to golden comments
5. Report results

**Pros:**
- No cross-repo dependencies
- Faster iteration (no workflow dispatch latency)
- Can run locally for development

**Cons:**
- Requires refactoring to make review logic callable outside GitHub Actions
- May not catch integration issues with real GitHub API
- Doesn't test the full action execution path

---

## Proposed Eval Loop Flow

```
┌─────────────────────────────────────────────────────────────────┐
│              CI Workflow (on PR to dev or manual)               │
├─────────────────────────────────────────────────────────────────┤
│  1. Determine droid-action ref to test                          │
│     - PR branch for pull_request events                         │
│     - Input parameter for workflow_dispatch                     │
│                                                                 │
│  2. For each of 50 benchmark PRs (parallel batches):            │
│     a. Trigger review workflow with specific action ref         │
│     b. Wait for completion (poll workflow status)               │
│     c. Fetch resulting review comments via GitHub API           │
│                                                                 │
│  3. Collect all review outputs                                  │
│     - PR number → list of comments (text + file + line)         │
│                                                                 │
│  4. Run evaluation script:                                      │
│     - Load golden_comments for each PR                          │
│     - Use LLM to semantically match Droid comments to golden    │
│     - Classify: TP, FP, FN                                      │
│     - Calculate metrics: precision, recall, F-score             │
│                                                                 │
│  5. Generate report                                             │
│     - Post as PR comment (for PR events)                        │
│     - Save as CI artifact                                       │
│     - Update tracking spreadsheet/dashboard (optional)          │
└─────────────────────────────────────────────────────────────────┘
```

---

## Components Needed

### 1. Eval Trigger Script

`scripts/trigger-eval.sh` or `scripts/trigger-eval.ts`

- Takes droid-action branch/SHA as input
- Triggers reviews on all 50 PRs (or configurable subset)
- Uses `gh api` to dispatch workflows or post `@droid review` comments
- Handles parallelization (batch by repo)

### 2. Comment Collector

`scripts/collect-comments.ts`

- Fetches all review comments from each benchmark PR
- Filters to only Droid-authored comments (by bot username or comment pattern)
- Outputs structured JSON:
  ```json
  {
    "repo": "droid-sentry",
    "pr_number": 6,
    "pr_title": "Enhanced Pagination Performance...",
    "comments": [
      {
        "id": 123456,
        "body": "**[P1] Race condition in device limit check**\n\nMultiple concurrent...",
        "path": "src/auth/device.go",
        "line": 42,
        "created_at": "2026-01-13T..."
      }
    ]
  }
  ```

### 3. Semantic Matcher

`scripts/evaluate.ts`

- Loads golden comments from `repos/golden_comments/code_review_benchmarks/*.json`
- For each Droid comment, uses LLM to determine if it matches any golden comment
- Handles severity mapping
- Outputs TP/FP/FN classifications:
  ```json
  {
    "repo": "droid-sentry",
    "pr_title": "...",
    "true_positives": [
      { "droid_comment": "...", "golden_comment": "...", "confidence": 0.95 }
    ],
    "false_positives": [
      { "droid_comment": "...", "reason": "No matching golden comment" }
    ],
    "false_negatives": [
      { "golden_comment": "...", "severity": "High" }
    ]
  }
  ```

### 4. Metrics Calculator

`scripts/metrics.ts`

- Aggregates TP/FP/FN across all PRs
- Calculates precision, recall, F-score (overall and per-severity)
- Generates markdown report:
  ```markdown
  ## Benchmark Results
  
  | Metric    | Value |
  |-----------|-------|
  | Precision | 65%   |
  | Recall    | 55%   |
  | F-score   | 59%   |
  
  ### By Severity
  | Severity | TP | FP | FN | Precision | Recall |
  |----------|----|----|----| ----------|--------|
  | High     | 20 | 5  | 8  | 80%       | 71%    |
  | Medium   | 15 | 10 | 12 | 60%       | 56%    |
  | Low      | 5  | 15 | 20 | 25%       | 20%    |
  ```

### 5. CI Workflow

`.github/workflows/eval.yml` (in droid-action repo)

- Triggered on PR to dev or manual dispatch
- Orchestrates the full eval loop
- Posts results as PR comment

---

## Semantic Matching Approaches

### Approach A: LLM-as-Judge (Recommended)

Use an LLM to determine if a Droid comment semantically matches a golden comment.

```
Prompt:
You are evaluating whether a code review comment matches an expected finding.

Expected finding (golden):
"Race condition: Multiple concurrent requests could pass the device count check simultaneously and create devices beyond the limit."

Actual comment from reviewer:
"**[P1] Potential race condition in device limit enforcement**
Multiple requests hitting this endpoint simultaneously could bypass the limit check since the count query and insert are not atomic."

Do these describe the same issue? Answer YES or NO, then explain briefly.
```

**Pros:**
- High accuracy for semantic similarity
- Handles paraphrasing well

**Cons:**
- Cost per comparison (~$0.01-0.05 per match check)
- 50 PRs × ~5 golden comments × ~5 droid comments = ~1250 comparisons = ~$12-60 per full eval

### Approach B: Embedding Similarity

Use embeddings (e.g., OpenAI ada-002, or open-source) to compute vector similarity.

```python
golden_embedding = embed(golden_comment)
droid_embedding = embed(droid_comment)
similarity = cosine_similarity(golden_embedding, droid_embedding)
if similarity > 0.85:
    return MATCH
```

**Pros:**
- Much cheaper (~$0.0001 per embedding)
- Faster

**Cons:**
- May miss semantic matches with different phrasing
- Requires tuning threshold

### Approach C: Hybrid

1. First pass: Use embeddings to filter candidate matches (similarity > 0.7)
2. Second pass: Use LLM to confirm/reject candidates

**Pros:**
- Balances cost and accuracy
- Reduces LLM calls significantly

---

## Parallelization Strategy

### By Repository (Recommended)

Run all 5 repos in parallel, each processing its 10 PRs sequentially:
- 5 parallel jobs × 10 sequential PRs × ~3 min = ~30 min total

### By PR

Run all 50 PRs in parallel:
- May hit GitHub rate limits
- May overwhelm Droid API
- Not recommended

### Batched

Run in batches of 10 PRs:
- 5 batches × ~15 min = ~75 min total
- Good balance of speed and resource usage

---

## Open Questions

1. **Where should eval results be stored long-term?**
   - Git repo (versioned markdown reports)?
   - Database/spreadsheet for trend tracking?
   - Dashboard (e.g., Grafana)?

2. **Should we support partial eval (subset of PRs)?**
   - Useful for quick iteration during development
   - Could run 1 PR per repo (5 total) for ~5 min smoke test

3. **How to handle flaky results?**
   - LLM outputs can vary slightly between runs
   - May need to run multiple times and average
   - Or use temperature=0 for determinism

4. **What's the acceptable eval cost budget?**
   - Full eval with LLM matching: ~$20-100 per run
   - Embedding-only: ~$1 per run
   - Hybrid: ~$5-10 per run

5. **Should eval block PR merge?**
   - Strict: Block if F-score drops below threshold
   - Advisory: Post results but don't block
   - Graduated: Block for large regressions only

---

## Next Steps

1. [ ] Decide on trigger mechanism (Option 1, 2, or 3)
2. [ ] Implement comment collector script
3. [ ] Implement semantic matcher (start with LLM-as-judge)
4. [ ] Implement metrics calculator
5. [ ] Set up CI workflow
6. [ ] Run first full eval and establish baseline metrics
7. [ ] Iterate on prompt/matching to improve accuracy

---

## References

- [Augment Blog Post](https://www.augmentcode.com/blog/we-benchmarked-7-ai-code-review-tools-on-real-world-prs-here-are-the-results)
- [ai-code-review-evaluations GitHub Org](https://github.com/ai-code-review-evaluations)
- [golden_comments Repo](https://github.com/ai-code-review-evaluations/golden_comments)
- [droid-action Repo](https://github.com/Factory-AI/droid-action)
- [droid-code-review-evals Org](https://github.com/droid-code-review-evals)
