"""EnglishConnect FastAPI application entry point."""

import logging
import os
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from sqlalchemy import text

from app.config import get_settings
from app.database import engine, init_db

# Load settings early for logging configuration
settings = get_settings()

# Configure logging - console always, file only in debug mode
log_format = "%(asctime)s %(levelname)s %(name)s: %(message)s"
date_format = "%H:%M:%S"

# Root logger configuration (console output)
logging.basicConfig(
    level=logging.INFO,
    format=log_format,
    datefmt=date_format,
)

# Add file handler only in debug/development mode
# In production (Kubernetes), logs are scraped from stdout
if settings.debug:
    logs_dir = Path(__file__).parent.parent.parent.parent / "logs"
    logs_dir.mkdir(exist_ok=True)
    log_filename = logs_dir / f"backend-{datetime.now().strftime('%Y%m%d-%H%M%S')}.log"

    file_handler = logging.FileHandler(log_filename)
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(logging.Formatter(log_format, date_format))
    logging.getLogger().addHandler(file_handler)
    logging.info(f"Debug mode: logging to file {log_filename}")

# Set our app loggers to INFO
logging.getLogger("app").setLevel(logging.INFO)
# Timing logger for latency analysis
logging.getLogger("timing").setLevel(logging.INFO)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup — Alembic handles schema migrations (see startup.sh).
    # init_db/create_all is only used for local dev without Alembic.
    if settings.app_env == "development":
        await init_db()
    yield
    # Shutdown
    pass


app = FastAPI(
    title=settings.app_name,
    description="Agentic English learning system for Spanish speakers",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS middleware for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.debug else [],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/status")
async def api_status():
    """API status endpoint (for development/debugging)."""
    return {
        "status": "ok",
        "app": settings.app_name,
        "env": settings.app_env,
    }


_GIT_SHA = os.environ.get("GIT_SHA", "dev")
_BUILD_TIME = os.environ.get("BUILD_TIME", "unknown")


@app.get("/health")
async def health():
    """Health check with real DB ping and version info.

    Used by ACA liveness/readiness probes and post-deploy verification.
    Returns 503 if database is unreachable so ACA marks revision unhealthy.
    """
    db_status = "connected"
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
    except Exception:
        db_status = "disconnected"

    status = "healthy" if db_status == "connected" else "unhealthy"
    response = {
        "status": status,
        "git_sha": _GIT_SHA,
        "build_time": _BUILD_TIME,
        "database": db_status,
    }

    if status == "unhealthy":
        from fastapi.responses import JSONResponse
        return JSONResponse(content=response, status_code=503)

    return response


@app.get("/api/config")
async def api_config():
    """Public configuration for frontend.

    Returns settings the frontend needs to know about.
    """
    return {
        "use_realtime_api": settings.use_realtime_api,
        "app_env": settings.app_env,
    }


# Import and include routers
from app.routers import lessons, conversation, progress, auth, content, audio, timing, realtime

app.include_router(lessons.router)
app.include_router(conversation.router)  # Unified conversation (/api/practice/conversation)
app.include_router(progress.router)
app.include_router(auth.router)
app.include_router(content.router)  # Authenticated content images (/api/content/images)
app.include_router(audio.router)  # Demo audio streaming (/api/audio)
app.include_router(timing.router)  # Timing log aggregation (/api/timing)
app.include_router(realtime.router)  # Realtime API WebSocket (/ws/conversation)

# Static file serving for React SPA (production container)
# The static/ directory is populated by Dockerfile.combined
static_path = Path(__file__).parent.parent / "static"
if static_path.exists():
    logging.info(f"SPA mode: serving static files from {static_path}")
    # Serve static assets (JS, CSS, images)
    app.mount("/assets", StaticFiles(directory=static_path / "assets"), name="assets")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        """Serve React SPA for all non-API routes."""
        # Check if it's a static file that exists
        file_path = static_path / full_path
        if file_path.exists() and file_path.is_file():
            return FileResponse(file_path)
        # Otherwise serve index.html for client-side routing
        return FileResponse(static_path / "index.html")
else:
    logging.info("API-only mode: no static files directory found")

    @app.get("/")
    async def root_dev():
        """Development fallback - no SPA available."""
        return {
            "status": "ok",
            "app": settings.app_name,
            "env": settings.app_env,
            "message": "SPA not built. Run 'npm run build' in frontend/",
        }
