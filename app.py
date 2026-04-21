"""
Agentic S3 Website Builder — FastAPI application entry point.

Run:
    uvicorn app:app --reload --port 8000

Or:
    python app.py
"""
import os
import logging
import logging.config
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv
from config.settings import settings

load_dotenv()

# ── Logging setup ──────────────────────────────────────────────────────────────
logging.config.dictConfig({
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "detailed": {
            "format": "%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
            "datefmt": "%Y-%m-%d %H:%M:%S",
        }
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "detailed",
            "stream": "ext://sys.stdout",
        },
        "file": {
            "class": "logging.handlers.RotatingFileHandler",
            "formatter": "detailed",
            "filename": "logs/website_builder.log",
            "maxBytes": 5_000_000,
            "backupCount": 3,
            "encoding": "utf-8",
        },
    },
    "loggers": {
        "website_builder": {"level": "DEBUG", "handlers": ["console", "file"], "propagate": False},
    },
    "root": {"level": "INFO", "handlers": ["console"]},
})

os.makedirs("logs", exist_ok=True)

from api.routes.auth import router as auth_router
from api.routes.website_builder import router as website_router
from api.routes.shopping_cart import router as shop_router
from api.routes.payment import router as payment_router
from api.routes.admin import router as admin_router
from api.routes.console import router as console_router
from api.routes.chatbot import router as chatbot_router
from api.routes.feedback import router as feedback_router
from api.routes.monitoring import router as monitoring_router
from api.routes.team import router as team_router
from api.routes.commerce import router as commerce_router
from api.routes.clients import router as clients_router

app = FastAPI(
    title="Agentic AI Website Builder",
    description=(
        "A SaaS platform that uses multi-agent AI (CrewAI + OpenAI) to auto-build "
        "customisable websites with shopping carts, payment gateways, multi-theme support, "
        "web/social content research, and Snowflake-backed analytics."
    ),
    version="2.0.0",
)

# CORS — origins controlled by CORS_ORIGINS env var (see config/settings.py)
# Default: localhost only. Set CORS_ORIGINS in .env for staging/production.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Accept", "X-Requested-With"],
)

# ── Routers ────────────────────────────────────────────────────────────────────
app.include_router(auth_router,    prefix="/api/v1")
app.include_router(website_router, prefix="/api/v1")
app.include_router(shop_router,    prefix="/api/v1")
app.include_router(payment_router, prefix="/api/v1")
app.include_router(admin_router,   prefix="/api/v1")
app.include_router(console_router, prefix="/api/v1")
app.include_router(chatbot_router, prefix="/api/v1")
app.include_router(feedback_router,  prefix="/api/v1")
app.include_router(monitoring_router, prefix="/api/v1")
app.include_router(team_router,       prefix="/api/v1")
app.include_router(commerce_router,   prefix="/api/v1")
app.include_router(clients_router,    prefix="/api/v1")

# ── Static file serving ────────────────────────────────────────────────────────
# Uploaded product images are stored in data/uploads and served at /static/uploads/
from fastapi.staticfiles import StaticFiles as _StaticFiles
_uploads_dir = Path(__file__).parent / "data" / "uploads"
_uploads_dir.mkdir(parents=True, exist_ok=True)
app.mount("/static/uploads", _StaticFiles(directory=str(_uploads_dir)), name="uploads")

# Serve built/staged/published websites from the output folder
_output_dir = Path(__file__).parent / "output"
_output_dir.mkdir(parents=True, exist_ok=True)
app.mount("/output", _StaticFiles(directory=str(_output_dir)), name="output")

# ── Frontend pages ─────────────────────────────────────────────────────────────
FRONTEND = Path(__file__).parent / "frontend"

def _read_html(name: str) -> str:
    return (FRONTEND / name).read_text()

@app.get("/login", response_class=HTMLResponse, include_in_schema=False)
async def login_page():
    return HTMLResponse(_read_html("login.html"))

@app.get("/console", response_class=HTMLResponse, include_in_schema=False)
async def console_page():
    return HTMLResponse(_read_html("console.html"))

@app.get("/dashboard", response_class=HTMLResponse, include_in_schema=False)
async def dashboard_page():
    return HTMLResponse(_read_html("dashboard.html"))

@app.get("/monitoring", response_class=HTMLResponse, include_in_schema=False)
async def monitoring_page():
    return HTMLResponse(_read_html("monitoring.html"))


# ── Background scheduler ───────────────────────────────────────────────────────
from contextlib import asynccontextmanager
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from services.monitoring_service import run_all_checks
from services.payment_reminder_service import run_payment_reminders
from database.migrations import run_migrations

def _start_scheduler():
    scheduler = BackgroundScheduler(daemon=True)
    check_interval = int(os.getenv("MONITOR_INTERVAL_MINUTES", "5"))
    scheduler.add_job(
        run_all_checks,
        trigger=IntervalTrigger(minutes=check_interval),
        id="monitoring",
        replace_existing=True,
    )
    scheduler.add_job(
        run_payment_reminders,
        trigger=IntervalTrigger(hours=24),
        id="payment_reminders",
        replace_existing=True,
    )
    scheduler.start()
    print(f"✅ Scheduler started — monitoring every {check_interval}min | reminders daily")
    return scheduler

@app.on_event("startup")
async def startup():
    run_migrations()
    _start_scheduler()

# ── Global exception handler ───────────────────────────────────────────────────
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


# ── Health check ───────────────────────────────────────────────────────────────
@app.get("/health", tags=["system"])
async def health():
    return {"status": "ok", "version": app.version}


@app.get("/", response_class=HTMLResponse, tags=["system"])
async def root():
    return RedirectResponse(url="/login")


# ── Dev entrypoint ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
