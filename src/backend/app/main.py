"""EnglishConnect FastAPI application entry point."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.database import init_db

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
from app.routers import lessons

app.include_router(lessons.router)

# Future routers (commented out until implemented):
# from app.routers import auth, progress, sessions
# app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
# app.include_router(progress.router, prefix="/api/progress", tags=["progress"])
# app.include_router(sessions.router, prefix="/api/sessions", tags=["sessions"])
