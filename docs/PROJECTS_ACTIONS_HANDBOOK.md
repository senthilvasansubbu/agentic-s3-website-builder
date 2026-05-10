# Projects and Actions Handbook

## Purpose
This handbook is the operational reference for managing issue tracking with GitHub Projects and GitHub Actions in this repository.

It documents:
- How to structure work from intake to delivery.
- How to use issue taxonomies and wave labels.
- How automation enforces consistency.
- How to validate workflows and maintain the system over time.

---

## 1. Operating Model Overview

### 1.1 Lifecycle
Use this common lifecycle for all work items:
1. Intake: Issue is created with minimal required details.
2. Classification: Priority and domain labels are applied.
3. Wave Assignment: Automation or manual triage assigns one wave label.
4. Planning: Item is moved to active project lanes/sprint plan.
5. Execution: Work is implemented and linked PRs are tracked.
6. Validation: Tests, review, and acceptance criteria are verified.
7. Closure: Issue is closed with traceability notes.
8. Backlog Hygiene: Re-open, demote, or re-wave as needed.

### 1.2 Why this model works
- Priority labels communicate urgency.
- Domain labels communicate ownership and technical area.
- Wave labels communicate delivery sequence.
- Project views communicate status and accountability.

---

## 2. GitHub Projects Handbook

## 2.1 Project structure recommendations
Create one project board for engineering execution with views tuned for different audiences.

Recommended views:
1. Intake Queue: New/untriaged items.
2. Sprint / Active Wave: Current execution set.
3. Backlog: Deferred work by priority/wave.
4. Bugs: Label = bug or severity-focused filters.
5. Roadmap: Quarter labels and feature/roadmap labels.
6. Review Needed: Items with linked PRs awaiting review.
7. My Items: Items assigned to current user.

## 2.2 Suggested project fields
Use these custom fields in GitHub Projects:
- Status: Backlog, Ready, In Progress, In Review, Done.
- Wave: Wave 1..6 + Low Maintenance/Opportunistic.
- Priority: Critical, High, Medium, Low.
- Domain: API, Security, Frontend, Database, Config, Test, etc.
- Sprint/Iteration: Current sprint tag.
- Owner: Assignee.
- Target Date: Planned completion date.

## 2.3 Usage patterns by stakeholder
- Engineering leads: Prioritize by Priority + Wave + Risk.
- Developers: Work from My Items + Active Wave.
- Reviewers: Work from Review Needed view.
- Product/planning: Use Roadmap + Backlog trends.

## 2.4 Maintenance cadence for Projects
Daily:
1. Move completed cards to Done.
2. Reclassify blocked items.

Weekly:
1. Triage new issues.
2. Rebalance wave scope.
3. Update sprint/iteration.

Monthly:
1. Backlog cleanup (duplicates, stale, out-of-scope).
2. Taxonomy quality check (missing labels, conflicting labels).

---

## 3. Taxonomy Reference

## 3.1 Priority labels
- critical: Fix immediately.
- high: Fix this sprint.
- medium: Plan for next sprint/wave.
- low: Backlog/opportunistic.

## 3.2 Domain labels (examples)
- security
- auth
- api
- frontend
- database
- config
- error-handling
- performance
- test
- code-quality

## 3.3 Wave labels in use
Critical/High waves:
- wave-1-security-auth
- wave-2-reliability-handling
- wave-3-stability-quality

Medium waves:
- wave-4-medium-security-config
- wave-5-medium-data-api
- wave-6-medium-ux-performance

Low waves:
- wave-low-maintenance
- wave-low-opportunistic

Manual override:
- no-auto-wave

## 3.4 Label policy rules
1. Every issue should have exactly one priority label.
2. Every issue should have at least one domain label.
3. Every issue should have at most one active wave label.
4. no-auto-wave disables automatic wave assignment.
5. Manual assignment should be used only when automation logic is intentionally bypassed.

---

## 4. GitHub Actions Handbook

## 4.1 Workflow in repository
Workflow file:
- .github/workflows/wave-labeling.yml

Purpose:
- Automatically assign and normalize wave labels on issue events.
- Keep one-wave-only consistency.
- Add an audit comment when wave changes.

## 4.2 Trigger events
The workflow listens to issue events:
- opened
- edited
- labeled
- unlabeled
- reopened

## 4.3 Execution logic summary
1. Read issue labels.
2. Exit if no-auto-wave is present.
3. Exit if no priority label (critical/high/medium/low).
4. Determine target wave using priority + domain mapping.
5. Remove non-target wave labels.
6. Add target wave if missing.
7. Post audit comment when wave changed.

Audit comment prefix used for filtering:
- [Wave Bot] Wave assignment updated by automation.

## 4.4 Mapping matrix
Critical/High:
- security/api/auth/config -> wave-1-security-auth
- error-handling -> wave-2-reliability-handling
- frontend/database/performance/test -> wave-3-stability-quality
- fallback critical -> wave-1-security-auth
- fallback high -> wave-2-reliability-handling

Medium:
- security/auth/config -> wave-4-medium-security-config
- api/database -> wave-5-medium-data-api
- fallback -> wave-6-medium-ux-performance

Low:
- security/auth/config/database/api/error-handling -> wave-low-maintenance
- fallback -> wave-low-opportunistic

## 4.5 Validation checklist for Actions
After any workflow change:
1. Create a test issue with a known label set.
2. Confirm expected wave is assigned.
3. Confirm conflicting wave labels are removed.
4. Confirm audit comment appears only on actual wave change.
5. Apply no-auto-wave and verify no automation updates happen.
6. Remove no-auto-wave and verify automation resumes.

---

## 5. Issue Creation Standards

## 5.1 Required issue template fields
- Problem statement.
- Expected behavior.
- Current behavior.
- Impact/risk.
- Reproduction steps (if bug).
- Acceptance criteria.
- Suggested labels (priority + domain).

## 5.2 Suggested title format
- [PRIORITY-ID] Short, concrete problem summary

Examples:
- [HIGH-101] Checkout API returns 500 on missing address
- [MEDIUM-214] Missing cleanup docs for SSE stream connections

## 5.3 Acceptance criteria quality
Good acceptance criteria are:
- Observable.
- Testable.
- Specific to edge cases.

Example:
- Given unauthenticated user, when calling /shop/finalize-image, response is 401 and no data is modified.

---

## 6. Board Workflow Examples

## 6.1 Example A: Critical security issue
Scenario:
- Labels: critical, security, api

Expected automation:
- Assigned to wave-1-security-auth.
- Any other wave label is removed.
- Audit comment is posted with previous/new wave.

Project handling:
1. Move to Ready.
2. Assign owner.
3. Pull into Active Wave view.
4. Attach PR and review checklist.

## 6.2 Example B: Medium data issue
Scenario:
- Labels: medium, database

Expected automation:
- Assigned to wave-5-medium-data-api.

Project handling:
1. Place in upcoming sprint bucket.
2. Link migration validation subtasks.
3. Add rollback verification notes before closure.

## 6.3 Example C: Low maintenance issue
Scenario:
- Labels: low, error-handling

Expected automation:
- Assigned to wave-low-maintenance.

Project handling:
1. Keep in backlog.
2. Pull opportunistically when touching same service.

---

## 7. Maintenance and Governance

## 7.1 Weekly triage agenda
1. Review all new issues in Intake Queue.
2. Ensure each issue has: priority + domain + wave.
3. Re-prioritize based on production risk.
4. Confirm active wave load fits capacity.
5. Escalate blocked issues.

## 7.2 Monthly governance agenda
1. Check label hygiene and duplicates.
2. Validate automation behavior against recent issues.
3. Review board views for stale filters.
4. Compare roadmap labels vs actual progress.
5. Archive obsolete issues and update taxonomy policy.

## 7.3 Change management for taxonomy/workflow
When taxonomy rules change:
1. Update this handbook.
2. Update workflow mapping logic.
3. Bulk-relabel existing issues if needed.
4. Communicate changes in team channel.
5. Validate using the checklist in section 4.5.

---

## 8. Troubleshooting Guide

## 8.1 Issue did not get a wave label
Possible causes:
- Missing priority label.
- no-auto-wave label present.
- Workflow failure/permissions problem.

Checks:
1. Confirm labels include one of critical/high/medium/low.
2. Confirm no-auto-wave is absent.
3. Check Actions run logs for wave-labeling workflow.

## 8.2 Wrong wave was assigned
Possible causes:
- Domain labels drove mapping unexpectedly.
- Missing expected domain label.

Resolution:
1. Add/correct domain label(s).
2. Remove incorrect wave label manually if needed.
3. Add no-auto-wave for custom handling.

## 8.3 Too many bot comments
Possible causes:
- Frequent label churn.

Resolution options:
1. Reduce manual relabeling churn.
2. Introduce stricter triage before label updates.
3. Optionally revise workflow to comment only for cross-family wave changes.

---

## 9. Operational Commands (CLI Examples)

## 9.1 List labels
```bash
gh label list --repo senthilvasansubbu/agentic-s3-website-builder --limit 300
```

## 9.2 List medium issues with current labels
```bash
gh issue list \
  --repo senthilvasansubbu/agentic-s3-website-builder \
  --state open \
  --label medium \
  --limit 200 \
  --json number,title,labels
```

## 9.3 Add manual override
```bash
gh issue edit 123 \
  --repo senthilvasansubbu/agentic-s3-website-builder \
  --add-label no-auto-wave
```

## 9.4 Remove manual override
```bash
gh issue edit 123 \
  --repo senthilvasansubbu/agentic-s3-website-builder \
  --remove-label no-auto-wave
```

## 9.5 Manually set wave label (exception handling)
```bash
gh issue edit 123 \
  --repo senthilvasansubbu/agentic-s3-website-builder \
  --add-label wave-2-reliability-handling
```

---

## 10. Quick Start Summary

For day-1 adoption:
1. Ensure issue templates require priority and domain labels.
2. Use project views: Intake, Active Wave, Backlog, Review Needed, My Items.
3. Let automation assign wave labels.
4. Use no-auto-wave only when intentionally overriding automation.
5. Run weekly triage and monthly governance routines.

This handbook should be treated as living documentation and updated whenever taxonomy, waves, or workflow logic changes.
