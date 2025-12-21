"""EnglishConnect FastAPI application entry point."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.database import init_db

# Configure logging to show our app logs
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
# Set our app loggers to INFO
logging.getLogger("app").setLevel(logging.INFO)

settings = get_settings()


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
from app.routers import lessons, conversation, tts, progress

app.include_router(lessons.router)
app.include_router(conversation.router)
app.include_router(tts.router)
app.include_router(progress.router)

# Future routers (Phase 4B):
# from app.routers import auth
# app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
