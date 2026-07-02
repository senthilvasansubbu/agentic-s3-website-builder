# Feature Improvement Backlog (Exhaustive)

Date: 2026-05-11
Scope: App User dashboard, Client workflows, Admin console, public storefront capabilities, and platform operations.

## Prioritization Model

- P0: Must improve immediately (reliability, auth, publish safety, checkout safety)
- P1: High value near-term improvements
- P2: Medium-term quality and growth improvements

## 1) Authentication and Access (Login, OTP, Roles)

Priority: P0

User story:
As an app user, team member, or client, I want secure login and role-based access so that I can only access authorized data and actions.

Acceptance criteria:
1. Register, verify OTP, login, me, and password-change flows are all functional for each allowed role.
2. Invalid credentials and unverified users receive consistent error responses.
3. Role-based authorization is enforced for all protected endpoints.
4. Session expiry and token refresh behavior is documented and test-covered.

API constraints:
1. Keep compatibility for existing auth routes and token payload fields.
2. Enforce role checks server-side for every mutating route.
3. OTP verification endpoint must remain idempotent for repeated requests.

## 2) Overview Dashboard

Priority: P1

User story:
As a user, I want a clear account health summary so I can quickly decide what action to take.

Acceptance criteria:
1. Overview loads key counters and actionable insights.
2. Empty states are handled gracefully.
3. Failures in one widget do not break the entire page.
4. Refresh behavior is deterministic and avoids stale data confusion.

API constraints:
1. Summary responses should use aggregation-friendly endpoints.
2. Role-aware filtering required in all aggregate queries.

## 3) My Websites Management

Priority: P0

User story:
As a user, I want to list and manage all websites so I can operate at scale.

Acceptance criteria:
1. Website list supports search, filters, and sorting.
2. Website cards/rows show status, theme, domain, timestamps.
3. Delete flow includes confirmation and clear post-delete state.
4. Access rules differ correctly for app users vs client users.

API constraints:
1. Keep website_id stable across all lifecycle endpoints.
2. Pagination/filter/sort params must be explicit and documented.

## 4) Build Website Pipeline

Priority: P0

User story:
As a user, I want a robust AI build flow so I can create websites with predictable outcomes.

Acceptance criteria:
1. Build starts reliably and returns an immediate operation context.
2. Build status and stream endpoints reflect true progress and final state.
3. Build narrative is available for observability and troubleshooting.
4. Long-running jobs provide timeout/retry-safe UX messaging.

API constraints:
1. Build start endpoint must be idempotent for retries.
2. Stream/status endpoints must remain backward compatible.
3. Concurrency limits are required per user and per website.

## 5) Staging Area and Deploy Promotion

Priority: P0

User story:
As a user, I want staging-first deployment so I can validate safely before going live.

Acceptance criteria:
1. Staged HTML retrieval and updates work with version checks.
2. Deploy action promotes staged content to live safely.
3. Publish failures return actionable diagnostics.
4. Rollback approach is available or clearly defined.

API constraints:
1. Promotion endpoint must enforce optimistic locking/version guard.
2. Store staging and live artifacts separately.

## 6) Edit Website Experience

Priority: P1

User story:
As a user, I want editable website content and settings so I can iterate continuously.

Acceptance criteria:
1. Edit flow supports content updates and preserves structure.
2. Save/rebuild flows expose progress and completion states.
3. Validation prevents invalid updates.
4. Unsaved change warnings are shown on navigation.

API constraints:
1. Partial update semantics must remain PATCH-compatible.
2. Conflict handling is required for concurrent edits.

## 7) Shopping Cart and Catalog Operations

Priority: P0

User story:
As a merchant user, I want complete catalog and cart tooling so I can sell products reliably.

Acceptance criteria:
1. Category and cart-item CRUD are fully functional.
2. Legacy product aliases keep working where expected.
3. Catalog import by URL and file upload are resilient and report imported/skipped counts.
4. Cart session upsert/get flows are reliable.

API constraints:
1. Cart/item writes must be atomic and race-safe.
2. Price calculations and totals must be server-authoritative.
3. Import endpoints should enforce schema validation and size limits.

## 8) Media Upload and Finalization

Priority: P1

User story:
As a user, I want safe image upload/finalization so product media is optimized and consistent.

Acceptance criteria:
1. Upload returns expected image variants and URLs.
2. Finalization persists selected URLs for products.
3. Invalid image formats/sizes are rejected with clear errors.
4. Storage backend config errors are surfaced meaningfully.

API constraints:
1. Signed URL/security controls required where object storage is used.
2. Upload endpoints need strict content-type and size checks.

## 9) Billing and Subscription Plans

Priority: P0

User story:
As an account owner, I want transparent billing and plan controls so I can manage costs and entitlements.

Acceptance criteria:
1. Plan list, plan-features, subscription details all align.
2. Subscribe flow redirects and returns clear outcome states.
3. Plan enforcement gates features in UI and backend.
4. Billing status issues are visible and recoverable.

API constraints:
1. Webhook processing must be idempotent.
2. Sensitive payment secrets must never be logged or leaked.
3. Plan entitlements should be a single source of truth.

## 10) Storefront Checkout and Payment Config

Priority: P0

User story:
As a site owner, I want secure checkout and payment config so customers can pay without friction.

Acceptance criteria:
1. Payment gateway config validates ownership and credentials.
2. Checkout starts successfully for valid cart payloads.
3. Webhook events reconcile final payment state.
4. Failed checkout states are traceable for support.

API constraints:
1. PCI-sensitive fields must be tokenized and encrypted.
2. Checkout initiation must enforce request idempotency.

## 11) Feedback Collection and Management

Priority: P1

User story:
As a business user, I want customer feedback capture and review so I can improve service quality.

Acceptance criteria:
1. Public feedback submission works per website.
2. Dashboard/admin feedback views are filtered and sortable.
3. Anti-spam and rate limits are enforced.
4. Feedback history is retained with timestamps.

API constraints:
1. Public submission endpoints need abuse protection.
2. PII handling must follow retention and masking rules.

## 12) Monitoring, Incidents, and Escalation

Priority: P0

User story:
As an operator, I want actionable monitoring so I can detect, resolve, and prevent production issues.

Acceptance criteria:
1. Platform and website health endpoints return reliable signals.
2. Incident list and resolve actions are consistent.
3. Escalation and reminder workflows are visible and auditable.
4. Monitoring history and notifications are queryable.

API constraints:
1. Time-series responses need stable schema and timestamps.
2. Incident state transitions must be valid and auditable.

## 13) Coupons

Priority: P1

User story:
As a merchant, I want coupon lifecycle controls so I can run promotions safely.

Acceptance criteria:
1. Coupon create/list/update/delete work by website ownership.
2. Duplicate code prevention per website is enforced.
3. Validity windows and limits behave correctly.
4. UI shows clear active/expired/disabled states.

API constraints:
1. Coupon redemption logic must be race-safe.
2. Validation errors should include machine-readable reasons.

## 14) Notifications and Campaigns

Priority: P1

User story:
As a merchant, I want campaign-based notifications so I can engage customers via email, SMS, and WhatsApp.

Acceptance criteria:
1. Campaign create/list/send/delete flows work per website.
2. Send operation reports sent counts and failures.
3. Channel failures do not hide partial success.
4. Scheduled and sent timestamps are persisted.

API constraints:
1. Channel delivery should be retryable and idempotent.
2. Provider failures need normalized error mapping.

## 15) Advertisements

Priority: P2

User story:
As a merchant, I want ad slot management so I can run promotions on storefront pages.

Acceptance criteria:
1. Ad create/list/delete works with position and date windows.
2. Invalid date windows are rejected.
3. Ownership checks are enforced.
4. UI renders active ads by slot consistently.

API constraints:
1. Ad assets URLs must pass validation and safety checks.
2. Timezone handling must be explicit for starts_at and ends_at.

## 16) Team Management

Priority: P1

User story:
As an owner, I want team onboarding and permissions so I can delegate operations safely.

Acceptance criteria:
1. Team member list/add/update permissions/remove all work.
2. Permission changes apply immediately in UI and API behavior.
3. Permission matrix is visible and editable.
4. Audit events are captured for membership changes.

API constraints:
1. Permission updates must be server-authoritative.
2. Role-permission model must prevent privilege escalation.

## 17) Client Management and Client Services

Priority: P1

User story:
As an app user, I want to onboard and manage clients so I can support multiple businesses.

Acceptance criteria:
1. Client CRUD flows work with proper ownership checks.
2. Client services list/update is consistent and persisted.
3. Client activation/deactivation behaves correctly.
4. Client users only see allowed pages and data.

API constraints:
1. Multi-tenant isolation required in every client-scoped query.
2. Service toggles should map to deterministic permission checks.

## 18) Admin Console and Superuser Operations

Priority: P1

User story:
As a superuser, I want centralized admin operations so I can support users and govern the platform.

Acceptance criteria:
1. App-user CRUD and activation controls work safely.
2. Admin stats, customers, activity, websites, and feedback views are reliable.
3. Plan and workspace provisioning endpoints enforce governance.
4. Admin password change flow is secure.

API constraints:
1. All admin routes require superuser checks.
2. Destructive operations require strict validation and audit logs.

## 19) AI Chatbot (Admin + Public Website)

Priority: P2

User story:
As a user or visitor, I want an AI assistant so I can get guidance quickly.

Acceptance criteria:
1. Admin chat endpoint works with context and website metadata.
2. Public website chat endpoint works by website id.
3. Fallback responses exist when LLM provider is unavailable.
4. Unsafe prompts are filtered and logged appropriately.

API constraints:
1. Protect API keys and avoid prompt leakage of sensitive data.
2. Apply request throttling per IP/user.

## 20) Health, Reliability, and Ops Automation

Priority: P0

User story:
As a platform team, I want robust health checks and scheduler reliability so operations stay stable.

Acceptance criteria:
1. Health endpoint reports db, disk, runtime status accurately.
2. Startup migrations and scheduler initialization are deterministic.
3. Periodic monitoring and reminder jobs run and log outcomes.
4. Failures are observable with actionable logs.

API constraints:
1. Health schema changes must remain backward compatible.
2. Background jobs must be idempotent and safe on restart.

## 21) Media Recovery (Deleted Images View + Restore)

Priority: P2

User story:
As a website owner, I want to review soft-deleted images and restore valid ones so accidental deletions do not cause content loss.

Acceptance criteria:
1. A deleted-images list is available per website with delete timestamp and actor details.
2. Restore action returns image to the active picker/list for that website.
3. Restore gracefully handles missing physical files and shows actionable feedback.
4. Restore operations are auditable.

API constraints:
1. Restore endpoint must enforce strict website ownership/role checks.
2. Restore must only target previously soft-deleted media records.

## 22) Media Retention Cleanup (Scheduled Hard Delete)

Priority: P2

User story:
As a platform operator, I want a retention-based cleanup task for deleted media so storage usage stays controlled and predictable.

Acceptance criteria:
1. Configurable retention window determines when soft-deleted media is permanently removed.
2. Cleanup removes both DB records and orphaned files safely.
3. Dry-run mode reports what would be removed before execution.
4. Cleanup summary logs include counts for deleted, skipped, and failed records.

API constraints:
1. Cleanup process must be idempotent and safe across retries/restarts.
2. Cleanup must not remove active (non-deleted) media records.

---

## Additional Improvement Themes (Cross-Cutting)

1. API consistency: standard pagination, sorting, filtering, and error schema.
2. Security: enforce RBAC at API layer, harden secrets handling, and reduce overbroad CORS.
3. Observability: correlation IDs, structured logs, and endpoint-level latency/error dashboards.
4. Testing: feature-level integration tests for each P0 and P1 workflow.
5. UX resilience: empty states, retry affordances, and granular loading states.
6. Data correctness: strong validation and conflict handling for concurrent edits.

## Suggested Execution Order

1. Wave 1 (P0): Auth, Websites, Build, Staging/Deploy, Cart, Billing/Checkout, Monitoring, Health.
2. Wave 2 (P1): Edit UX hardening, Feedback, Coupons, Notifications, Team, Clients, Admin console.
3. Wave 3 (P2): Ads and Chatbot advanced quality improvements.
