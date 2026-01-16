# Analysis of Missed Issues (131 False Negatives)

## Summary by Severity
- **Critical**: 9 (6.9%)
- **High**: 39 (29.8%)
- **Medium**: 46 (35.1%)
- **Low**: 37 (28.2%)

**Key insight**: 36.6% of missed issues are High/Critical - these are serious bugs.

---

## Categorization by Detection Method Required

### Category 1: Type Flow / Data Type Mismatches (18 issues)

These require tracing what types flow through functions.

| Repo | Issue | Severity |
|------|-------|----------|
| sentry | `get_item_key` assumes numeric key but used with datetime | High |
| sentry | `math.floor/ceil` on datetime raises TypeError | High |
| cal.com | `dayjs` object comparison with `===` always false | Medium |
| cal.com | `parseRefreshTokenResponse` returns safeParse result not data | High |
| cal.com | `res.data` undefined when res is fetch Response | High |
| grafana | `dbSession.Exec(args...)` expects string first param | Medium |
| keycloak | Wrong provider returned (default vs BouncyCastle) | High |

**Why missed**: Droid doesn't trace types through function calls. Needs to understand that `order_by='-datetime'` means the value is a datetime object.

---

### Category 2: Null/None/Undefined Reference (19 issues)

These require understanding when values can be null.

| Repo | Issue | Severity |
|------|-------|----------|
| sentry | `organization_context.member` can be None for API keys | High |
| sentry | `github_authenticated_user` state might be missing | Medium |
| discourse | TopicUser record might not exist (nil) | High |
| discourse | EmbeddableHost record might not exist | Medium |
| discourse | `contents` parameter could be nil | Medium |
| cal.com | `mainHostDestinationCalendar` undefined if empty array | High |
| keycloak | `Optional.get()` without checking `isPresent()` | Medium |
| keycloak | `getSubGroupsCount()` returns null violating contract | Critical |
| grafana | Nil request causes panic in middleware | High |

**Why missed**: Requires understanding which values can be null in different code paths. Droid sees the code but doesn't reason about "what if this is null?"

---

### Category 3: Concurrency / Race Conditions (12 issues)

These require understanding concurrent execution patterns.

| Repo | Issue | Severity |
|------|-------|----------|
| grafana | Race condition in device count check | High |
| grafana | Race in `BuildIndex` - multiple goroutines build same index | High |
| grafana | `TotalDocs()` races with concurrent index creation | High |
| grafana | Double-checked locking pattern incomplete | Medium |
| cal.com | Backup code can be used multiple times concurrently | High |
| cal.com | `retryCount + 1` loses increments under concurrency | High |
| keycloak | Reader thread not waited for - race in test | Medium |
| discourse | Thread-safety issue with lazy `@loaded_locales` | Low |

**Why missed**: Requires reasoning about what happens when multiple threads/processes execute code simultaneously. This is hard for LLMs without explicit prompting.

---

### Category 4: Security Vulnerabilities (11 issues)

These require security-specific knowledge.

| Repo | Issue | Severity |
|------|-------|----------|
| discourse | SSRF via `open(url)` without validation | Critical |
| discourse | Origin validation bypass with indexOf | Medium |
| discourse | X-Frame-Options: ALLOWALL disables clickjacking protection | Medium |
| discourse | XSS via unescaped URL interpolation | Medium |
| sentry | OAuth state uses static value instead of per-request random | Medium |
| cal.com | Case sensitivity bypass in email blacklist | High |
| grafana | Asymmetric cache trust - grants cached but denials aren't | High |
| keycloak | Feature flag inconsistency causes orphaned permissions | High |

**Why missed**: Security bugs require domain-specific knowledge about attack patterns (SSRF, XSS, CSRF state, cache poisoning).

---

### Category 5: API Contract / Breaking Changes (14 issues)

These require understanding API contracts and backward compatibility.

| Repo | Issue | Severity |
|------|-------|----------|
| sentry | Breaking changes in error response format | Medium |
| sentry | Detector validator uses wrong key | Medium |
| discourse | Method override breaks existing callers | Medium |
| discourse | `include_website_name` missing required `?` suffix | Medium |
| discourse | Migration doesn't normalize existing data | High |
| cal.com | Calendar interface contract broken | Low |
| cal.com | `refreshFunction` return type mismatch | High |
| grafana | Authentication now fails entirely (was async) | Medium |
| keycloak | Permission lookup uses wrong resource type | High |

**Why missed**: Requires understanding what the "contract" is - either from docs, tests, or other callers. Droid would need to actively look for how the API is used elsewhere.

---

### Category 6: Async/Await Mistakes (8 issues)

These are specific to JavaScript/TypeScript async patterns.

| Repo | Issue | Severity |
|------|-------|----------|
| cal.com | `forEach` with async callbacks - fire and forget | Critical |
| cal.com | `deleteScheduledEmailReminder` not awaited | Medium |
| cal.com | `deleteScheduledSMSReminder` not awaited | Medium |
| discourse | `findMembers()` async but not awaited | High |

**Why missed**: Specific pattern: `array.forEach(async () => ...)` doesn't await. Droid should know this anti-pattern.

---

### Category 7: Logic Errors / Wrong Variable (16 issues)

These are simple mistakes using wrong variable or inverted logic.

| Repo | Issue | Severity |
|------|-------|----------|
| sentry | Returns `monitor.config` instead of modified `config` | High |
| sentry | `zip()` assumes dict preserves order | Low |
| cal.com | Logic uses AND instead of OR for permissions | Critical |
| cal.com | Incorrect end time uses `slotStartTime` instead of `slotEndTime` | Medium |
| cal.com | `externalCalendarId` search logic always fails | High |
| cal.com | Logic inversion with `IS_TEAM_BILLING_ENABLED` | Medium |
| keycloak | Wrong parameter in null check (`grantType` vs `rawTokenId`) | Critical |
| keycloak | Substring indices inverted in `isAccessTokenId` | High |
| keycloak | `canManage()` checks wrong permission | High |
| grafana | `recordLegacyDuration` should be `recordStorageDuration` | High |
| grafana | `enableSqlExpressions` always returns false | Critical |

**Why missed**: These are "obvious" once you look closely, but require careful reading. The bug is in plain sight but Droid didn't notice.

---

### Category 8: Test-Specific Issues (10 issues)

Issues that only manifest in tests or are about test quality.

| Repo | Issue | Severity |
|------|-------|----------|
| sentry | Fixed sleep in tests is flaky | Low |
| sentry | Monkeypatched sleep won't wait | Medium |
| sentry | Test docstring doesn't match implementation | Low |
| keycloak | Test cleanup uses wrong alias | Medium |
| keycloak | Test comment contradicts code | Low |
| grafana | Template variables not used in test setup | Low |

**Why missed**: Test-specific context. Droid may not understand test mocking patterns.

---

### Category 9: Language/Framework Specific (13 issues)

Bugs requiring knowledge of specific language/framework behavior.

| Repo | Issue | Severity |
|------|-------|----------|
| sentry | Django querysets don't support negative slicing | High |
| sentry | `queue.shutdown(immediate=False)` may not exist | High |
| sentry | `hash()` is non-deterministic across processes | Low |
| sentry | `sample_rate = 0.0` is falsy and skipped | Low |
| discourse | Invalid ERB syntax `end if` | Medium |
| discourse | `-ms-align-items` never existed | Low |
| keycloak | `picocli.exit()` calls `System.exit()` directly | Medium |
| keycloak | `SpawnProcess` not subclass of `Process` on POSIX | High |
| cal.com | Zod computed property syntax invalid | High |
| cal.com | Prisma `@updatedAt` needs explicit field in update | Medium |
| cal.com | macOS-specific `sed -i` fails on Linux | Low |

**Why missed**: Requires deep knowledge of specific frameworks/libraries. Django ORM behavior, Python multiprocessing, Prisma decorators, etc.

---

### Category 10: Import/Symbol Errors (3 issues)

Missing or incorrect imports.

| Repo | Issue | Severity |
|------|-------|----------|
| sentry | Importing non-existent `OptimizedCursorPaginator` | Low |
| keycloak | `ConditionalPasskeysEnabled()` called wrong | Medium |
| keycloak | Recursive call using `session` instead of `delegate` | Critical |

**Why missed**: Requires verifying the imported symbol actually exists. Should be caught by grep.

---

## Top Opportunities for Improvement

### 1. Logic Errors (16 issues, 5 Critical/High)
**Detection strategy**: More careful variable name checking, especially in conditionals and return statements.

### 2. Null Reference (19 issues, 5 High)
**Detection strategy**: Explicit null-path analysis - "what if X is null?"

### 3. Type Mismatches (18 issues, 7 High)
**Detection strategy**: Trace types through function calls, especially for math operations.

### 4. Concurrency (12 issues, 6 High)
**Detection strategy**: Flag common patterns (double-check locking, concurrent mutations).

### 5. Security (11 issues, 3 Critical/High)
**Detection strategy**: Security-specific checks for SSRF, XSS, auth state, cache trust.

### 6. Async/Await (8 issues, 2 Critical/High)
**Detection strategy**: Flag `forEach` with async callbacks, check all async calls are awaited.

---

## Patterns Droid Should Learn

1. **`array.forEach(async () => ...)`** - always a bug in JS/TS
2. **`hash()` in Python** - non-deterministic across processes
3. **Django querysets** - don't support negative slicing
4. **`Optional.get()`** - must check `isPresent()` first
5. **Double-checked locking** - must re-check after acquiring lock
6. **OAuth state** - must be per-request random, not static
7. **`zip(a, dict.values())`** - dict order not guaranteed
8. **Type-sensitive operations** - trace input types (floor/ceil, etc.)
9. **Null reference chains** - `a.b.c` where any could be null
10. **Return value mismatch** - returning wrapper instead of data
