# Plan: set up `droid-*` benchmark repos + recreate benchmark PRs (no execution yet)

## Scope / decisions (confirmed)

- Create new org: `droid-code-review-evals` (user will do this manually before we execute)
- Repo visibility: **public**
- Target repos: `droid-sentry`, `droid-grafana`, `droid-keycloak`, `droid-discourse`, `droid-cal_dot_com`
- Clone mode: **mirror** (from `ai-code-review-evaluations`, not upstream)
- Canonical sources: `ai-code-review-evaluations/augment-*` (one per project)
- PR set defined by: `ai-code-review-evaluations/golden_comments`
- PR diffs sourced from: `augment-*` refs/SHAs whenever possible
- **Hard stop rule:** if a PR requires fallback to patch artifacts in `golden_comments`, stop and ask for explicit approval before proceeding.
- Triggering reviews: user will manually comment `@droid review` on each benchmark PR
- Workflow: identical everywhere, copied from this repo, committed directly to `main`
- Keep PR titles + commit titles the same; reuse Augment branch names when available (else deterministic fallback with notice)

## Local workspace layout

Everything under `~/review-droid-benchmark/`.

Proposed structure:

```
~/review-droid-benchmark/
  manifest.json
  repos/                  # local mirrors/clones
    augment-sentry.git/   # mirror clones (bare) OR working clones as needed
    augment-grafana.git/
    augment-keycloak.git/
    augment-discourse.git/
    augment-cal_dot_com.git/
    golden_comments/
  work/                  # non-bare working dirs when we need to craft branches/PRs
    droid-sentry/
    droid-grafana/
    droid-keycloak/
    droid-discourse/
    droid-cal_dot_com/
  logs/
  scripts/
```

## Phase 1 — Inventory & manifest creation

1. Clone `ai-code-review-evaluations/golden_comments` locally.
2. For each project (`sentry`, `grafana`, `keycloak`, `discourse`, `cal_dot_com`):
   - Mirror-clone `ai-code-review-evaluations/augment-<project>`.
   - Record into `manifest.json`:
     - source repo URL
     - default branch name
     - head SHA on default branch at time of clone
3. Parse `golden_comments` to extract the canonical list of **10 PRs per project**:
   - benchmark PR ID (stable identifier)
   - expected title (and any metadata needed to locate the change)
   - reference pointers (preferred): PR number / head SHA / branch name in the `augment-*` repo
   - **base branch name** (critical: PRs do NOT all target `main`)

Output: `manifest.json` fully describing what we will recreate.

### Commands to set up directory structure and clone repos

```bash
cd ~/review-droid-benchmark
mkdir -p repos work logs scripts

# Clone golden_comments
cd ~/review-droid-benchmark/repos
git clone https://github.com/ai-code-review-evaluations/golden_comments.git

# Mirror-clone the augment-* repos
git clone --mirror https://github.com/ai-code-review-evaluations/augment-sentry.git
git clone --mirror https://github.com/ai-code-review-evaluations/augment-grafana.git
git clone --mirror https://github.com/ai-code-review-evaluations/augment-keycloak.git
git clone --mirror https://github.com/ai-code-review-evaluations/augment-discourse.git
git clone --mirror https://github.com/ai-code-review-evaluations/augment-cal_dot_com.git

# Get default branch and HEAD SHA for each mirror
for repo in augment-sentry.git augment-grafana.git augment-keycloak.git augment-discourse.git augment-cal_dot_com.git; do
  echo "=== $repo ==="
  git -C $repo symbolic-ref HEAD  # shows default branch
  git -C $repo rev-parse HEAD     # shows HEAD SHA
done
```

### Commands to gather PR data

Get PR titles from golden_comments:
```bash
cd ~/review-droid-benchmark/repos/golden_comments
for project in sentry grafana keycloak discourse cal_dot_com; do
  echo "=== $project ==="
  cat code_review_benchmarks/${project}.json | jq -r '.[].pr_title'
done
```

Get branch names, base branches, and SHAs from augment-* repos:
```bash
for project in sentry grafana keycloak discourse cal_dot_com; do
  echo "=== $project ==="
  GH_PAGER="" gh pr list --repo ai-code-review-evaluations/augment-${project} \
     --state all --limit 20 --json number,title,headRefName,headRefOid,baseRefName
done
```

**Important discovery:** Most PRs have custom base branches (not `main`), e.g.:
- `appstore-sync-refactor-base`
- `oauth-state-vulnerable`
- `performance-optimization-baseline`
- `feature-idp-cache-baseline`

The manifest must capture `baseRefName` for each PR to recreate them correctly.

## Phase 2 — Create destination repos in `droid-code-review-evals`

For each project:

1. Create empty repo `droid-<project>` in `droid-code-review-evals` (public).
2. Push the mirrored `augment-*` content into it (mirror push) so the destination starts from identical history/refs.

Result: `droid-*` repos match the evaluation sources without touching upstream OSS repos.

### Commands to create and push repos

```bash
# Create the repos
gh repo create droid-code-review-evals/droid-sentry --public --description "Droid code review benchmark - Sentry"
gh repo create droid-code-review-evals/droid-grafana --public --description "Droid code review benchmark - Grafana"
gh repo create droid-code-review-evals/droid-keycloak --public --description "Droid code review benchmark - Keycloak"
gh repo create droid-code-review-evals/droid-discourse --public --description "Droid code review benchmark - Discourse"
gh repo create droid-code-review-evals/droid-cal_dot_com --public --description "Droid code review benchmark - Cal.com"

# Push mirrors
cd ~/review-droid-benchmark/repos
git -C augment-sentry.git push --mirror https://github.com/droid-code-review-evals/droid-sentry.git
git -C augment-grafana.git push --mirror https://github.com/droid-code-review-evals/droid-grafana.git
git -C augment-keycloak.git push --mirror https://github.com/droid-code-review-evals/droid-keycloak.git
git -C augment-discourse.git push --mirror https://github.com/droid-code-review-evals/droid-discourse.git
git -C augment-cal_dot_com.git push --mirror https://github.com/droid-code-review-evals/droid-cal_dot_com.git
```

**Note:** The `--mirror` push will show `[remote rejected] refs/pull/*/head` and `refs/pull/*/merge` errors. This is expected - GitHub doesn't allow pushing to internal PR refs. The important thing is that all actual branches push successfully (look for `[new branch]` lines). All head branches and base branches needed for PRs will be available.

## Phase 3 — Add workflows (identical everywhere)

1. Copy this repo’s workflow file(s) (as instructed) into each `droid-*` repo under `.github/workflows/`.
2. Commit directly to `main`.

This commit is the only intended divergence from the mirrored sources.


### Commands to clone work directories and add workflow

```bash
# Clone repos to work directory
cd ~/review-droid-benchmark/work
git clone https://github.com/droid-code-review-evals/droid-sentry.git droid-sentry
git clone https://github.com/droid-code-review-evals/droid-grafana.git droid-grafana
git clone https://github.com/droid-code-review-evals/droid-keycloak.git droid-keycloak
git clone https://github.com/droid-code-review-evals/droid-discourse.git droid-discourse
git clone https://github.com/droid-code-review-evals/droid-cal_dot_com.git droid-cal_dot_com

# Add workflow file to each repo and push
cd ~/review-droid-benchmark/work
for project in droid-sentry droid-grafana droid-keycloak droid-discourse droid-cal_dot_com; do
  echo "=== $project ==="
  mkdir -p ${project}/.github/workflows
  cp ~/review-droid-benchmark/droid.yml ${project}/.github/workflows/droid.yml
  cd ${project}
  git add .github/workflows/droid.yml
  git commit -m "Add Droid code review workflow"
  git push
  cd ..
done
```
## Phase 4 — Recreate benchmark PRs in `droid-*`

For each project’s 10 PRs:

1. Identify the source change in `augment-*`:
   - Prefer an existing branch name (best case).
   - Else use PR head SHA / `refs/pull/*` if accessible via fetch.
2. Create the branch in `droid-*`:
   - **Preferred:** same branch name as Augment uses.
   - **Fallback (only if needed, with notice):** `benchmark/<project>/<benchmark_pr_id>`
3. Ensure PR title and commit titles match the benchmark:
   - If we can push the original commits (mirror history), titles naturally match.
   - If any rewrite is needed, preserve commit messages explicitly.
4. Open PR against the **correct base branch** (from `baseRefName`, NOT always `main`) in `droid-*` with:
   - same PR title
   - PR body includes benchmark ID + link back to the `golden_comments` entry for traceability
5. Record created PR URL/number in `manifest.json`.

**Stop condition:** if any PR cannot be reproduced from `augment-*` refs/SHAs and would require applying a patch from `golden_comments`, stop and ask for explicit approval for that specific PR.

### Commands to create PRs

Since branches already exist from the mirror push, we just need to create PRs using `gh pr create`.

**droid-sentry:**
```bash
cd ~/review-droid-benchmark/work/droid-sentry
gh pr create --head performance-enhancement-complete --base master --title "Enhanced Pagination Performance for High-Volume Audit Logs" --body "Benchmark PR from ai-code-review-evaluations"
gh pr create --head performance-enhancement-complete --base performance-optimization-baseline --title "Optimize spans buffer insertion with eviction during insert" --body "Benchmark PR from ai-code-review-evaluations"
gh pr create --head error-upsampling-race-condition --base master --title "feat(upsampling) - Support upsampled error count with performance optimizations" --body "Benchmark PR from ai-code-review-evaluations"
gh pr create --head oauth-state-secure --base oauth-state-vulnerable --title "GitHub OAuth Security Enhancement" --body "Benchmark PR from ai-code-review-evaluations"
gh pr create --head replays-delete-stable --base replays-delete-vulnerable --title "Replays Self-Serve Bulk Delete System" --body "Benchmark PR from ai-code-review-evaluations"
gh pr create --head span-flusher-multiprocess --base span-flusher-stable --title "Span Buffer Multiprocess Enhancement with Health Monitoring" --body "Benchmark PR from ai-code-review-evaluations"
gh pr create --head ecosystem-sync-integration-after --base ecosystem-sync-integration-before --title "feat(ecosystem): Implement cross-system issue synchronization" --body "Benchmark PR from ai-code-review-evaluations"
gh pr create --head monitor-incident-refactor-after --base monitor-incident-refactor-before --title "ref(crons): Reorganize incident creation / issue occurrence logic" --body "Benchmark PR from ai-code-review-evaluations"
gh pr create --head kafka-consumer-parallel-after --base kafka-consumer-parallel-before --title "feat(uptime): Add ability to use queues to manage parallelism" --body "Benchmark PR from ai-code-review-evaluations"
gh pr create --head workflow-engine-stateful-detector-after --base workflow-engine-stateful-detector-before --title "feat(workflow_engine): Add in hook for producing occurrences from the stateful detector" --body "Benchmark PR from ai-code-review-evaluations"
```

**droid-grafana:**
```bash
cd ~/review-droid-benchmark/work/droid-grafana
gh pr create --head implement-device-limits --base enhance-anonymous-access --title "Anonymous: Add configurable device limit" --body "Benchmark PR from ai-code-review-evaluations"
gh pr create --head authz-service-improve-caching-pr --base cache-optimization-baseline --title "AuthZService: improve authz caching" --body "Benchmark PR from ai-code-review-evaluations"
gh pr create --head plugins/rename-instrumentation-middleware-to-metrics-middleware --base main --title "Plugins: Chore: Renamed instrumentation middleware to metrics middleware" --body "Benchmark PR from ai-code-review-evaluations"
gh pr create --head query-splitting-enhancements --base query-splitting-baseline --title "Advanced Query Processing Architecture" --body "Benchmark PR from ai-code-review-evaluations"
gh pr create --head notification-rule-enhancements --base notification-rule-baseline --title "Notification Rule Processing Engine" --body "Benchmark PR from ai-code-review-evaluations"
gh pr create --head dual-storage-enhanced --base dual-storage-baseline --title "Dual Storage Architecture" --body "Benchmark PR from ai-code-review-evaluations"
gh pr create --head db-cleanup-optimized --base db-cleanup-baseline --title "Database Performance Optimizations" --body "Benchmark PR from ai-code-review-evaluations"
gh pr create --head asset-loading-optimized --base asset-loading-baseline --title "Frontend Asset Optimization" --body "Benchmark PR from ai-code-review-evaluations"
gh pr create --head advanced-sql-analytics --base data-analysis-features --title "Advanced SQL Analytics Framework" --body "Benchmark PR from ai-code-review-evaluations"
gh pr create --head unified-storage-enhancements --base performance-optimization-baseline --title "Unified Storage Performance Optimizations" --body "Benchmark PR from ai-code-review-evaluations"
```

**droid-keycloak:**
```bash
cd ~/review-droid-benchmark/work/droid-keycloak
gh pr create --head enhance-passkey-authentication-flow --base improve-auth-user-experience --title "Fixing Re-authentication with passkeys" --body "Benchmark PR from ai-code-review-evaluations"
gh pr create --head feature-idp-cache-implementation --base feature-idp-cache-baseline --title "Add caching support for IdentityProviderStorageProvider.getForLogin operations" --body "Benchmark PR from ai-code-review-evaluations"
gh pr create --head feature-authz-crypto-implementation --base feature-authz-crypto-baseline --title "Add AuthzClientCryptoProvider for authorization client cryptographic operations" --body "Benchmark PR from ai-code-review-evaluations"
gh pr create --head feature-rolling-updates-implementation --base feature-rolling-updates-baseline --title "Add rolling-updates feature flag and compatibility framework" --body "Benchmark PR from ai-code-review-evaluations"
gh pr create --head feature-clients-authz-implementation --base feature-clients-authz-baseline --title "Add Client resource type and scopes to authorization schema" --body "Benchmark PR from ai-code-review-evaluations"
gh pr create --head feature-groups-authz-implementation --base feature-groups-authz-baseline --title "Add Groups resource type and scopes to authorization schema" --body "Benchmark PR from ai-code-review-evaluations"
gh pr create --head feature-html-sanitizer-implementation --base feature-html-sanitizer-baseline --title "Add HTML sanitizer for translated message resources" --body "Benchmark PR from ai-code-review-evaluations"
gh pr create --head feature-token-context-implementation --base feature-token-context-baseline --title "Implement access token context encoding framework" --body "Benchmark PR from ai-code-review-evaluations"
gh pr create --head feature-recovery-keys-implementation --base feature-recovery-keys-foundation --title "Implement recovery key support for user storage providers" --body "Benchmark PR from ai-code-review-evaluations"
gh pr create --head feature-group-concurrency-implementation --base feature-group-concurrency-update --title "Fix concurrent group access to prevent NullPointerException" --body "Benchmark PR from ai-code-review-evaluations"
```

**droid-discourse:**
```bash
cd ~/review-droid-benchmark/work/droid-discourse
gh pr create --head large-image-processing --base image-processing-optimization --title "FEATURE: automatically downsize large images" --body "Benchmark PR from ai-code-review-evaluations"
gh pr create --head topic-email-management --base email-notifications-enhancement --title "FEATURE: per-topic unsubscribe option in emails" --body "Benchmark PR from ai-code-review-evaluations"
gh pr create --head blocked-email-validation-post --base blocked-email-validation-pre --title "Add comprehensive email validation for blocked users" --body "Benchmark PR from ai-code-review-evaluations"
gh pr create --head embed-url-handling-post --base embed-url-handling-pre --title "Enhance embed URL handling and validation system" --body "Benchmark PR from ai-code-review-evaluations"
gh pr create --head header-layout-optimization-post --base header-layout-optimization-pre --title "Optimize header layout performance with flexbox mixins" --body "Benchmark PR from ai-code-review-evaluations"
gh pr create --head url-handling-post --base url-handling-pre --title "UX: show complete URL path if website domain is same as instance domain" --body "Benchmark PR from ai-code-review-evaluations"
gh pr create --head theme-color-scheme-post --base theme-color-scheme-pre --title "scale-color \$lightness must use \$secondary for dark themes" --body "Benchmark PR from ai-code-review-evaluations"
gh pr create --head group-dm-user-addition-post --base group-dm-user-addition-pre --title "FIX: proper handling of group memberships" --body "Benchmark PR from ai-code-review-evaluations"
gh pr create --head localization-system-post --base localization-system-pre --title "FEATURE: Localization fallbacks (server-side)" --body "Benchmark PR from ai-code-review-evaluations"
gh pr create --head rest-serializer-enhancement-post --base rest-serializer-enhancement-pre --title "FEATURE: Can edit category/host relationships for embedding" --body "Benchmark PR from ai-code-review-evaluations"
```

**droid-cal_dot_com:**
```bash
cd ~/review-droid-benchmark/work/droid-cal_dot_com
gh pr create --head appstore-async-improvements --base appstore-sync-refactor-base --title "Async import of the appStore packages" --body "Benchmark PR from ai-code-review-evaluations"
gh pr create --head improve-two-factor-authentication-features --base enhance-two-factor-security-foundation --title "feat: 2fa backup codes" --body "Benchmark PR from ai-code-review-evaluations"
gh pr create --head fix/handle-collective-multiple-host-destinations --base enhance-collective-scheduling-foundation --title "fix: handle collective multiple host on destinationCalendar" --body "Benchmark PR from ai-code-review-evaluations"
gh pr create --head insights-performance-optimization --base insights-query-foundation --title "feat: convert InsightsBookingService to use Prisma.sql raw queries" --body "Benchmark PR from ai-code-review-evaluations"
gh pr create --head workflow-queue-enhanced --base workflow-queue-base --title "Comprehensive workflow reminder management for booking lifecycle events" --body "Benchmark PR from ai-code-review-evaluations"
gh pr create --head date-algorithm-enhanced --base date-algorithm-base --title "Advanced date override handling and timezone compatibility improvements" --body "Benchmark PR from ai-code-review-evaluations"
gh pr create --head oauth-security-enhanced --base oauth-security-base --title "OAuth credential sync and app integration enhancements" --body "Benchmark PR from ai-code-review-evaluations"
gh pr create --head sms-retry-enhanced --base sms-retry-base --title "SMS workflow reminder retry count tracking" --body "Benchmark PR from ai-code-review-evaluations"
gh pr create --head guest-management-enhanced --base guest-management-base --title "Add guest management functionality to existing bookings" --body "Benchmark PR from ai-code-review-evaluations"
gh pr create --head introduce-cache-key-overflow --base calendar-cache-foundation --title "feat: add calendar cache status and actions (#22532)" --body "Benchmark PR from ai-code-review-evaluations"
```

## Phase 5 — Run Evaluation

### Overview

The evaluation process compares Droid's review comments against golden comments using an LLM-as-judge approach. All metrics are calculated programmatically to eliminate manual errors.

### Evaluation Scripts

**Location:** `~/review-droid-benchmark/scripts/`

Key scripts:
- `evaluate_sentry_run.py` - Evaluates a single droid-sentry run (PRs #6-15)
- `generate_results_markdown.py` - Generates RESULTS.md and README.md from evaluation JSON

### Step 1: Trigger reviews on all PRs

Comment `@droid review` on each benchmark PR to trigger the review workflow.

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

### Step 2: Set up Python environment (one-time setup)

```bash
cd ~/review-droid-benchmark
python3 -m venv venv
source venv/bin/activate
pip install anthropic
```

### Step 3: Fetch comments from PRs

For **droid-sentry only** evaluation (recommended for quick iteration):

```bash
# Set run name
RUN_NAME="run_$(date +%Y-%m-%d)"

# Create directories
mkdir -p ~/review-droid-benchmark/results/${RUN_NAME}/raw_comments

# Fetch comments
for pr in 6 7 8 9 10 11 12 13 14 15; do
  echo "Fetching comments from PR #$pr..."
  gh api repos/droid-code-review-evals/droid-sentry/pulls/$pr/comments > \
    ~/review-droid-benchmark/results/${RUN_NAME}/pr_${pr}_comments.json
done

# Copy golden comments
cp ~/review-droid-benchmark/repos/golden_comments/code_review_benchmarks/sentry.json \
   ~/review-droid-benchmark/results/${RUN_NAME}/golden_comments.json

# Copy transform script
cp ~/review-droid-benchmark/results/run_2026-01-14/transform_comments.py \
   ~/review-droid-benchmark/results/${RUN_NAME}/transform_comments.py

# Transform comments to evaluation format
cd ~/review-droid-benchmark/results/${RUN_NAME}
python3 transform_comments.py
mkdir -p raw_comments
cp golden_comments.json raw_comments/golden_sentry.json
```

For **all repositories** evaluation:

```bash
# Fetch comments for each repo
# This script is saved at scripts/fetch_comments.sh
for REPO_NAME in droid-sentry droid-grafana droid-keycloak droid-discourse droid-cal_dot_com; do
  # Determine PR range based on repo
  if [ "$REPO_NAME" = "droid-sentry" ]; then
    PR_START=6; PR_END=15
  else
    PR_START=1; PR_END=10
  fi
  
  REPO="droid-code-review-evals/${REPO_NAME}"
  OUTPUT_FILE="$HOME/review-droid-benchmark/results/run_$(date +%Y-%m-%d)/raw_comments/${REPO_NAME}.json"
  
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

Copy golden comments for comparison:

```bash
cp ~/review-droid-benchmark/repos/golden_comments/code_review_benchmarks/sentry.json ~/review-droid-benchmark/results/run_$(date +%Y-%m-%d)/raw_comments/golden_sentry.json
cp ~/review-droid-benchmark/repos/golden_comments/code_review_benchmarks/grafana.json ~/review-droid-benchmark/results/run_$(date +%Y-%m-%d)/raw_comments/golden_grafana.json
cp ~/review-droid-benchmark/repos/golden_comments/code_review_benchmarks/keycloak.json ~/review-droid-benchmark/results/run_$(date +%Y-%m-%d)/raw_comments/golden_keycloak.json
cp ~/review-droid-benchmark/repos/golden_comments/code_review_benchmarks/discourse.json ~/review-droid-benchmark/results/run_$(date +%Y-%m-%d)/raw_comments/golden_discourse.json
cp ~/review-droid-benchmark/repos/golden_comments/code_review_benchmarks/cal_dot_com.json ~/review-droid-benchmark/results/run_$(date +%Y-%m-%d)/raw_comments/golden_cal_dot_com.json
```

### Step 4: Run evaluation

**For droid-sentry:**

```bash
cd ~/review-droid-benchmark
source venv/bin/activate

# Set your API key
export ANTHROPIC_API_KEY="sk-ant-api03-..."

# Run evaluation (calculates all metrics programmatically)
RUN_NAME="run_$(date +%Y-%m-%d)"
python3 scripts/evaluate_sentry_run.py ${RUN_NAME}
```

The evaluation script:
1. Loads Droid's review comments and golden comments for each PR
2. Uses Claude Sonnet 4 to semantically match each Droid comment to golden comments
3. Classifies each as True Positive, False Positive, or False Negative
4. **Calculates per-PR and overall metrics programmatically** (no manual calculation)

Output: `results/${RUN_NAME}/sentry_eval.json` with:
- Per-PR metrics (TP, FP, FN, precision, recall, F-score)
- Overall summary metrics
- Full evaluation details for each comment

### Step 5: Generate documentation

```bash
cd ~/review-droid-benchmark
source venv/bin/activate

RUN_NAME="run_$(date +%Y-%m-%d)"

# Generate RESULTS.md and README.md from evaluation JSON
python3 scripts/generate_results_markdown.py ${RUN_NAME}

# Or compare against baseline:
python3 scripts/generate_results_markdown.py ${RUN_NAME} run_2026-01-14
```

This generates:
- `RESULTS.md` - Detailed per-PR breakdown with metrics
- `README.md` - Run overview and configuration notes

**All metrics are calculated programmatically from the evaluation JSON** - no manual calculations needed!

### Metrics Definitions

- **True Positive (TP)**: Droid comment semantically matches a golden comment
- **False Positive (FP)**: Droid comment doesn't match any golden comment  
- **False Negative (FN)**: Golden comment that Droid missed
- **Precision** = TP / (TP + FP) - "Of what Droid flagged, how much was correct?"
- **Recall** = TP / (TP + FN) - "Of what should have been flagged, how much did Droid catch?"
- **F-Score** = 2 × (Precision × Recall) / (Precision + Recall) - Harmonic mean of precision and recall

### Evaluation Scripts

The evaluation uses an LLM-as-judge approach to semantically match Droid's comments to golden comments.

**Key components:**
1. **Semantic matching via LLM**: Uses Claude Sonnet 4 to determine if Droid's comment matches any golden comment
2. **Severity mapping**: Golden uses High/Medium/Low; Droid uses P0-P3
3. **Per-PR tracking**: Records which golden comments were found vs missed
4. **Programmatic metrics**: All calculations done in Python (no manual errors)

**Key Scripts:**

1. **[`scripts/evaluate_sentry_run.py`](scripts/evaluate_sentry_run.py)** - Main evaluation script for droid-sentry
   - Loads Droid comments and golden comments
   - Uses Claude API to match comments semantically
   - **Calculates per-PR metrics** (TP, FP, FN, precision, recall, F-score)
   - Outputs `sentry_eval.json` with complete results

2. **[`scripts/generate_results_markdown.py`](scripts/generate_results_markdown.py)** - Documentation generator
   - Reads `sentry_eval.json` (single source of truth)
   - Generates `RESULTS.md` with per-PR breakdown
   - Generates `README.md` with run overview
   - Supports baseline comparison
   - **Eliminates manual calculation errors**

See the script files for implementation details.

## Deliverables

- `~/review-droid-benchmark/manifest.json` mapping:
  - each `droid-*` repo → base head SHA → list of PRs (source ref + destination PR URL)
- `droid-code-review-evals/droid-*` repos with:
  - mirrored codebase history from `ai-code-review-evaluations/augment-*`
  - identical Droid workflow committed to `main`
  - recreated benchmark PRs ready for manual `@droid review` triggers
- `~/review-droid-benchmark/results/run_YYYY-MM-DD/` containing:
  - `raw_comments/` - Fetched Droid comments and golden comments
  - `evaluations/` - LLM evaluation results with TP/FP/FN classifications
  - `evaluations/overall_summary.json` - Aggregated metrics

## Workspace Structure (Final)

```
~/review-droid-benchmark/
  PLAN.md                 # This file
  EVAL_LOOP_DESIGN.md     # Design doc for automated eval loop
  manifest.json           # PR and repo metadata
  droid.yml               # Workflow file template
  venv/                   # Python virtual environment
  repos/                  # Local mirrors/clones
    augment-sentry.git/
    augment-grafana.git/
    augment-keycloak.git/
    augment-discourse.git/
    augment-cal_dot_com.git/
    golden_comments/
  work/                   # Non-bare working dirs
    droid-sentry/
    droid-grafana/
    droid-keycloak/
    droid-discourse/
    droid-cal_dot_com/
  scripts/                # Evaluation scripts
    evaluate_sentry.py
    evaluate_all.py
  results/                # Evaluation results by run date
    run_2026-01-13/
      raw_comments/
        droid-sentry.json
        droid-grafana.json
        droid-keycloak.json
        droid-discourse.json
        droid-cal_dot_com.json
        golden_sentry.json
        golden_grafana.json
        golden_keycloak.json
        golden_discourse.json
        golden_cal_dot_com.json
      evaluations/
        droid-sentry_eval.json
        droid-grafana_eval.json
        droid-keycloak_eval.json
        droid-discourse_eval.json
        droid-cal_dot_com_eval.json
        overall_summary.json
  logs/
```

---

## Quick Reference: Complete Evaluation Workflow

### For droid-sentry (recommended for iteration)

Complete end-to-end workflow:

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

---

## Running droid-sentry Only Evaluation (Detailed)

For quick iteration on just droid-sentry (PRs #6-15), use this workflow:

### Step 1: Reset droid-sentry PRs

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

### Step 2: Trigger reviews

```bash
for pr in 6 7 8 9 10 11 12 13 14 15; do
  gh pr comment $pr --repo droid-code-review-evals/droid-sentry --body "@droid review"
  echo "Triggered droid-sentry PR #$pr"
  sleep 2
done
```

### Step 3: Wait for reviews to complete

Monitor workflow runs:
```bash
gh run list --repo droid-code-review-evals/droid-sentry --limit 20
```

### Step 4: Fetch comments and evaluate

```bash
# Create run directory
RUN_NAME="run_$(date +%Y-%m-%d)-sentry-only"
mkdir -p ~/review-droid-benchmark/results/${RUN_NAME}/raw_comments

# Fetch droid-sentry comments
REPO="droid-code-review-evals/droid-sentry"
OUTPUT_FILE="$HOME/review-droid-benchmark/results/${RUN_NAME}/raw_comments/droid-sentry.json"

echo "Fetching droid-sentry comments..."
(
  echo "{"
  echo "  \"repo\": \"droid-sentry\","
  echo "  \"fetched_at\": \"$(date -u +%Y-%m-%dT%H:%M:%SZ)\","
  echo "  \"prs\": ["
  
  FIRST_PR=true
  for pr in 6 7 8 9 10 11 12 13 14 15; do
    if [ "$FIRST_PR" = true ]; then
      FIRST_PR=false
    else
      echo "    ,"
    fi
    
    PR_TITLE=$(gh pr view $pr -R $REPO --json title --jq '.title')
    REVIEW_COMMENTS=$(gh api repos/$REPO/pulls/$pr/comments --paginate --jq '[.[] | select(.user.login == "factory-droid[bot]") | {id: .id, body: .body, path: .path, line: .line, created_at: .created_at}]')
    REVIEWS=$(gh api repos/$REPO/pulls/$pr/reviews --paginate --jq '[.[] | select(.user.login == "factory-droid[bot]") | {id: .id, body: .body, state: .state}]')
    
    echo "    {"
    echo "      \"number\": $pr,"
    echo "      \"title\": $(echo "$PR_TITLE" | jq -R .),"
    echo "      \"review_comments\": $REVIEW_COMMENTS,"
    echo "      \"reviews\": $REVIEWS"
    echo -n "    }"
  done
  
  echo ""
  echo "  ]"
  echo "}"
) > "$OUTPUT_FILE"

# Copy golden comments
cp ~/review-droid-benchmark/repos/golden_comments/code_review_benchmarks/sentry.json \
   ~/review-droid-benchmark/results/${RUN_NAME}/raw_comments/golden_sentry.json

# Run evaluation (create single-repo evaluator)
cd ~/review-droid-benchmark
source venv/bin/activate
ANTHROPIC_API_KEY="your-api-key" python3 scripts/evaluate_sentry.py ${RUN_NAME}
```

### Step 5: Review results

```bash
RUN_NAME="run_$(date +%Y-%m-%d)-sentry-only"
cat ~/review-droid-benchmark/results/${RUN_NAME}/sentry_eval.json | jq '.summary'
```

---

## Utility Scripts

### Reset PRs for Re-evaluation

These scripts clear all Droid comments and reset PRs for a fresh evaluation run. They:
1. Delete inline PR review comments from `factory-droid[bot]`
2. Update PR review bodies to "." (reviews can't be deleted, only edited)
3. Delete issue comments from `factory-droid[bot]` and `varin-nair-factory`

**droid-sentry (PRs #6-15):**
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

**droid-grafana (PRs #1-10):**
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

**droid-keycloak (PRs #1-10):**
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

**droid-discourse (PRs #1-10):**
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

**droid-cal_dot_com (PRs #1-10):**
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

### Trigger Reviews on All Repos

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
