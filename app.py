"""
Agentic S3 Website Builder — FastAPI application entry point.

Run:
    uvicorn app:app --reload --port 8000

Or:
    python app.py
"""
import os
import argparse
import logging
import logging.config
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from config.settings import settings

load_dotenv()

# ── Logging setup ──────────────────────────────────────────────────────────────
os.makedirs("logs", exist_ok=True)

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

from api.routes.auth import router as auth_router
from api.routes.website_builder import router as website_router
from api.routes.shopping_cart import router as shop_router
from api.routes.media import router as media_router
from api.routes.payment import router as payment_router
from api.routes.admin import router as admin_router
from api.routes.console import router as console_router
from api.routes.chatbot import router as chatbot_router
from api.routes.feedback import router as feedback_router
from api.routes.monitoring import router as monitoring_router
from api.routes.team import router as team_router
from api.routes.commerce import router as commerce_router
from api.routes.clients import router as clients_router

# ── Rate limiter (shared across all routes) ───────────────────────────────────
limiter = Limiter(key_func=get_remote_address, default_limits=[])

app = FastAPI(
    title="Agentic AI Website Builder",
    description=(
        "A SaaS platform that uses multi-agent AI (CrewAI + OpenAI) to auto-build "
        "customisable websites with shopping carts, payment gateways, multi-theme support, "
        "web/social content research, and Snowflake-backed analytics."
    ),
    version="2.0.0",
)

# ── Attach rate-limiter state & error handler ─────────────────────────────────
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

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
app.include_router(media_router,   prefix="/api/v1")
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

# Serve all assets (uploads, images, css, js) from output folder for staging and published sites
from fastapi.staticfiles import StaticFiles as _StaticFiles
_app_root = Path(__file__).resolve().parent
_output_dir = (_app_root / "output").resolve()
_output_dir.mkdir(parents=True, exist_ok=True)
for _subdir in ("staging", "published"):
    (_output_dir / _subdir).mkdir(parents=True, exist_ok=True)
app.mount("/output", _StaticFiles(directory=str(_output_dir)), name="output")


## No need to mount /static/uploads anymore; all assets are under /output/staging/<site>/assets/

# Serve docs folder (reports, exported documents)
_docs_dir = (_app_root / "docs").resolve()
_docs_dir.mkdir(parents=True, exist_ok=True)
app.mount("/docs-files", _StaticFiles(directory=str(_docs_dir)), name="docs")

# Serve frontend JS/CSS assets (dashboard.js etc.)
_frontend_dir = (_app_root / "frontend").resolve()
app.mount("/static/frontend", _StaticFiles(directory=str(_frontend_dir)), name="frontend-assets")

# Serve logs folder for log viewing
_logs_dir = (_app_root / "logs").resolve()
_logs_dir.mkdir(parents=True, exist_ok=True)
app.mount("/logs", StaticFiles(directory=str(_logs_dir)), name="logs")

@app.get("/downloads", response_class=HTMLResponse, include_in_schema=False)
async def docs_index():
    """Browser-accessible listing of all files in the docs/ folder."""
    files = sorted(_docs_dir.iterdir()) if _docs_dir.exists() else []
    rows = "".join(
        f'<tr><td><a href="/docs-files/{f.name}" download>{f.name}</a></td>'
        f'<td style="color:#888;padding-left:24px">{f.stat().st_size // 1024} KB</td></tr>'
        for f in files if f.is_file()
    )
    html = f"""<!DOCTYPE html><html><head><meta charset="utf-8">
    <title>Docs — Website Builder</title>
    <style>
      body{{font-family:system-ui,sans-serif;max-width:700px;margin:60px auto;padding:0 20px;background:#f9fafb}}
      h1{{font-size:1.4rem;color:#4f46e5;margin-bottom:24px}}
      table{{width:100%;border-collapse:collapse}}
      tr{{border-bottom:1px solid #e5e7eb}}
      td{{padding:12px 8px;font-size:.95rem}}
      a{{color:#4f46e5;text-decoration:none;font-weight:600}}
      a:hover{{text-decoration:underline}}
      .empty{{color:#9ca3af;font-style:italic}}
    </style></head><body>
    <h1>📄 Project Documents</h1>
    {'<table>'+rows+'</table>' if rows else '<p class="empty">No files yet.</p>'}
    </body></html>"""
    return HTMLResponse(html)


@app.get("/output-browser", response_class=HTMLResponse, include_in_schema=False)
async def output_browser(request: Request):
    """Browser-accessible listing of files under the output/ directory."""
    if not _output_dir.exists():
        _output_dir.mkdir(parents=True, exist_ok=True)

    requested_rel = request.query_params.get("path", "").strip()
    current_dir = _output_dir
    if requested_rel:
        candidate = (_output_dir / requested_rel).resolve()
        try:
            candidate.relative_to(_output_dir.resolve())
            if candidate.is_dir():
                current_dir = candidate
        except ValueError:
            current_dir = _output_dir

    breadcrumb_parts = []
    current = current_dir
    while current != _output_dir.resolve() and current != current.parent:
        breadcrumb_parts.append(current.name)
        current = current.parent
    breadcrumb_parts.reverse()

    breadcrumb_links = []
    cursor = _output_dir.resolve()
    for part in breadcrumb_parts:
        cursor = cursor / part
        breadcrumb_links.append(
            f'<a href="/output-browser?path={cursor.relative_to(_output_dir.resolve()).as_posix()}">{part}</a>'
        )

    entries = []
    for entry in sorted(current_dir.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower())) if current_dir.exists() else []:
        rel_path = entry.relative_to(_output_dir.resolve()).as_posix()
        href = f"/output/{rel_path}" if entry.is_file() else f"/output-browser?path={rel_path}"
        kind = "📁" if entry.is_dir() else "📄"
        entries.append(f'<tr><td>{kind}</td><td><a href="{href}">{entry.name}</a></td></tr>')

    html = f"""<!DOCTYPE html><html><head><meta charset="utf-8">
    <title>Output Browser — Website Builder</title>
    <style>
      body{{font-family:system-ui,sans-serif;max-width:900px;margin:40px auto;padding:0 20px 40px;background:#f9fafb;color:#111827}}
      h1{{font-size:1.4rem;color:#4f46e5;margin-bottom:8px}}
      .meta{{color:#6b7280;margin-bottom:16px}}
      .crumbs{{margin-bottom:16px}}
      table{{width:100%;border-collapse:collapse;background:white;border:1px solid #e5e7eb;border-radius:8px;overflow:hidden}}
      th,td{{padding:12px 14px;border-bottom:1px solid #e5e7eb;text-align:left}}
      th{{background:#f3f4f6;font-size:.85rem;text-transform:uppercase;letter-spacing:.04em}}
      a{{color:#4f46e5;text-decoration:none;font-weight:600}}
      a:hover{{text-decoration:underline}}
    </style></head><body>
    <h1>📁 Output Browser</h1>
    <div class="meta">Browsing {current_dir.relative_to(_output_dir.resolve()).as_posix() if current_dir != _output_dir.resolve() else 'output/'}</div>
    <div class="crumbs"><a href="/output-browser">output/</a>{' / '.join(breadcrumb_links)}</div>
    <table>
      <thead><tr><th>Type</th><th>Name</th></tr></thead>
      <tbody>{''.join(entries)}</tbody>
    </table>
    </body></html>"""
    return HTMLResponse(html)


@app.get("/health", include_in_schema=False)
async def health_check():
    """Returns DB reachability, disk usage, and service configuration status."""
    import shutil
    import platform
    import sqlite3

    db_path = Path("data/website_builder.db")
    db_ok = False
    db_error = None
    try:
        con = sqlite3.connect(str(db_path), timeout=3)
        con.execute("SELECT 1")
        con.close()
        db_ok = True
    except Exception as exc:
        db_error = str(exc)

    disk = shutil.disk_usage("/")
    return {
        "status": "ok" if db_ok else "degraded",
        "db": "ok" if db_ok else f"error: {db_error}",
        "disk": {
            "total_gb": round(disk.total / 1e9, 1),
            "used_gb": round(disk.used / 1e9, 1),
            "free_gb": round(disk.free / 1e9, 1),
        },
        "s3_configured": bool(os.getenv("AWS_ACCESS_KEY_ID") and os.getenv("S3_BUCKET_NAME")),
        "openai_configured": bool(os.getenv("OPENAI_API_KEY")),
        "stripe_configured": bool(os.getenv("STRIPE_SECRET_KEY")),
        "python": platform.python_version(),
    }


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


def _is_truthy(value: str) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "on"}


def _validate_startup_configuration() -> None:
    jwt_secret = (os.getenv("JWT_SECRET") or "").strip()
    if not jwt_secret or jwt_secret.lower() in {"change-me-in-production", "changeme", "default", "secret"}:
        raise RuntimeError(
            "JWT_SECRET is missing or insecure. Set a strong JWT_SECRET before startup."
        )

    openai_api_key = (os.getenv("OPENAI_API_KEY") or "").strip()
    allow_missing_openai = (
        _is_truthy(os.getenv("ALLOW_MISSING_OPENAI_API_KEY", ""))
        or _is_truthy(os.getenv("TESTING", ""))
    )
    if not openai_api_key and not allow_missing_openai:
        raise RuntimeError(
            "OPENAI_API_KEY is required at startup. "
            "Set ALLOW_MISSING_OPENAI_API_KEY=true only for non-AI local/test runs."
        )

    storage_secrets_key = (os.getenv("STORAGE_SECRETS_KEY") or "").strip()
    if storage_secrets_key:
        try:
            from cryptography.fernet import Fernet
            Fernet(storage_secrets_key.encode("utf-8"))
        except Exception:
            raise RuntimeError(
                "STORAGE_SECRETS_KEY is set but is not a valid Fernet key. "
                "Generate a valid key with: "
                "python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\""
            )

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

@asynccontextmanager
async def _lifespan(_: FastAPI):
    _validate_startup_configuration()
    run_migrations()
    scheduler = _start_scheduler()
    try:
        yield
    finally:
        try:
            scheduler.shutdown(wait=False)
        except Exception:
            pass


app.router.lifespan_context = _lifespan

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

    parser = argparse.ArgumentParser(description="Run the Agentic Website Builder API")
    parser.add_argument("--host", default=os.getenv("APP_HOST", "0.0.0.0"))
    parser.add_argument("--port", type=int, default=int(os.getenv("APP_PORT", "8000")))
    parser.add_argument("--https", action="store_true", default=_is_truthy(os.getenv("APP_HTTPS", "")))
    parser.add_argument("--ssl-keyfile", default=os.getenv("SSL_KEYFILE", ""))
    parser.add_argument("--ssl-certfile", default=os.getenv("SSL_CERTFILE", ""))
    parser.add_argument("--reload", dest="reload", action="store_true")
    parser.add_argument("--no-reload", dest="reload", action="store_false")
    parser.set_defaults(reload=_is_truthy(os.getenv("UVICORN_RELOAD", "true")))

    args = parser.parse_args()

    ssl_keyfile = (args.ssl_keyfile or "").strip() or None
    ssl_certfile = (args.ssl_certfile or "").strip() or None
    https_enabled = bool(args.https or ssl_keyfile or ssl_certfile)

    if https_enabled and not (ssl_keyfile and ssl_certfile):
        default_key = Path("certs/dev.key")
        default_cert = Path("certs/dev.crt")
        if default_key.exists() and default_cert.exists():
            ssl_keyfile = str(default_key)
            ssl_certfile = str(default_cert)
        else:
            raise RuntimeError(
                "HTTPS enabled but SSL certificate files are missing. "
                "Provide --ssl-keyfile and --ssl-certfile (or SSL_KEYFILE/SSL_CERTFILE), "
                "or add local dev certs at certs/dev.key and certs/dev.crt."
            )

    uvicorn.run(
        "app:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        ssl_keyfile=ssl_keyfile if https_enabled else None,
        ssl_certfile=ssl_certfile if https_enabled else None,
    )
