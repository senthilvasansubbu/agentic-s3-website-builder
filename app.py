"""
Agentic S3 Website Builder — FastAPI application entry point.

Run:
    uvicorn app:app --reload --port 8000

Or:
    python app.py
"""
import os
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from dotenv import load_dotenv

load_dotenv()

from api.routes.auth import router as auth_router
from api.routes.website_builder import router as website_router
from api.routes.shopping_cart import router as shop_router
from api.routes.payment import router as payment_router
from api.routes.admin import router as admin_router

app = FastAPI(
    title="Agentic AI Website Builder",
    description=(
        "A SaaS platform that uses multi-agent AI (CrewAI + OpenAI) to auto-build "
        "customisable websites with shopping carts, payment gateways, multi-theme support, "
        "web/social content research, and Snowflake-backed analytics."
    ),
    version="2.0.0",
)

# CORS — tighten origins in production
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ────────────────────────────────────────────────────────────────────
app.include_router(auth_router,    prefix="/api/v1")
app.include_router(website_router, prefix="/api/v1")
app.include_router(shop_router,    prefix="/api/v1")
app.include_router(payment_router, prefix="/api/v1")
app.include_router(admin_router,   prefix="/api/v1")


# ── Global exception handler ───────────────────────────────────────────────────
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


# ── Health check ───────────────────────────────────────────────────────────────
@app.get("/health", tags=["system"])
async def health():
    return {"status": "ok", "version": app.version}


@app.get("/", tags=["system"])
async def root():
    return {
        "message": "Welcome to Agentic AI Website Builder API",
        "docs": "/docs",
        "version": app.version,
    }


# ── Dev entrypoint ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
