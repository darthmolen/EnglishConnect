"""EnglishConnect FastAPI application entry point."""

import logging
import os
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.database import init_db

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
    # Startup
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


@app.get("/")
async def root():
    """Health check endpoint."""
    return {
        "status": "ok",
        "app": settings.app_name,
        "env": settings.app_env,
    }


@app.get("/health")
async def health():
    """Detailed health check."""
    return {
        "status": "healthy",
        "database": "connected",  # TODO: Add actual DB check
        "services": {
            "stt": settings.stt_service_url,
            "tts_mcp": settings.tts_mcp_url,
            "content_mcp": settings.content_mcp_url,
        },
    }


# Import and include routers
from app.routers import lessons, conversation, progress, auth, content, audio, timing

app.include_router(lessons.router)
app.include_router(conversation.router)  # Unified conversation (/api/practice/conversation)
app.include_router(progress.router)
app.include_router(auth.router)
app.include_router(content.router)  # Authenticated content images (/api/content/images)
app.include_router(audio.router)  # Demo audio streaming (/api/audio)
app.include_router(timing.router)  # Timing log aggregation (/api/timing)
