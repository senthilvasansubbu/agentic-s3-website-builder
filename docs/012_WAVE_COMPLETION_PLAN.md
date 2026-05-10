# Wave Completion Plan

## Purpose
This plan defines the execution order, completion gates, and operational cadence to complete issue waves with minimal regressions.

## Current Status Snapshot

- Open issues: 67
- Priority-waved issues (critical/high/medium/low): 48
- Roadmap/feature bucketed issues: 19
- Start wave marked `status-ready`: 4 issues

## Execution Order

1. Wave 1: `wave-1-security-auth` (start first)
2. Wave 2: `wave-2-reliability-handling`
3. Wave 3: `wave-3-stability-quality`
4. Wave 4: `wave-4-medium-security-config`
5. Wave 5: `wave-5-medium-data-api`
6. Wave 6: `wave-6-medium-ux-performance`
7. Low buckets: `wave-low-maintenance`, `wave-low-opportunistic`
8. Future lanes: `wave-roadmap-future`, `wave-feature-backlog`

## Wave 1 Start Scope (Ready)

Issues currently marked `status-ready`:

1. #2 `[CRITICAL-2]` Hardcoded JWT_SECRET default in auth_service.py
2. #3 `[CRITICAL-3]` Unauthenticated /shop/finalize-image endpoint
3. #4 `[CRITICAL-4]` SQL injection risk in coupon UPDATE query (commerce.py)
4. #6 `[HIGH-6]` No startup validation for OPENAI_API_KEY

## Wave Completion Gates (Definition of Done)

A wave is complete only when all items in that wave meet all criteria below:

1. Code fix merged to `main`.
2. Automated tests added/updated for changed behavior.
3. Security-sensitive fixes include negative-path tests.
4. No blocker/sev-1 regressions introduced by the wave.
5. Documentation/ops notes updated if behavior/config changed.
6. Issues closed with evidence (PR link, test proof, verification note).

## Delivery Cadence

- Daily:
  - Track active wave burndown.
  - Keep `status-ready` queue populated for next work item.
- Weekly:
  - Promote completed wave items to closed.
  - Move next-wave candidates to `status-ready`.
  - Rebalance if newly discovered criticals appear.
- End-of-wave:
  - Run regression checks.
  - Publish wave summary (fixed issues, risk delta, follow-ups).

## Ownership Model

- Security/API owner: Wave 1 and security-heavy items in Wave 4.
- Reliability owner: Wave 2 and error-handling hardening.
- Platform quality owner: Wave 3/5 (stability/data correctness).
- Product owner: Roadmap and feature backlog wave ordering.

## Risk Controls

1. Do not start multiple critical waves simultaneously.
2. Prevent scope creep: new medium/low work enters next-wave queue.
3. Require rollback notes for schema/data touching issues.
4. Keep `no-auto-wave` for explicit exceptions only.

## Operational Labeling Rules

- Active execution starts from `wave-1-security-auth`.
- Items actively pulled into sprint/storyboard must have `status-ready`.
- Long-horizon roadmap items use `wave-roadmap-future`.
- Non-roadmap feature backlog uses `wave-feature-backlog`.

## Immediate Next Actions

1. Complete all `status-ready` Wave 1 issues first.
2. Promote the top 3 Wave 2 issues to `status-ready` once Wave 1 reaches 75% completion.
3. Keep Wave 3 on standby to avoid context switching until Wave 2 stabilizes.
