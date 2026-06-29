# Agentic S3 Website Builder

AI-powered website generation platform built on FastAPI, with a multi-agent content and design pipeline, publishing support, and operational tooling.

## Quick Links

- [Documentation Index](docs/000_DOC_INDEX.md)
- [Projects and Actions Handbook](docs/009_PROJECTS_ACTIONS_HANDBOOK.md)
- [Codebase Audit](docs/007_CODEBASE_AUDIT.md)
- [Deployment Verification](docs/010_DEPLOYMENT_VERIFICATION.md)
- [Manual Test Guide](docs/004_MANUAL_TEST_GUIDE.md)

 - [Database ERM Diagram](docs/database-erm.md)
 - [Database Table Details](docs/database-table-details.md)

## What This Repository Includes

- FastAPI application with auth, website builder, commerce, payment, monitoring, and admin APIs.
- Frontend pages served by FastAPI (login, dashboard, monitoring, console).
- Scheduled background jobs for monitoring checks and payment reminders.
- Optional integrations: S3, Stripe, Twilio, Snowflake, Tavily, Google APIs.

## Prerequisites

- Python 3.9 or later
- pip
- OpenAI API key for AI generation features
- Optional provider credentials depending on enabled features (AWS, Stripe, Twilio, Snowflake, etc.)

## Installation

1. Clone the repository.

```bash
git clone https://github.com/senthilvasansubbu/agentic-s3-website-builder.git
cd agentic-s3-website-builder
```

2. Install dependencies.

```bash
pip install -r requirements.txt
```

3. Configure the environment.

```bash
cp .env.example .env
```

Then edit .env and provide required values.

Minimum recommended values for local development:

```env
OPENAI_API_KEY=your_openai_api_key
JWT_SECRET=replace-with-a-long-random-secret
ADMIN_EMAIL=admin@websitebuilder.ai
ADMIN_PASSWORD=replace-with-strong-password
STORAGE_SECRETS_KEY=generate-this-value
```

## Run the Application

Primary entry point:

```bash
python app.py
```

Alternative (development mode with auto-reload):

```bash
uvicorn app:app --reload --port 8000
```

## Local URLs

- App root: http://localhost:8000
- Login page: http://localhost:8000/login
- Dashboard: http://localhost:8000/dashboard
- Output browser: http://localhost:8000/output-browser
- Health endpoint: http://localhost:8000/health
- OpenAPI docs: http://localhost:8000/docs

## Optional CLI Generator

The legacy interactive CLI is still available:

```bash
python main.py
```

Use this mode only when you want terminal-driven website generation instead of the web/API workflow.

## Production Run

Recommended baseline command:

```bash
uvicorn app:app --host 0.0.0.0 --port 8000 --workers 2
```

Suggested process-manager pattern (systemd-style):

```ini
[Unit]
Description=Agentic S3 Website Builder API
After=network.target

[Service]
WorkingDirectory=/opt/agentic-s3-website-builder
EnvironmentFile=/opt/agentic-s3-website-builder/.env
ExecStart=/usr/bin/python -m uvicorn app:app --host 0.0.0.0 --port 8000 --workers 2
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
```

Deployment notes:

- Put Nginx (or another reverse proxy) in front of port 8000.
- Terminate TLS at the proxy and forward traffic to the API.
- Restrict CORS_ORIGINS to your real frontend domains.
- Set strong production values for JWT_SECRET, ADMIN_PASSWORD, and STORAGE_SECRETS_KEY.
- Ensure OUTPUT_DIR, data, and logs locations are writable by the service user.
- Use external monitoring checks against /health.

## QA/Prod Health Monitoring (Ready Mode)

- End-of-wave health gate is already wired into Wave 1-6 workflows.
- Continuous QA/Prod monitor is configured in `.github/workflows/monitor-health-continuous.yml`.
- The scheduled monitor remains idle until environment URLs are set as repository secrets.

Set secrets when environments are available:

```bash
bash scripts/configure_health_monitoring_secrets.sh --qa-url https://qa.example.com --prod-url https://app.example.com
```

Manual run examples:

```bash
gh workflow run "Monitor | QA/Prod | Continuous Health" -f target=all
gh workflow run "Monitor | QA/Prod | Continuous Health" -f target=qa
gh workflow run "Monitor | QA/Prod | Continuous Health" -f target=prod
```

## Project Structure

```text
agentic-s3-website-builder/
├── app.py                    # FastAPI application entrypoint
├── main.py                   # Legacy interactive CLI entrypoint
├── api/                      # API routes
├── services/                 # Business logic/services
├── agents/                   # Multi-agent generation pipeline
├── config/                   # Settings and configuration
├── database/                 # Migrations and persistence helpers
├── frontend/                 # HTML/CSS/JS assets/pages
├── tests/                    # Automated tests
├── docs/                     # Project documentation
├── output/                   # Generated/published site artifacts
└── logs/                     # Runtime logs
```

## Notes

- The app runs database migrations at startup.
- Monitoring and payment reminder schedulers start during app startup.
- CORS defaults to localhost origins unless CORS_ORIGINS is set.

For operational processes (issue taxonomy, waves, automation, backlog and project hygiene), see [Projects and Actions Handbook](docs/009_PROJECTS_ACTIONS_HANDBOOK.md).