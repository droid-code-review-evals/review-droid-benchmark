# Setup Guide — Greptile

One-time setup for the `greptile-*` benchmark repositories.

## Prerequisites

- GitHub CLI (`gh`) installed and authenticated
- Git
- Access to create repos in the `droid-code-review-evals` organization

## Scope & Decisions

| Setting | Value |
|---------|-------|
| Organization | `droid-code-review-evals` |
| Repo visibility | Public |
| Target repos | `greptile-sentry`, `greptile-grafana`, `greptile-keycloak`, `greptile-discourse`, `greptile-cal_dot_com` |
| Clone mode | Mirror (from `ai-code-review-evaluations/augment-*`) |
| PR set | Defined by `ai-code-review-evaluations/golden_comments` |

**Hard stop rule:** If a PR requires fallback to patch artifacts in `golden_comments`, stop and ask for explicit approval before proceeding.

## Local Workspace Layout

```
~/review-droid-benchmark/
  manifest.json
  source-augment-repos/                  # Local mirrors/clones (already present from droid setup)
    augment-sentry.git/
    augment-grafana.git/
    augment-keycloak.git/
    augment-discourse.git/
    augment-cal_dot_com.git/
  target-repos/
    greptile-sentry/
    greptile-grafana/
    greptile-keycloak/
    greptile-discourse/
    greptile-cal_dot_com/
```

---

## Phase 1: Create Destination Repos

```bash
gh repo create droid-code-review-evals/greptile-sentry --public --description "Greptile code review benchmark - Sentry"
gh repo create droid-code-review-evals/greptile-grafana --public --description "Greptile code review benchmark - Grafana"
gh repo create droid-code-review-evals/greptile-keycloak --public --description "Greptile code review benchmark - Keycloak"
gh repo create droid-code-review-evals/greptile-discourse --public --description "Greptile code review benchmark - Discourse"
gh repo create droid-code-review-evals/greptile-cal_dot_com --public --description "Greptile code review benchmark - Cal.com"
```

## Phase 2: Push Mirrors to Destination Repos

```bash
cd ~/review-droid-benchmark/source-augment-repos
git -C augment-sentry.git push --mirror https://github.com/droid-code-review-evals/greptile-sentry.git
git -C augment-grafana.git push --mirror https://github.com/droid-code-review-evals/greptile-grafana.git
git -C augment-keycloak.git push --mirror https://github.com/droid-code-review-evals/greptile-keycloak.git
git -C augment-discourse.git push --mirror https://github.com/droid-code-review-evals/greptile-discourse.git
git -C augment-cal_dot_com.git push --mirror https://github.com/droid-code-review-evals/greptile-cal_dot_com.git
```

**Note:** The `--mirror` push will show `[remote rejected] refs/pull/*/head` and `refs/pull/*/merge` errors. This is expected — GitHub doesn't allow pushing to internal PR refs. All actual branches will push successfully.

---

## Phase 3: Clone Repos to target-repos Directory

```bash
cd ~/review-droid-benchmark/target-repos
git clone https://github.com/droid-code-review-evals/greptile-sentry.git greptile-sentry
git clone https://github.com/droid-code-review-evals/greptile-grafana.git greptile-grafana
git clone https://github.com/droid-code-review-evals/greptile-keycloak.git greptile-keycloak
git clone https://github.com/droid-code-review-evals/greptile-discourse.git greptile-discourse
git clone https://github.com/droid-code-review-evals/greptile-cal_dot_com.git greptile-cal_dot_com
```

---

## Phase 4: Recreate Benchmark PRs

Since branches already exist from the mirror push, we just need to create PRs using `gh pr create`.

### greptile-sentry

```bash
cd ~/review-droid-benchmark/target-repos/greptile-sentry
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

### greptile-grafana

```bash
cd ~/review-droid-benchmark/target-repos/greptile-grafana
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

### greptile-keycloak

```bash
cd ~/review-droid-benchmark/target-repos/greptile-keycloak
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

### greptile-discourse

```bash
cd ~/review-droid-benchmark/target-repos/greptile-discourse
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

### greptile-cal_dot_com

```bash
cd ~/review-droid-benchmark/target-repos/greptile-cal_dot_com
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
