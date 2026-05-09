#!/usr/bin/env bash
# Create GitHub issues for features and roadmap items from the CEO docs
set -e
REPO="senthilvasansubbu/agentic-s3-website-builder"

# Create extra labels for features/roadmap
gh label create "roadmap" --color "8B5CF6" --description "Planned roadmap item" 2>/dev/null || true
gh label create "enhancement" --color "84B6EB" --description "Feature enhancement" 2>/dev/null || true
gh label create "billing" --color "F59E0B" --description "Billing & payments" 2>/dev/null || true
gh label create "commerce" --color "10B981" --description "Commerce/e-commerce" 2>/dev/null || true
gh label create "auth" --color "EF4444" --description "Authentication" 2>/dev/null || true
gh label create "hosting" --color "3B82F6" --description "Hosting & deployment" 2>/dev/null || true
gh label create "monitoring" --color "6366F1" --description "Monitoring & analytics" 2>/dev/null || true
gh label create "ai-agent" --color "EC4899" --description "AI agent pipeline" 2>/dev/null || true
gh label create "q3-2026" --color "DDD6FE" --description "Roadmap: Q3 2026" 2>/dev/null || true
gh label create "q4-2026" --color "C4B5FD" --description "Roadmap: Q4 2026" 2>/dev/null || true
gh label create "q1-2027" --color "A78BFA" --description "Roadmap: Q1 2027" 2>/dev/null || true
gh label create "q2-2027" --color "8B5CF6" --description "Roadmap: Q2 2027" 2>/dev/null || true

create() {
  local title="$1" labels="$2" body="$3"
  gh issue create --repo "$REPO" --title "$title" --label "$labels" --body "$body"
  sleep 0.5
}

echo "=== CURRENT PLATFORM FEATURES (gaps/incomplete) ==="

create "[FEATURE] Custom domain mapping for published sites" \
  "feature,hosting,enhancement" \
  "**Source:** PPT Slide 7 — Hosting & DevOps: 'Custom domain support'
**Word Doc:** Section 7.3 Production Recommendations

**Current State:** Platform publishes to S3 URLs only (e.g., \`s3.amazonaws.com/bucket/site/index.html\`). Custom domain mapping is listed as a feature but not fully implemented.

**Required:**
- Allow clients to enter a custom domain (e.g., \`www.myclinic.com\`) in the dashboard
- Generate DNS instructions (CNAME → S3/CloudFront)
- Validate domain ownership via TXT record check
- Update \`websites\` table with \`domain\` field (already exists in schema)
- Serve correct CORS headers for custom domains

**Acceptance Criteria:** Client can configure a custom domain from the dashboard and their site is accessible at that domain."

create "[FEATURE] Uptime alerting — WhatsApp/Email notifications when site goes down" \
  "feature,monitoring,enhancement" \
  "**Source:** PPT Slide 7 — 'Uptime alerting'
**Word Doc:** Section 8 — Monitoring & Analytics

**Current State:** Monitoring service runs scheduled checks and stores results but alerting (notifying the client) when a site goes down is not implemented.

**Required:**
- When uptime check fails, trigger notification via WhatsApp (Twilio) and/or Email (SendGrid)
- Configurable alert threshold (e.g., 2 consecutive failures before alerting)
- Alert cooldown to prevent notification spam
- Per-client alert preferences (email / WhatsApp / both)
- Recovery notification when site comes back up

**Acceptance Criteria:** Client receives WhatsApp/email alert within 10 minutes of site going down."

create "[FEATURE] Real-time health dashboard with metrics" \
  "feature,monitoring,enhancement" \
  "**Source:** PPT Slide 7 — 'Real-time health dashboard'
**Word Doc:** Section 8.1, 8.2

**Current State:** \`monitoring.html\` exists but analytics data queryable only via admin console. No real-time charts or aggregated metrics visible to clients.

**Required:**
- Dashboard widget showing: uptime %, avg response time, last check timestamp
- Admin panel: platform-wide metrics (total sites, active clients, build counts)
- Analytics charts: websites generated per day, publish rate, chatbot sessions
- Data from \`analytics_service.py\` surfaced in UI

**Acceptance Criteria:** Dashboard shows live uptime status and 30-day analytics charts."

create "[FEATURE] Stripe Pro & Enterprise subscription plans with plan-gating" \
  "feature,billing,enhancement" \
  "**Source:** PPT Slide 7 — 'Pro & Enterprise plans'
**Word Doc:** Section 9.1

**Current State:** Stripe checkout session creation exists but plan-based feature gating (limiting sites/features by plan tier) is incomplete.

**Required:**
- Define clear plan limits: Free (1 site), Pro (10 sites), Enterprise (unlimited)
- Enforce limits at \`POST /website-builder/generate\` before agent run
- Plan upgrade prompt in dashboard when limit reached
- Stripe webhook updates plan tier in DB on payment success/cancellation
- Display current plan and usage in dashboard

**Acceptance Criteria:** Users on Free plan cannot generate more than 1 site; upgrade flow works end-to-end."

create "[FEATURE] Shopping cart embeddable in generated websites" \
  "feature,commerce,enhancement" \
  "**Source:** PPT Slide 7 — 'Shopping cart module'
**Word Doc:** Section 9.2

**Current State:** Shopping cart API exists (\`/shopping_cart\`) but cart state is not embedded/injected into generated website HTML.

**Required:**
- Developer Agent should include cart UI (add to cart, cart drawer, checkout button) in generated HTML when commerce is requested
- Cart state connected to \`/shopping_cart\` API endpoints
- Product catalogue data from \`/commerce/catalogue\` rendered in website
- Mobile-responsive cart component

**Acceptance Criteria:** Generated e-commerce site has working add-to-cart and cart drawer connected to the API."

create "[FEATURE] Catalogue scraper — import products from existing website URL" \
  "feature,commerce,enhancement" \
  "**Source:** PPT Slide 7 — 'Catalogue scraper'
**Word Doc:** Section 9.2

**Current State:** \`tools/catalog_scraper.py\` exists but is not wired into the dashboard or the agent pipeline as a user-facing feature.

**Required:**
- Dashboard input: 'Import products from URL'
- \`catalog_scraper.py\` scrapes product name, price, image, description
- Imported products stored in client's catalogue
- Agent uses catalogue data when generating an e-commerce site

**Acceptance Criteria:** Client can paste a URL and have products automatically imported into their catalogue."

create "[FEATURE] Multi-language website generation (i18n content)" \
  "feature,ai-agent,enhancement" \
  "**Source:** PPT Slide 7 — AI Capabilities: 'Multi-language content'
**Word Doc:** Section 4.4 Content Agent

**Current State:** Content Agent generates copy in English only. Multi-language is listed as a capability but not implemented.

**Required:**
- Client can select target language(s) during website generation
- Content Agent generates copy in the selected language
- Theme Agent ensures RTL support for Arabic/Hebrew
- Language selector stored in \`websites\` table

**Acceptance Criteria:** Client can generate a fully Hindi, Tamil, Arabic, or French website from an English prompt."

create "[FEATURE] Social search (Twitter/X) integration for content enrichment" \
  "feature,ai-agent,enhancement" \
  "**Source:** PPT Slide 7 — 'Social search (Twitter)'
**Word Doc:** Section 4.4 — Content Agent Tools

**Current State:** \`tools/social_media_search.py\` exists but RapidAPI key is optional and social data is not consistently passed to Content Agent.

**Required:**
- Wire \`social_media_search\` tool into Content Agent's tool list
- Use trending posts/hashtags in the target industry to inform copy tone and keywords
- Graceful fallback if \`RAPIDAPI_KEY\` not set

**Acceptance Criteria:** Content Agent uses social search results when RAPIDAPI_KEY is configured."

create "[FEATURE] White-label multi-tenant agency portal" \
  "feature,enhancement" \
  "**Source:** PPT Slide 8 — 'Multi-tenant web agencies'
**Word Doc:** Section 1.1 Target Audience — 'Agency owners looking for a white-label, multi-tenant website builder'

**Current State:** Multi-tenancy exists (clients are isolated) but no white-label branding or agency-level management dashboard.

**Required:**
- Agency owner dashboard: manage all client accounts from one view
- Custom branding: agency logo/colours on client-facing pages
- Sub-account creation: agency creates client accounts on their behalf
- Usage reports: sites built per client, last activity, billing status

**Acceptance Criteria:** Agency owner can log in, see all their clients, create new sub-accounts, and white-label the UI."

create "[FEATURE] Website scraper — use reference URL to guide generation" \
  "feature,ai-agent,enhancement" \
  "**Source:** PPT Slide 5 — Requirements Analyst Tools: website_scraper
**Word Doc:** Section 3 Step 2 — 'The system accepts reference URLs'

**Current State:** \`tools/website_scraper.py\` exists but reference URL scraping in the chatbot/dashboard flow is not consistently connected to the Requirements Analyst.

**Required:**
- Dashboard input: 'Reference website URL (optional)'
- Requirements Analyst scrapes the URL and extracts design/content patterns
- Scraped data influences design spec and content generation
- Error handling when URL is unreachable

**Acceptance Criteria:** Providing a reference URL produces a website visually inspired by the reference."

create "[FEATURE] Google Drive image storage backend" \
  "feature,hosting,enhancement" \
  "**Source:** PPT Slide 10 — 'Google Drive (optional image store)'
**Word Doc:** Section 7.2 Env Vars

**Current State:** \`services/image_service.py\` has Google Drive backend references but it silently fails when libraries or credentials are missing.

**Required:**
- Complete Google Drive integration for image upload/storage
- Dashboard toggle to select image backend: S3 / Google Drive / Local
- Store selection in client settings
- Validate credentials on save, show clear error if misconfigured

**Acceptance Criteria:** Client images are stored and served from Google Drive when that backend is selected."

echo ""
echo "=== ROADMAP ITEMS ==="

create "[ROADMAP Q3-2026] Custom domain mapping (CNAME → S3/CloudFront)" \
  "roadmap,hosting,q3-2026" \
  "**Source:** Word Doc Section 10 — Suggested Roadmap Q3 2026

Map client custom domains to their hosted S3 sites via CNAME records pointing to CloudFront distribution.

**Scope:**
- CloudFront distribution per published site (or shared with path routing)
- Domain verification via TXT DNS record
- SSL certificate auto-provisioning via AWS ACM
- Dashboard UI for domain management

**Dependencies:** Issue #49 (Custom domain mapping feature)

**Target:** Q3 2026"

create "[ROADMAP Q3-2026] White-label reseller portal for agencies" \
  "roadmap,enhancement,q3-2026" \
  "**Source:** Word Doc Section 10 — Suggested Roadmap Q3 2026

Enable web agencies to resell the platform under their own brand with custom logos, colours, and domain.

**Scope:**
- Agency admin portal with sub-account management
- Custom branding config stored per agency
- Branded email templates (OTP, welcome, invoice)
- Agency billing: flat fee or per-client seat pricing

**Dependencies:** Issue #57 (White-label agency portal feature)

**Target:** Q3 2026"

create "[ROADMAP Q3-2026] AI image generation integration (DALL·E / Stable Diffusion)" \
  "roadmap,ai-agent,q3-2026" \
  "**Source:** Word Doc Section 10 — Suggested Roadmap Q3 2026

Integrate image generation so the Developer Agent can produce custom hero images, icons, and illustrations for each site.

**Scope:**
- Developer Agent calls DALL·E API for hero/banner images based on design spec
- Stable Diffusion as fallback/cost-optimized alternative
- Generated images stored in client image backend (S3/Drive)
- Image generation cost included in plan limits

**Target:** Q3 2026"

create "[ROADMAP Q4-2026] Mobile app companion (iOS/Android) for on-the-go edits" \
  "roadmap,enhancement,q4-2026" \
  "**Source:** Word Doc Section 10 — Suggested Roadmap Q4 2026

Native mobile app allowing clients to manage sites, chat with the AI builder, and monitor uptime from their phone.

**Scope:**
- React Native or Flutter app
- Chat interface for requesting website changes
- Site status and uptime at a glance
- Push notifications for downtime alerts
- Image upload from camera roll

**Target:** Q4 2026"

create "[ROADMAP Q4-2026] A/B testing module for landing page variants" \
  "roadmap,enhancement,q4-2026" \
  "**Source:** Word Doc Section 10 — Suggested Roadmap Q4 2026

Allow clients to generate two variants of a landing page and split-test them to find the higher-converting version.

**Scope:**
- Agent generates Variant A and Variant B from the same prompt with different layouts/CTAs
- Traffic split logic (50/50 or configurable)
- Analytics: conversion events, click tracking per variant
- Auto-select winner after statistical significance reached

**Target:** Q4 2026"

create "[ROADMAP Q1-2027] Multi-language website generation (i18n)" \
  "roadmap,ai-agent,q1-2027" \
  "**Source:** Word Doc Section 10 — Suggested Roadmap Q1 2027

Full i18n support: generate websites in multiple languages simultaneously, with RTL support.

**Scope:**
- Content Agent generates copy in all selected languages
- Frontend language switcher component in generated site
- RTL CSS for Arabic/Hebrew/Urdu
- Language metadata stored in \`websites\` table

**Dependencies:** Issue #55 (Multi-language feature)

**Target:** Q1 2027"

create "[ROADMAP Q1-2027] CRM integration — HubSpot and Salesforce lead capture" \
  "roadmap,enhancement,q1-2027" \
  "**Source:** Word Doc Section 10 — Suggested Roadmap Q1 2027

Contact forms on generated websites push leads directly into the client's CRM.

**Scope:**
- CRM connector service (HubSpot API / Salesforce REST API)
- Client configures CRM API key in dashboard secret store
- Developer Agent injects form submission hook in generated HTML
- Lead routing: map form fields to CRM contact properties
- Webhook fallback for unsupported CRMs

**Target:** Q1 2027"

create "[ROADMAP Q2-2027] Self-serve plan upgrades and usage-based billing" \
  "roadmap,billing,q2-2027" \
  "**Source:** Word Doc Section 10 — Suggested Roadmap Q2 2027

Allow clients to upgrade/downgrade plans and pay based on actual usage (sites generated, pages published, AI tokens consumed).

**Scope:**
- Stripe metered billing per AI generation job
- In-dashboard plan upgrade/downgrade flow (no support ticket needed)
- Usage dashboard: tokens used this month, sites published, overages
- Automatic invoice generation with itemized AI usage
- Dunning management for failed payments

**Target:** Q2 2027"

echo ""
echo "✅ All feature and roadmap issues created!"
