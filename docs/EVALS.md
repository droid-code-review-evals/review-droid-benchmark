# Running Evaluations

Guide for running Droid code review evaluations against the benchmark PRs.

## Overview

The evaluation process:
1. Triggers Droid reviews on benchmark PRs
2. Fetches Droid's comments
3. Compares against golden comments using LLM-as-judge
4. Calculates precision, recall, and F-score

### Metrics Definitions

| Metric | Definition |
|--------|------------|
| **True Positive (TP)** | Droid comment semantically matches a golden comment |
| **False Positive (FP)** | Droid comment doesn't match any golden comment |
| **False Negative (FN)** | Golden comment that Droid missed |
| **Precision** | TP / (TP + FP) - "Of what Droid flagged, how much was correct?" |
| **Recall** | TP / (TP + FN) - "Of what should have been flagged, how much did Droid catch?" |
| **F-Score** | 2 × (Precision × Recall) / (Precision + Recall) |

---

## Prerequisites

### Python Environment (one-time setup)

```bash
cd ~/review-droid-benchmark
python3 -m venv venv
source venv/bin/activate
pip install anthropic
```

### API Key

```bash
export ANTHROPIC_API_KEY="sk-ant-api03-..."
```

---

## Single Repo Evaluation (droid-sentry)

Recommended for quick iteration. Evaluates PRs #6-15.

### Quick Reference: Complete Workflow

```bash
# 1. Set run name
RUN_NAME="run_$(date +%Y-%m-%d)"

# 2. Reset PRs (clear old comments)
export GH_PAGER=""
for pr in 6 7 8 9 10 11 12 13 14 15; do
  for cid in $(gh api repos/droid-code-review-evals/droid-sentry/pulls/$pr/comments --jq '.[] | select(.user.login == "factory-droid[bot]") | .id'); do
    gh api -X DELETE repos/droid-code-review-evals/droid-sentry/pulls/comments/$cid 2>/dev/null
  done
  for rid in $(gh api repos/droid-code-review-evals/droid-sentry/pulls/$pr/reviews --jq '.[] | select(.user.login == "factory-droid[bot]") | .id'); do
    gh api -X PUT repos/droid-code-review-evals/droid-sentry/pulls/$pr/reviews/$rid -f body="." >/dev/null 2>&1
  done
  for cid in $(gh api repos/droid-code-review-evals/droid-sentry/issues/$pr/comments --jq '.[] | select(.user.login == "factory-droid[bot]" or .user.login == "varin-nair-factory") | .id'); do
    gh api -X DELETE repos/droid-code-review-evals/droid-sentry/issues/comments/$cid 2>/dev/null
  done
done

# 3. Trigger reviews
for pr in 6 7 8 9 10 11 12 13 14 15; do
  gh pr comment $pr --repo droid-code-review-evals/droid-sentry --body "@droid review"
done

# 4. Wait for reviews to complete (monitor with gh run list)
gh run list --repo droid-code-review-evals/droid-sentry --limit 20

# 5. Fetch comments
mkdir -p ~/review-droid-benchmark/results/${RUN_NAME}/raw_comments
for pr in 6 7 8 9 10 11 12 13 14 15; do
  gh api repos/droid-code-review-evals/droid-sentry/pulls/$pr/comments > \
    ~/review-droid-benchmark/results/${RUN_NAME}/pr_${pr}_comments.json
done
cp ~/review-droid-benchmark/repos/golden_comments/code_review_benchmarks/sentry.json \
   ~/review-droid-benchmark/results/${RUN_NAME}/golden_comments.json

# 6. Transform to evaluation format
cp ~/review-droid-benchmark/results/run_2026-01-14/transform_comments.py \
   ~/review-droid-benchmark/results/${RUN_NAME}/
cd ~/review-droid-benchmark/results/${RUN_NAME}
python3 transform_comments.py
mkdir -p raw_comments
cp golden_comments.json raw_comments/golden_sentry.json

# 7. Run evaluation
cd ~/review-droid-benchmark
source venv/bin/activate
export ANTHROPIC_API_KEY="sk-ant-api03-..."
python3 scripts/evaluate_sentry_run.py ${RUN_NAME}

# 8. Generate documentation
python3 scripts/generate_results_markdown.py ${RUN_NAME}
# Or with baseline comparison:
python3 scripts/generate_results_markdown.py ${RUN_NAME} run_2026-01-14

# 9. View results
cat results/${RUN_NAME}/RESULTS.md
```

### Detailed Steps

#### Step 1: Reset PRs

Clear all existing Droid comments for a fresh evaluation:

```bash
export GH_PAGER=""
for pr in 6 7 8 9 10 11 12 13 14 15; do
  echo "=== Processing PR #$pr ==="
  for cid in $(gh api repos/droid-code-review-evals/droid-sentry/pulls/$pr/comments --jq '.[] | select(.user.login == "factory-droid[bot]") | .id'); do
    echo "Deleting PR comment $cid"
    gh api -X DELETE repos/droid-code-review-evals/droid-sentry/pulls/comments/$cid 2>/dev/null
  done
  for rid in $(gh api repos/droid-code-review-evals/droid-sentry/pulls/$pr/reviews --jq '.[] | select(.user.login == "factory-droid[bot]") | .id'); do
    echo "Updating review $rid"
    gh api -X PUT repos/droid-code-review-evals/droid-sentry/pulls/$pr/reviews/$rid -f body="." >/dev/null 2>&1
  done
  for cid in $(gh api repos/droid-code-review-evals/droid-sentry/issues/$pr/comments --jq '.[] | select(.user.login == "factory-droid[bot]" or .user.login == "varin-nair-factory") | .id'); do
    echo "Deleting issue comment $cid"
    gh api -X DELETE repos/droid-code-review-evals/droid-sentry/issues/comments/$cid 2>/dev/null
  done
  echo "Completed PR #$pr"
done
```

#### Step 2: Trigger Reviews

```bash
for pr in 6 7 8 9 10 11 12 13 14 15; do
  gh pr comment $pr --repo droid-code-review-evals/droid-sentry --body "@droid review"
  echo "Triggered droid-sentry PR #$pr"
  sleep 2
done
```

#### Step 3: Wait for Completion

Monitor workflow runs:

```bash
gh run list --repo droid-code-review-evals/droid-sentry --limit 20
```

#### Step 4: Run Evaluation

```bash
cd ~/review-droid-benchmark
source venv/bin/activate
export ANTHROPIC_API_KEY="sk-ant-api03-..."

RUN_NAME="run_$(date +%Y-%m-%d)"
python3 scripts/evaluate_sentry_run.py ${RUN_NAME}
```

Output: `results/${RUN_NAME}/sentry_eval.json` with:
- Per-PR metrics (TP, FP, FN, precision, recall, F-score)
- Overall summary metrics
- Full evaluation details for each comment

#### Step 5: Generate Documentation

```bash
python3 scripts/generate_results_markdown.py ${RUN_NAME}
# Or compare against baseline:
python3 scripts/generate_results_markdown.py ${RUN_NAME} run_2026-01-14
```

Generates:
- `RESULTS.md` - Detailed per-PR breakdown with metrics
- `README.md` - Run overview and configuration notes

---

## Full Evaluation (All 5 Repos)

Evaluates all 50 PRs across 5 repositories.

### Step 1: Trigger Reviews on All Repos

```bash
# droid-sentry (PRs #6-15)
for pr in 6 7 8 9 10 11 12 13 14 15; do
  gh pr comment $pr -R droid-code-review-evals/droid-sentry -b "@droid review"
done

# droid-grafana (PRs #1-10)
for pr in 1 2 3 4 5 6 7 8 9 10; do
  gh pr comment $pr -R droid-code-review-evals/droid-grafana -b "@droid review"
done

# droid-keycloak (PRs #1-10)
for pr in 1 2 3 4 5 6 7 8 9 10; do
  gh pr comment $pr -R droid-code-review-evals/droid-keycloak -b "@droid review"
done

# droid-discourse (PRs #1-10)
for pr in 1 2 3 4 5 6 7 8 9 10; do
  gh pr comment $pr -R droid-code-review-evals/droid-discourse -b "@droid review"
done

# droid-cal_dot_com (PRs #1-10)
for pr in 1 2 3 4 5 6 7 8 9 10; do
  gh pr comment $pr -R droid-code-review-evals/droid-cal_dot_com -b "@droid review"
done
```

Wait for all reviews to complete before proceeding.

### Step 2: Fetch Comments from All Repos

```bash
RUN_NAME="run_$(date +%Y-%m-%d)"
mkdir -p ~/review-droid-benchmark/results/${RUN_NAME}/raw_comments

for REPO_NAME in droid-sentry droid-grafana droid-keycloak droid-discourse droid-cal_dot_com; do
  # Determine PR range based on repo
  if [ "$REPO_NAME" = "droid-sentry" ]; then
    PR_START=6; PR_END=15
  else
    PR_START=1; PR_END=10
  fi

  REPO="droid-code-review-evals/${REPO_NAME}"
  OUTPUT_FILE="$HOME/review-droid-benchmark/results/${RUN_NAME}/raw_comments/${REPO_NAME}.json"

  echo "Fetching $REPO_NAME..."

  (
    echo "{"
    echo "  \"repo\": \"${REPO_NAME}\","
    echo "  \"fetched_at\": \"$(date -u +%Y-%m-%dT%H:%M:%SZ)\","
    echo "  \"prs\": ["

    FIRST_PR=true
    for pr in $(seq $PR_START $PR_END); do
      if [ "$FIRST_PR" = true ]; then
        FIRST_PR=false
      else
        echo "    ,"
      fi

      PR_TITLE=$(gh pr view $pr -R $REPO --json title --jq '.title')
      ISSUE_COMMENTS=$(gh api repos/$REPO/issues/$pr/comments --paginate --jq '[.[] | select(.user.login == "factory-droid[bot]") | {id: .id, body: .body, created_at: .created_at, html_url: .html_url}]')
      REVIEW_COMMENTS=$(gh api repos/$REPO/pulls/$pr/comments --paginate --jq '[.[] | select(.user.login == "factory-droid[bot]") | {id: .id, body: .body, path: .path, line: .line, side: .side, created_at: .created_at, html_url: .html_url}]')
      REVIEWS=$(gh api repos/$REPO/pulls/$pr/reviews --paginate --jq '[.[] | select(.user.login == "factory-droid[bot]") | {id: .id, body: .body, state: .state, submitted_at: .submitted_at, html_url: .html_url}]')

      echo "    {"
      echo "      \"number\": $pr,"
      echo "      \"title\": $(echo "$PR_TITLE" | jq -R .),"
      echo "      \"issue_comments\": $ISSUE_COMMENTS,"
      echo "      \"review_comments\": $REVIEW_COMMENTS,"
      echo "      \"reviews\": $REVIEWS"
      echo -n "    }"
    done

    echo ""
    echo "  ]"
    echo "}"
  ) > "$OUTPUT_FILE"
done
```

### Step 3: Copy Golden Comments

```bash
RUN_NAME="run_$(date +%Y-%m-%d)"
cp ~/review-droid-benchmark/repos/golden_comments/code_review_benchmarks/sentry.json ~/review-droid-benchmark/results/${RUN_NAME}/raw_comments/golden_sentry.json
cp ~/review-droid-benchmark/repos/golden_comments/code_review_benchmarks/grafana.json ~/review-droid-benchmark/results/${RUN_NAME}/raw_comments/golden_grafana.json
cp ~/review-droid-benchmark/repos/golden_comments/code_review_benchmarks/keycloak.json ~/review-droid-benchmark/results/${RUN_NAME}/raw_comments/golden_keycloak.json
cp ~/review-droid-benchmark/repos/golden_comments/code_review_benchmarks/discourse.json ~/review-droid-benchmark/results/${RUN_NAME}/raw_comments/golden_discourse.json
cp ~/review-droid-benchmark/repos/golden_comments/code_review_benchmarks/cal_dot_com.json ~/review-droid-benchmark/results/${RUN_NAME}/raw_comments/golden_cal_dot_com.json
```

### Step 4: Run Evaluation

```bash
cd ~/review-droid-benchmark
source venv/bin/activate
export ANTHROPIC_API_KEY="sk-ant-api03-..."

RUN_NAME="run_$(date +%Y-%m-%d)"
python3 scripts/evaluate_all.py ${RUN_NAME}
```

---

## Reset Scripts by Repository

### droid-grafana (PRs #1-10)

```bash
export GH_PAGER=""
for pr in 1 2 3 4 5 6 7 8 9 10; do
  echo "=== Processing PR #$pr ==="
  for cid in $(gh api repos/droid-code-review-evals/droid-grafana/pulls/$pr/comments --jq '.[] | select(.user.login == "factory-droid[bot]") | .id'); do
    echo "Deleting PR comment $cid"
    gh api -X DELETE repos/droid-code-review-evals/droid-grafana/pulls/comments/$cid 2>/dev/null
  done
  for rid in $(gh api repos/droid-code-review-evals/droid-grafana/pulls/$pr/reviews --jq '.[] | select(.user.login == "factory-droid[bot]") | .id'); do
    echo "Updating review $rid"
    gh api -X PUT repos/droid-code-review-evals/droid-grafana/pulls/$pr/reviews/$rid -f body="." >/dev/null 2>&1
  done
  for cid in $(gh api repos/droid-code-review-evals/droid-grafana/issues/$pr/comments --jq '.[] | select(.user.login == "factory-droid[bot]" or .user.login == "varin-nair-factory") | .id'); do
    echo "Deleting issue comment $cid"
    gh api -X DELETE repos/droid-code-review-evals/droid-grafana/issues/comments/$cid 2>/dev/null
  done
  echo "Completed PR #$pr"
done
```

### droid-keycloak (PRs #1-10)

```bash
export GH_PAGER=""
for pr in 1 2 3 4 5 6 7 8 9 10; do
  echo "=== Processing PR #$pr ==="
  for cid in $(gh api repos/droid-code-review-evals/droid-keycloak/pulls/$pr/comments --jq '.[] | select(.user.login == "factory-droid[bot]") | .id'); do
    echo "Deleting PR comment $cid"
    gh api -X DELETE repos/droid-code-review-evals/droid-keycloak/pulls/comments/$cid 2>/dev/null
  done
  for rid in $(gh api repos/droid-code-review-evals/droid-keycloak/pulls/$pr/reviews --jq '.[] | select(.user.login == "factory-droid[bot]") | .id'); do
    echo "Updating review $rid"
    gh api -X PUT repos/droid-code-review-evals/droid-keycloak/pulls/$pr/reviews/$rid -f body="." >/dev/null 2>&1
  done
  for cid in $(gh api repos/droid-code-review-evals/droid-keycloak/issues/$pr/comments --jq '.[] | select(.user.login == "factory-droid[bot]" or .user.login == "varin-nair-factory") | .id'); do
    echo "Deleting issue comment $cid"
    gh api -X DELETE repos/droid-code-review-evals/droid-keycloak/issues/comments/$cid 2>/dev/null
  done
  echo "Completed PR #$pr"
done
```

### droid-discourse (PRs #1-10)

```bash
export GH_PAGER=""
for pr in 1 2 3 4 5 6 7 8 9 10; do
  echo "=== Processing PR #$pr ==="
  for cid in $(gh api repos/droid-code-review-evals/droid-discourse/pulls/$pr/comments --jq '.[] | select(.user.login == "factory-droid[bot]") | .id'); do
    echo "Deleting PR comment $cid"
    gh api -X DELETE repos/droid-code-review-evals/droid-discourse/pulls/comments/$cid 2>/dev/null
  done
  for rid in $(gh api repos/droid-code-review-evals/droid-discourse/pulls/$pr/reviews --jq '.[] | select(.user.login == "factory-droid[bot]") | .id'); do
    echo "Updating review $rid"
    gh api -X PUT repos/droid-code-review-evals/droid-discourse/pulls/$pr/reviews/$rid -f body="." >/dev/null 2>&1
  done
  for cid in $(gh api repos/droid-code-review-evals/droid-discourse/issues/$pr/comments --jq '.[] | select(.user.login == "factory-droid[bot]" or .user.login == "varin-nair-factory") | .id'); do
    echo "Deleting issue comment $cid"
    gh api -X DELETE repos/droid-code-review-evals/droid-discourse/issues/comments/$cid 2>/dev/null
  done
  echo "Completed PR #$pr"
done
```

### droid-cal_dot_com (PRs #1-10)

```bash
export GH_PAGER=""
for pr in 1 2 3 4 5 6 7 8 9 10; do
  echo "=== Processing PR #$pr ==="
  for cid in $(gh api repos/droid-code-review-evals/droid-cal_dot_com/pulls/$pr/comments --jq '.[] | select(.user.login == "factory-droid[bot]") | .id'); do
    echo "Deleting PR comment $cid"
    gh api -X DELETE repos/droid-code-review-evals/droid-cal_dot_com/pulls/comments/$cid 2>/dev/null
  done
  for rid in $(gh api repos/droid-code-review-evals/droid-cal_dot_com/pulls/$pr/reviews --jq '.[] | select(.user.login == "factory-droid[bot]") | .id'); do
    echo "Updating review $rid"
    gh api -X PUT repos/droid-code-review-evals/droid-cal_dot_com/pulls/$pr/reviews/$rid -f body="." >/dev/null 2>&1
  done
  for cid in $(gh api repos/droid-code-review-evals/droid-cal_dot_com/issues/$pr/comments --jq '.[] | select(.user.login == "factory-droid[bot]" or .user.login == "varin-nair-factory") | .id'); do
    echo "Deleting issue comment $cid"
    gh api -X DELETE repos/droid-code-review-evals/droid-cal_dot_com/issues/comments/$cid 2>/dev/null
  done
  echo "Completed PR #$pr"
done
```

---

## Trigger Reviews: All Repos

After resetting, trigger new reviews:

```bash
# droid-sentry (PRs #6-15)
for pr in 6 7 8 9 10 11 12 13 14 15; do
  gh pr comment $pr --repo droid-code-review-evals/droid-sentry --body "@droid review"
  echo "Triggered review on droid-sentry PR #$pr"
  sleep 2
done

# droid-grafana (PRs #1-10)
for pr in 1 2 3 4 5 6 7 8 9 10; do
  gh pr comment $pr --repo droid-code-review-evals/droid-grafana --body "@droid review"
  echo "Triggered review on droid-grafana PR #$pr"
  sleep 2
done

# droid-keycloak (PRs #1-10)
for pr in 1 2 3 4 5 6 7 8 9 10; do
  gh pr comment $pr --repo droid-code-review-evals/droid-keycloak --body "@droid review"
  echo "Triggered review on droid-keycloak PR #$pr"
  sleep 2
done

# droid-discourse (PRs #1-10)
for pr in 1 2 3 4 5 6 7 8 9 10; do
  gh pr comment $pr --repo droid-code-review-evals/droid-discourse --body "@droid review"
  echo "Triggered review on droid-discourse PR #$pr"
  sleep 2
done

# droid-cal_dot_com (PRs #1-10)
for pr in 1 2 3 4 5 6 7 8 9 10; do
  gh pr comment $pr --repo droid-code-review-evals/droid-cal_dot_com --body "@droid review"
  echo "Triggered review on droid-cal_dot_com PR #$pr"
  sleep 2
done
```

---

## Evaluation Scripts Reference

| Script | Purpose |
|--------|---------|
| `scripts/evaluate_sentry_run.py` | Evaluate droid-sentry (PRs #6-15) |
| `scripts/evaluate_all.py` | Evaluate all 5 repos |
| `scripts/generate_results_markdown.py` | Generate RESULTS.md and README.md from eval JSON |

### evaluate_sentry_run.py

- Loads Droid comments and golden comments for each PR
- Uses Claude Sonnet 4 to match comments semantically
- Classifies each as TP, FP, or FN
- **Calculates per-PR metrics programmatically** (no manual calculation)

Output: `sentry_eval.json` with complete results.

### generate_results_markdown.py

- Reads `sentry_eval.json` (single source of truth)
- Generates `RESULTS.md` with per-PR breakdown
- Generates `README.md` with run overview
- Supports baseline comparison
- **Eliminates manual calculation errors**

---

## See Also

- [Validation Playbook](VALIDATION_PLAYBOOK.md) - Manual ground truth validation
- [Architecture](ARCHITECTURE.md) - System design and improvement plans
- [results/](../results/) - Evaluation run data
