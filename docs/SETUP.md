# Setup Guide

One-time setup for the `droid-*` benchmark repositories and evaluation infrastructure.

## Prerequisites

- GitHub CLI (`gh`) installed and authenticated
- Git
- Access to create repos in the `droid-code-review-evals` organization

## Scope & Decisions

| Setting | Value |
|---------|-------|
| Organization | `droid-code-review-evals` |
| Repo visibility | Public |
| Target repos | `droid-sentry`, `droid-grafana`, `droid-keycloak`, `droid-discourse`, `droid-cal_dot_com` |
| Clone mode | Mirror (from `ai-code-review-evaluations/augment-*`) |
| PR set | Defined by `ai-code-review-evaluations/golden_comments` |
| Workflow | Identical everywhere, copied from this repo's `droid.yml` |

**Hard stop rule:** If a PR requires fallback to patch artifacts in `golden_comments`, stop and ask for explicit approval before proceeding.

## Local Workspace Layout

```
~/review-droid-benchmark/
  manifest.json
  repos/                  # Local mirrors/clones
    augment-sentry.git/
    augment-grafana.git/
    augment-keycloak.git/
    augment-discourse.git/
    augment-cal_dot_com.git/
    golden_comments/
  work/                   # Non-bare working dirs for PR creation
    droid-sentry/
    droid-grafana/
    droid-keycloak/
    droid-discourse/
    droid-cal_dot_com/
  logs/
  scripts/
```

---

## Phase 1: Inventory & Manifest Creation

### Step 1.1: Create Directory Structure

```bash
cd ~/review-droid-benchmark
mkdir -p repos work logs scripts
```

### Step 1.2: Clone golden_comments

```bash
cd ~/review-droid-benchmark/repos
git clone https://github.com/ai-code-review-evaluations/golden_comments.git
```

### Step 1.3: Mirror-clone the augment-* repos

```bash
cd ~/review-droid-benchmark/repos
git clone --mirror https://github.com/ai-code-review-evaluations/augment-sentry.git
git clone --mirror https://github.com/ai-code-review-evaluations/augment-grafana.git
git clone --mirror https://github.com/ai-code-review-evaluations/augment-keycloak.git
git clone --mirror https://github.com/ai-code-review-evaluations/augment-discourse.git
git clone --mirror https://github.com/ai-code-review-evaluations/augment-cal_dot_com.git
```

### Step 1.4: Get default branch and HEAD SHA

```bash
cd ~/review-droid-benchmark/repos
for repo in augment-sentry.git augment-grafana.git augment-keycloak.git augment-discourse.git augment-cal_dot_com.git; do
  echo "=== $repo ==="
  git -C $repo symbolic-ref HEAD  # shows default branch
  git -C $repo rev-parse HEAD     # shows HEAD SHA
done
```

### Step 1.5: Gather PR data from golden_comments

```bash
cd ~/review-droid-benchmark/repos/golden_comments
for project in sentry grafana keycloak discourse cal_dot_com; do
  echo "=== $project ==="
  cat code_review_benchmarks/${project}.json | jq -r '.[].pr_title'
done
```

### Step 1.6: Get branch names, base branches, and SHAs

```bash
for project in sentry grafana keycloak discourse cal_dot_com; do
  echo "=== $project ==="
  GH_PAGER="" gh pr list --repo ai-code-review-evaluations/augment-${project} \
     --state all --limit 20 --json number,title,headRefName,headRefOid,baseRefName
done
```

**Important:** Most PRs have custom base branches (not `main`), e.g.:
- `appstore-sync-refactor-base`
- `oauth-state-vulnerable`
- `performance-optimization-baseline`
- `feature-idp-cache-baseline`

The manifest must capture `baseRefName` for each PR to recreate them correctly.

---

## Phase 2: Create Destination Repos

### Step 2.1: Create empty repos in droid-code-review-evals

```bash
gh repo create droid-code-review-evals/droid-sentry --public --description "Droid code review benchmark - Sentry"
gh repo create droid-code-review-evals/droid-grafana --public --description "Droid code review benchmark - Grafana"
gh repo create droid-code-review-evals/droid-keycloak --public --description "Droid code review benchmark - Keycloak"
gh repo create droid-code-review-evals/droid-discourse --public --description "Droid code review benchmark - Discourse"
gh repo create droid-code-review-evals/droid-cal_dot_com --public --description "Droid code review benchmark - Cal.com"
```

### Step 2.2: Push mirrors to destination repos

```bash
cd ~/review-droid-benchmark/repos
git -C augment-sentry.git push --mirror https://github.com/droid-code-review-evals/droid-sentry.git
git -C augment-grafana.git push --mirror https://github.com/droid-code-review-evals/droid-grafana.git
git -C augment-keycloak.git push --mirror https://github.com/droid-code-review-evals/droid-keycloak.git
git -C augment-discourse.git push --mirror https://github.com/droid-code-review-evals/droid-discourse.git
git -C augment-cal_dot_com.git push --mirror https://github.com/droid-code-review-evals/droid-cal_dot_com.git
```

**Note:** The `--mirror` push will show `[remote rejected] refs/pull/*/head` and `refs/pull/*/merge` errors. This is expected - GitHub doesn't allow pushing to internal PR refs. All actual branches will push successfully.

---

## Phase 3: Add Workflows

### Step 3.1: Clone repos to work directory

```bash
cd ~/review-droid-benchmark/work
git clone https://github.com/droid-code-review-evals/droid-sentry.git droid-sentry
git clone https://github.com/droid-code-review-evals/droid-grafana.git droid-grafana
git clone https://github.com/droid-code-review-evals/droid-keycloak.git droid-keycloak
git clone https://github.com/droid-code-review-evals/droid-discourse.git droid-discourse
git clone https://github.com/droid-code-review-evals/droid-cal_dot_com.git droid-cal_dot_com
```

### Step 3.2: Add workflow file to each repo

```bash
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

This commit is the only intended divergence from the mirrored sources.

---

## Phase 4: Recreate Benchmark PRs

Since branches already exist from the mirror push, we just need to create PRs using `gh pr create`.

### droid-sentry (PRs #6-15)

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

### droid-grafana (PRs #1-10)

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

### droid-keycloak (PRs #1-10)

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

### droid-discourse (PRs #1-10)

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

### droid-cal_dot_com (PRs #1-10)

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

---

## Next Steps

After completing setup:
1. Trigger reviews by commenting `@droid review` on each PR
2. See [EVALS.md](EVALS.md) for running and analyzing evaluations
