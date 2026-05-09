# 🚀 Agentic AI Website Builder

A full-stack, conversational AI platform that designs, generates, and hosts responsive websites using a multi-agent architecture powered by **CrewAI** and **OpenAI GPT-4.1-mini**. The platform exposes a **FastAPI** backend with a browser-based dashboard, supports multi-tenant client management, OTP authentication, Stripe billing, AWS S3 hosting, and real-time monitoring.

## ✨ Features

- **🤖 Multi-Agent Pipeline**: Requirements Analyst → UI/UX Designer → Theme Builder → Content Agent → Web Developer — each agent refines the output before handing off to the next
- **💬 Conversational Chatbot**: Describe your website in natural language; agents iterate until the result matches your vision
- **🎨 Theme & Design System**: Dynamic theme generation with colour palettes, typography, and layout rules
- **💻 Full Code Generation**: Production-ready HTML/CSS/JavaScript with inline assets
- **☁️ AWS S3 Hosting**: One-click publish to S3 with staging and published environments
- **🔐 JWT Authentication + OTP**: Email (SendGrid/SMTP) and SMS (Twilio) OTP; role-based access (superuser / client)
- **💳 Stripe Billing**: Subscription plans (Pro / Enterprise), webhook handling, payment reminders
- **🛒 Commerce Module**: Shopping cart, product catalogue, catalog scraper
- **📊 Monitoring & Analytics**: Scheduled uptime checks, platform health dashboard, analytics service
- **🗄️ Dual Database Support**: Snowflake (production) with automatic SQLite fallback for local development
- **🔔 Notifications**: In-app + WhatsApp (Twilio) notifications
- **🌐 Web & Social Search**: Tavily web search and RapidAPI Twitter search to enrich content

## 📋 Prerequisites

- Python 3.9+
- OpenAI API Key
- (Optional) AWS credentials for S3 hosting
- (Optional) Snowflake account — SQLite is used automatically if not configured
- (Optional) Stripe, Twilio, SendGrid for billing, SMS, and email OTP

## 🛠️ Installation

1. **Clone the repository**:
   ```bash
   git clone https://github.com/senthilvasansubbu/agentic-s3-website-builder.git
   cd agentic-s3-website-builder
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment variables** — copy the example and fill in your values:
   ```bash
   cp .env.example .env
   ```
   Key variables:
   ```env
   OPENAI_API_KEY=your_openai_api_key_here
   OPENAI_MODEL=gpt-4.1-mini

   # AWS S3 (optional)
   AWS_ACCESS_KEY_ID=
   AWS_SECRET_ACCESS_KEY=
   AWS_REGION=us-east-1
   S3_BUCKET_NAME=

   # JWT
   JWT_SECRET=change-me-to-a-long-random-secret-before-production

   # Admin superuser (created on first run)
   ADMIN_EMAIL=admin@websitebuilder.ai
   ADMIN_PASSWORD=Admin@1234
   ADMIN_NAME=Super Admin

   # Secret store encryption key
   # Generate: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
   STORAGE_SECRETS_KEY=
   ```
   See `.env.example` for the full list of options.

## 🚀 Running the Server

```bash
python app.py
```

The API server starts at **http://localhost:8000**.  
Open the dashboard at **http://localhost:8000/dashboard** in your browser.

> If Snowflake credentials are not set, the platform automatically falls back to SQLite at `data/website_builder.db`.

## 🌐 API Overview

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/auth/login` | Login with email + password, returns JWT |
| `POST` | `/auth/otp/send` | Send OTP via email or SMS |
| `POST` | `/website-builder/generate` | Generate a website from a prompt |
| `POST` | `/website-builder/publish` | Publish staging site to S3 |
| `GET`  | `/website-builder/sites` | List all client websites |
| `GET`  | `/monitoring/status` | Platform health & uptime |
| `POST` | `/payment/checkout` | Create Stripe checkout session |
| `POST` | `/commerce/cart` | Add item to shopping cart |
| `GET`  | `/admin/clients` | List all clients (superuser only) |

Full interactive API docs available at **http://localhost:8000/docs**.

## 🗂️ Project Structure

```
agentic-s3-website-builder/
├── app.py                        # FastAPI application entry point
├── main.py                       # CLI entry point (standalone agent run)
├── requirements.txt
├── .env.example                  # All supported environment variables
│
├── agents/
│   ├── crew.py                   # CrewAI crew orchestration
│   ├── requirements_analyst.py   # Parses and clarifies user requirements
│   ├── designer_agent.py         # UI/UX design specification
│   ├── theme_agent.py            # Colour palette & typography system
│   ├── content_agent.py          # Copywriting & content generation
│   └── developer_agent.py        # HTML/CSS/JS code generation
│
├── api/routes/
│   ├── auth.py                   # Login, OTP, JWT refresh
│   ├── website_builder.py        # Generate, stage, publish websites
│   ├── chatbot.py                # Conversational website builder chat
│   ├── clients.py                # Client management
│   ├── payment.py                # Stripe billing & webhooks
│   ├── commerce.py               # Product catalogue & shopping cart
│   ├── monitoring.py             # Uptime & health checks
│   ├── console.py                # Admin console API
│   ├── admin.py                  # Superuser operations
│   ├── feedback.py               # User feedback
│   ├── team.py                   # Team management
│   └── shopping_cart.py          # Cart operations
│
├── services/
│   ├── auth_service.py           # JWT, password hashing, OTP logic
│   ├── hosting_service.py        # S3 staging & publish workflow
│   ├── payment_service.py        # Stripe integration
│   ├── payment_reminder_service.py
│   ├── monitoring_service.py     # Scheduled uptime checks
│   ├── notification_service.py   # In-app & WhatsApp notifications
│   ├── otp_service.py            # Email & SMS OTP delivery
│   ├── analytics_service.py      # Usage analytics
│   ├── image_service.py          # Image upload & processing
│   ├── currency_service.py       # Multi-currency support
│   └── secret_store.py           # Encrypted credential storage
│
├── tools/
│   ├── html_generator.py         # Writes generated HTML to disk
│   ├── s3_uploader.py            # AWS S3 upload helper
│   ├── theme_builder.py          # Builds CSS theme from design spec
│   ├── website_scraper.py        # Scrapes reference URLs for context
│   ├── catalog_scraper.py        # Scrapes product catalogues
│   ├── web_search.py             # Tavily web search
│   └── social_media_search.py    # RapidAPI Twitter search
│
├── database/
│   ├── snowflake_client.py       # Snowflake connector
│   └── migrations.py             # Schema migrations (Snowflake + SQLite)
│
├── config/
│   └── settings.py               # Pydantic settings loaded from .env
│
├── frontend/
│   ├── login.html                # Login page
│   ├── dashboard.html            # Main client dashboard
│   ├── dashboard.js              # Dashboard interactivity
│   ├── console.html              # Admin console UI
│   ├── monitoring.html           # Monitoring dashboard
│   ├── logs.html                 # Log viewer
│   └── toast.js                  # Toast notification helper
│
├── output/
│   ├── staging/                  # Per-site staging builds
│   └── published/                # Live published snapshots
│
└── tests/                        # pytest test suite
```

## 📦 Key Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| `crewai` | 1.14.1 | Multi-agent orchestration |
| `openai` | 2.32.0 | GPT-4.1-mini API client |
| `fastapi` | 0.115.12 | REST API framework |
| `uvicorn` | 0.34.3 | ASGI server |
| `python-dotenv` | 1.1.1 | `.env` loading |
| `boto3` | 1.42.90 | AWS S3 SDK |
| `stripe` | 12.1.0 | Payment processing |
| `twilio` | 9.6.3 | SMS & WhatsApp OTP |
| `PyJWT` | 2.10.1 | JWT authentication |
| `bcrypt` | 4.3.0 | Password hashing |
| `cryptography` | 44.0.2 | Secret store encryption |
| `snowflake-connector-python` | 3.14.0 | Snowflake database |
| `tavily-python` | 0.7.4 | Web search for content |
| `apscheduler` | 3.10+ | Scheduled monitoring jobs |
| `pydantic[email]` | 2.11.3 | Settings & validation |

## 🏗️ How It Works

1. **Requirements Analyst** — parses your prompt and extracts structured requirements (industry, pages, features, tone).
2. **Designer Agent** — produces a detailed design specification: layout, colour scheme, typography, component list.
3. **Theme Agent** — converts the design spec into a reusable CSS theme (variables, utility classes).
4. **Content Agent** — writes copy for each section based on the business context and web/social search results.
5. **Developer Agent** — assembles everything into a single, production-ready HTML/CSS/JS file.
6. **Hosting Service** — saves the output to `output/staging/<slug>/` and optionally publishes to AWS S3 (`output/published/`).
7. **Monitoring Service** — runs scheduled checks against published URLs and reports uptime via the dashboard.