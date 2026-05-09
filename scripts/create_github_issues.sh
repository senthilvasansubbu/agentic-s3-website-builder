#!/usr/bin/env bash
# Bulk-create all 48 codebase issues as GitHub Issues
set -e
REPO="senthilvasansubbu/agentic-s3-website-builder"

create() {
  local title="$1" labels="$2" body="$3"
  gh issue create --repo "$REPO" --title "$title" --label "$labels" --body "$body"
  sleep 0.5
}

echo "Creating CRITICAL issues..."
create "[CRITICAL-1] 22 empty test stubs in test_editor_features.py - zero coverage" \
  "critical,test" \
  "**File:** \`tests/test_editor_features.py\` (lines 26-287)

**Problem:** All 22 test methods are empty stubs (\`pass\`). Zero test coverage for editor UI features — styled dialogs, carousel, animations, presets, persistence, multi-file upload.

**Fix:** Implement each test using the test client and assert real behaviour.

**Closes when:** All 22 tests are implemented and passing."

create "[CRITICAL-2] Hardcoded JWT_SECRET default in auth_service.py" \
  "critical,security" \
  "**File:** \`services/auth_service.py\` (lines 12-13)

**Problem:** \`JWT_SECRET\` falls back to \`'change-me-in-production'\` if the env var is missing. Any deployment without the env var is silently insecure.

**Fix:** Raise a startup error if \`JWT_SECRET\` is not set or equals the default placeholder. Never use a default.

**Closes when:** App refuses to start if JWT_SECRET is missing/default."

create "[CRITICAL-3] Unauthenticated /shop/finalize-image endpoint" \
  "critical,security,api" \
  "**File:** \`api/routes/website_builder.py\`

**Problem:** \`POST /shop/finalize-image\` has no authentication check — anyone can call it and manipulate file operations.

**Fix:** Add \`@require_auth\` decorator, validate that the requesting user owns the target site.

**Closes when:** Endpoint rejects unauthenticated calls with 401."

create "[CRITICAL-4] SQL injection risk in coupon UPDATE query (commerce.py)" \
  "critical,security,database" \
  "**File:** \`api/routes/commerce.py\` (lines 91-96)

**Problem:** Dynamic column names are built into the UPDATE query using an f-string: \`f\"UPDATE coupons SET {set_clause}\"\`. Column names are not parameterized — SQL injection vector.

**Fix:** Whitelist allowed column names, validate against schema before building query.

**Closes when:** No dynamic SQL string construction using user-controlled input."

create "[CRITICAL-5] 10+ bare except blocks with no logging in website_builder.py" \
  "critical,error-handling" \
  "**File:** \`api/routes/website_builder.py\` (lines 92, 105, 276, 429, 481, 500, 672, 908, 1199, 1222)

**Problem:** Multiple \`except Exception:\` blocks with no logging — silent failures hide real bugs from developers and operators.

**Fix:** Add structured \`logger.exception()\` calls, return proper HTTP error responses.

**Closes when:** All exception handlers log the error and return meaningful responses."

echo "Creating HIGH issues..."
create "[HIGH-6] No startup validation for OPENAI_API_KEY" \
  "high,config" \
  "**File:** \`config/settings.py\`

**Problem:** Missing \`OPENAI_API_KEY\` only generates a warning at startup — the app will crash mid-request when the agent pipeline runs.

**Fix:** Validate all required env vars at startup, fail fast with a clear error message listing exactly what is missing.

**Closes when:** App refuses to start without OPENAI_API_KEY."

create "[HIGH-7] 4+ generic exception handlers without logging in clients.py" \
  "high,error-handling" \
  "**File:** \`api/routes/clients.py\` (lines 75, 134, 192, 221)

**Problem:** Generic \`except Exception\` blocks catch all errors without logging or differentiated responses, making debugging impossible.

**Fix:** Add \`logger.exception()\`, return specific HTTP status codes based on exception type.

**Closes when:** All handlers log errors and return typed responses."

create "[HIGH-8] Frontend global state race conditions in dashboard.js" \
  "high,frontend" \
  "**File:** \`frontend/dashboard.js\` (lines 3-31)

**Problem:** Multiple global variables (\`currentUser\`, \`lastReferenceQuality\`, etc.) with no synchronization — race conditions occur on concurrent operations.

**Fix:** Refactor to event-driven architecture or encapsulate state in a single object with controlled access.

**Closes when:** No unprotected global mutable state, concurrent operations are safe."

create "[HIGH-9] No database connection pooling — N+1 query risk" \
  "high,performance,database" \
  "**File:** \`database/snowflake_client.py\` (lines 78-88)

**Problem:** A new SQLite connection is created per query with no pooling or reuse. In loops this creates N+1 connection overhead and latency spikes.

**Fix:** Implement connection pool (e.g., \`sqlite3\` with a thread-local connection or \`sqlalchemy\` pool), reuse connections across requests.

**Closes when:** Connection pooling is in place, verified by load test."

create "[HIGH-10] No code coverage metrics configured" \
  "high,test" \
  "**File:** \`tests/\`

**Problem:** No coverage tooling configured — impossible to know what percentage of code is actually tested.

**Fix:** Add \`pytest-cov\`, set minimum threshold (80%), configure with \`pyproject.toml\` or \`setup.cfg\`.

**Closes when:** \`pytest --cov\` runs successfully with a coverage report and threshold enforced."

create "[HIGH-11] Silent failure in campaign send logic (commerce.py)" \
  "high,error-handling" \
  "**File:** \`api/routes/commerce.py\` (lines 214-224)

**Problem:** Campaign send catches exception silently with \`pass\` — user gets no feedback when a campaign fails to send.

**Fix:** Implement retry logic, return error to caller, log failure details.

**Closes when:** Failed campaign sends are surfaced to the user and logged."

create "[HIGH-12] 3 bare exception handlers in shopping_cart.py" \
  "high,error-handling" \
  "**File:** \`api/routes/shopping_cart.py\` (lines 122, 146, 410)

**Problem:** Bare exception handlers with no recovery or logging — cart failures are invisible.

**Fix:** Add logging, implement graceful cart state recovery.

**Closes when:** All handlers log and return appropriate error responses."

create "[HIGH-13] Silent exception catch in team.py" \
  "high,error-handling" \
  "**File:** \`api/routes/team.py\` (line 57)

**Problem:** Silent \`except: pass\` — team management errors are swallowed.

**Fix:** Add logging, return proper error response.

**Closes when:** Handler logs error and returns typed HTTP response."

create "[HIGH-14] Empty catch block in dashboard.js (line 96)" \
  "high,frontend,error-handling" \
  "**File:** \`frontend/dashboard.js\` (line 96)

**Problem:** Empty \`catch { apiFetch._lastError = ... }\` — errors silently swallowed, no user notification.

**Fix:** Add error display (toast), log to console in dev mode.

**Closes when:** User is notified of API failures."

create "[HIGH-15] Empty try/catch at dashboard.js line 398" \
  "high,frontend,error-handling" \
  "**File:** \`frontend/dashboard.js\` (line 398)

**Problem:** \`try {} catch(e) {}\` — debugging issues completely hidden.

**Fix:** Add console.error logging at minimum, implement recovery logic.

**Closes when:** All try/catch blocks handle errors meaningfully."

echo "Creating MEDIUM issues..."
create "[MEDIUM-16] Hardcoded default admin password in .env.example" \
  "medium,security" \
  "**File:** \`.env.example\` (line 71)

**Problem:** \`ADMIN_PASSWORD=Admin@1234\` in example file — could be accidentally used as-is in production or committed.

**Fix:** Replace with a generated placeholder like \`ADMIN_PASSWORD=<generate-a-strong-password>\`, document requirement.

**Closes when:** No real/guessable defaults in .env.example."

create "[MEDIUM-17] Foreign keys disabled in SQLite (PRAGMA foreign_keys=OFF)" \
  "medium,security,database" \
  "**File:** \`database/snowflake_client.py\` (line 60)

**Problem:** Referential integrity is not enforced — orphaned records can accumulate silently.

**Fix:** Enable \`PRAGMA foreign_keys=ON\`, run cleanup migration for existing orphans.

**Closes when:** Foreign keys are enabled and orphaned data audit passes."

create "[MEDIUM-18] Missing ownership authorization checks in clients.py" \
  "medium,security,api" \
  "**File:** \`api/routes/clients.py\`

**Problem:** No validation that a client owns the website they're operating on — potential cross-tenant data access.

**Fix:** Add ownership assertions to all client endpoints before executing operations.

**Closes when:** All endpoints verify client_id ownership before proceeding."

create "[MEDIUM-19] No pre-check on STORAGE_SECRETS_KEY — runtime crash" \
  "medium,security,config" \
  "**File:** \`services/secret_store.py\` (line 34)

**Problem:** App crashes at runtime with an unhelpful error if \`STORAGE_SECRETS_KEY\` is missing rather than failing at startup.

**Fix:** Add startup validation, raise clear error with setup instructions.

**Closes when:** App fails at startup with a clear message if key is missing."

create "[MEDIUM-20] SMTP_PASSWORD defaults to empty — silent email failure" \
  "medium,config" \
  "**File:** \`services/notification_service.py\` (lines 23-32)

**Problem:** \`SMTP_PASSWORD\` defaults to empty string — email sending silently fails without warning.

**Fix:** Check for empty value at notification time, log a clear warning, surface error to caller.

**Closes when:** Empty SMTP config produces a clear error instead of silent failure."

create "[MEDIUM-21] .env.example missing required vs optional field documentation" \
  "medium,config" \
  "**File:** \`.env.example\`

**Problem:** No indication which environment variables are mandatory vs optional — new developers can misconfigure easily.

**Fix:** Add comments marking each variable as \`# REQUIRED\` or \`# OPTIONAL\`.

**Closes when:** Every variable in .env.example has a required/optional annotation."

create "[MEDIUM-22] Plan limit check runs SELECT COUNT(*) per request — no caching" \
  "medium,performance" \
  "**File:** \`api/routes/website_builder.py\` (lines 358-371)

**Problem:** Full \`SELECT COUNT(*)\` runs on every request for plan limit checking — database load spike risk under concurrency.

**Fix:** Cache plan limit results (short TTL), or denormalize the count into the client row.

**Closes when:** Plan limit check does not hit database on every request."

create "[MEDIUM-23] Duplicate stock fields in cart_items table" \
  "medium,database" \
  "**File:** \`database/migrations.py\` (lines 86-106)

**Problem:** \`cart_items\` has both \`stock\` (INTEGER) and \`stock_quantity\` (INTEGER) — duplicate fields with unclear semantics.

**Fix:** Decide canonical field, create migration to drop the redundant one, update all references.

**Closes when:** Only one stock field exists and is consistently used."

create "[MEDIUM-24] items_json in carts table has undefined structure — no validation" \
  "medium,database" \
  "**File:** \`database/migrations.py\` (lines 112-120)

**Problem:** \`carts.items_json\` is a VARIANT with no defined schema — any JSON shape can be stored, breaking queries.

**Fix:** Define JSON schema, add validation in cart service before write.

**Closes when:** JSON schema is documented and validated on write."

create "[MEDIUM-25] websites table optional fields have no defaults — NULL handling inconsistent" \
  "medium,database" \
  "**File:** \`database/migrations.py\` (lines 39-68)

**Problem:** \`s3_url\`, \`domain\`, \`title\`, \`description\` have no defaults — NULL handling spread across code is inconsistent.

**Fix:** Define sensible empty-string defaults, add NOT NULL where appropriate.

**Closes when:** Schema migration adds defaults, NULL checks removed from code."

create "[MEDIUM-26] Migrations have no rollback mechanism" \
  "medium,database" \
  "**File:** \`database/migrations.py\`

**Problem:** Failed migrations leave the database in an inconsistent state with no rollback path.

**Fix:** Wrap each migration in a transaction, implement corresponding rollback functions.

**Closes when:** Each migration has a paired rollback and is wrapped in a transaction."

create "[MEDIUM-27] /scrape-url endpoint missing rate limiting — SSRF/DoS risk" \
  "medium,security,api" \
  "**File:** \`api/routes/website_builder.py\`

**Problem:** No rate limiting on \`POST /scrape-url\` — can be abused for SSRF or to exhaust server resources.

**Fix:** Add SlowAPI limiter, validate and allowlist target URL schemes/domains.

**Closes when:** Rate limit enforced, SSRF protection in place."

create "[MEDIUM-28] SSE /build-stream endpoint has no timeout or cleanup documentation" \
  "medium,api" \
  "**File:** \`api/routes/website_builder.py\`

**Problem:** Server-Sent Events stream has no documented max duration or cleanup on disconnect — potential resource leak.

**Fix:** Implement connection timeout (e.g., 5 min), cleanup generator on client disconnect.

**Closes when:** Stream timeout and cleanup logic is implemented and tested."

create "[MEDIUM-29] Password field placeholder exposes credential format in dashboard.html" \
  "medium,security,frontend" \
  "**File:** \`frontend/dashboard.html\` (line 446)

**Problem:** Placeholder text shows real credential JSON format — exposes secret structure in HTML source.

**Fix:** Remove placeholder examples from password-type input fields.

**Closes when:** No credential format examples in HTML placeholders."

create "[MEDIUM-30] apiFetch() timeout not handled — returns null without user notification" \
  "medium,frontend" \
  "**File:** \`frontend/dashboard.js\` (lines 89-102)

**Problem:** API request timeout returns \`null\` silently — user sees a stale/blank UI with no feedback.

**Fix:** Add AbortController timeout, show toast notification on timeout.

**Closes when:** Timeout shows user-facing message instead of silent null."

echo "Creating LOW issues..."
create "[LOW-31] Generic exception handling in CLI main.py" \
  "low,error-handling" \
  "**File:** \`main.py\` (lines 116-176)

**Problem:** CLI errors caught generically without context or actionable messages.

**Fix:** Add typed exception handling with suggested fixes based on error type.

**Closes when:** CLI errors show helpful context to the developer."

create "[LOW-32] No single validation point for image backend config" \
  "low,config" \
  "**File:** \`services/image_service.py\` (lines 337-356)

**Problem:** Multiple scattered fallback warnings for missing S3/Drive/OneDrive/FTP configs instead of centralized validation.

**Fix:** Centralize image backend config validation at startup with a single report.

**Closes when:** Single startup check reports all missing image backend configs."

create "[LOW-33] Stripe config missing check in monitoring_service.py" \
  "low,config" \
  "**File:** \`services/monitoring_service.py\` (line 128)

**Problem:** Hard-coded check for STRIPE_SECRET_KEY missing returns 402 with a generic message.

**Fix:** Add env validation, surface specific config error message.

**Closes when:** Clear error message when Stripe is unconfigured."

create "[LOW-34] Analytics log table has no cleanup/archival policy" \
  "low,performance" \
  "**File:** \`services/analytics_service.py\` (lines 18-30)

**Problem:** One row inserted per event, no cleanup — analytics table will grow unbounded.

**Fix:** Implement log rotation (delete records older than 90 days) or archival job.

**Closes when:** Scheduled cleanup/archival is running."

create "[LOW-35] Hardcoded time.sleep() in tests — slow and brittle" \
  "low,performance,test" \
  "**File:** \`tests/run_automated_tests.py\` (lines 93-288)

**Problem:** Multiple \`time.sleep(1-3)\` calls — tests are slow and flaky on slower machines.

**Fix:** Replace with \`pytest\` fixture polling helpers that wait for condition with timeout.

**Closes when:** No hardcoded sleeps remain in test files."

create "[LOW-36] SQL placeholder mismatch — %s vs ? in auth_service.py" \
  "low,database" \
  "**File:** \`services/auth_service.py\` (lines 47-51)

**Problem:** OTP insertion uses \`%s\` but SQLite adapter expects \`?\` — could cause failures.

**Fix:** Normalize all SQL to use \`?\` placeholders consistently.

**Closes when:** All SQL in the codebase uses consistent placeholder style."

create "[LOW-37] ALTER TABLE migrations not idempotent — fail on re-run" \
  "low,database" \
  "**File:** \`database/migrations.py\` (lines 359-360)

**Problem:** ALTER TABLE for \`owner_id\` and \`permissions\` columns doesn't check existence — fails if run twice.

**Fix:** Add IF NOT EXISTS guard or check column existence before altering.

**Closes when:** All migrations can be run multiple times safely."

create "[LOW-38] Unclear comment about scraped_title not being passed" \
  "low,code-quality" \
  "**File:** \`api/routes/website_builder.py\` (line 773)

**Problem:** Comment says 'scraped_title is intentionally NOT passed' but doesn't explain why — future developer may 'fix' it accidentally.

**Fix:** Add detailed explanation of the intent and reason behind the decision.

**Closes when:** Comment clearly explains the architectural decision."

create "[LOW-39] Temp password field requires manual entry — security risk" \
  "low,frontend,security" \
  "**File:** \`frontend/dashboard.html\` (line 1472)

**Problem:** Temporary password field has no auto-generate option — users pick weak passwords.

**Fix:** Add auto-generate button that creates a strong random password and copies it to clipboard.

**Closes when:** Password field has auto-generate capability."

create "[LOW-40] Toast fallback in dashboard.js uses fragile typeof check" \
  "low,frontend,code-quality" \
  "**File:** \`frontend/dashboard.js\` (line 105)

**Problem:** \`if (typeof toast === 'undefined')\` fallback check — fragile global dependency detection.

**Fix:** Use proper ES module import or guaranteed initialization order.

**Closes when:** No global typeof guard for toast function."

create "[LOW-41] dashboard.js is a 14K+ line monolithic file" \
  "low,frontend,code-quality" \
  "**File:** \`frontend/dashboard.js\`

**Problem:** 14,000+ line single file — extremely difficult to navigate, test, or maintain.

**Fix:** Split into logical modules: \`auth.js\`, \`sites.js\`, \`editor.js\`, \`settings.js\`, \`commerce.js\`, \`monitoring.js\`.

**Closes when:** File is split into modules under 2K lines each."

create "[LOW-42] README.md entry point instruction is outdated (main.py vs app.py)" \
  "low,code-quality" \
  "**File:** \`README.md\`

**Problem:** README still references \`python main.py\` as the entry point but the app runs via \`app.py\`.

**Fix:** Update all getting-started instructions to use \`app.py\`.

**Closes when:** README accurately reflects current setup process. ✅ Already partially fixed — verify all sections."

create "[LOW-43] console.error messages from agents exposed in generated HTML" \
  "low,code-quality" \
  "**File:** \`agents/requirements_analyst.py\` (line 282)

**Problem:** \`console.error('Shop load error', e)\` injected into generated HTML — error messages exposed to end users.

**Fix:** Use server-side logger instead of injecting console.error into HTML output.

**Closes when:** No console.error injected into generated HTML."

create "[LOW-44] currency_service.py uses ip-api.com free tier — rate limit risk" \
  "low,config" \
  "**File:** \`services/currency_service.py\` (line 4)

**Problem:** Free tier of ip-api.com is rate-limited — silently fails when limit exceeded, breaking currency detection.

**Fix:** Add rate limit error handling, implement a fallback (default currency), consider paid tier.

**Closes when:** Currency service gracefully handles rate limit with a fallback."

create "[LOW-45] Google API missing library failure in hosting_service.py is silent" \
  "low,error-handling" \
  "**File:** \`services/hosting_service.py\` (line 124)

**Problem:** Missing Google API library prints error but doesn't raise — operation fails silently, caller gets incorrect success response.

**Fix:** Raise exception, propagate error to caller with clear message.

**Closes when:** Missing Google API raises and propagates correctly."

create "[LOW-46] pytest conftest fixtures not verified for proper isolation" \
  "low,test" \
  "**File:** \`tests/conftest.py\`

**Problem:** Unclear if database state is properly reset between tests — tests may pollute each other.

**Fix:** Add explicit session/function-scoped fixtures with teardown, verify test isolation.

**Closes when:** Each test runs in isolation with a clean database state."

create "[LOW-47] Inconsistent logging — mix of print(), logger, and silence" \
  "low,code-quality" \
  "**Files:** Multiple (notification_service.py, hosting_service.py, website_builder.py, others)

**Problem:** Inconsistent logging strategy across the codebase — some uses \`logger.debug()\`, some \`print()\`, some nothing.

**Fix:** Standardize on Python \`logging\` module with structured JSON output, remove all \`print()\` used for operational logging.

**Closes when:** Zero \`print()\` statements for operational logging, all using \`logger.*\`."

create "[LOW-48] No retry logic for transient failures (network, Stripe, timeouts)" \
  "low,feature,error-handling" \
  "**File:** \`services/auth_service.py\` and external API call sites

**Problem:** Hard failures on transient network/Stripe/OTP errors — user gets an error when a simple retry would succeed.

**Fix:** Implement exponential backoff with jitter for external API calls, circuit breaker pattern for critical services.

**Closes when:** Transient failures are retried automatically with configurable max attempts."

echo ""
echo "✅ All 48 issues created successfully!"
