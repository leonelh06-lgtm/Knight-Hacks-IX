"""FastAPI application factory and root API router."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import health, voice
from app.core.config import get_settings


def create_app() -> FastAPI:
    settings = get_settings()
    application = FastAPI(
        title="KnightHacks Backend",
        description="Backend API for the KnightHacks IX project.",
        version="0.1.0",
    )
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=False,
        allow_methods=["GET"],
        allow_headers=["*"],
    )

    application.include_router(health.router, prefix="/api", tags=["health"])
    application.include_router(voice.router, prefix="/api", tags=["voice"])
    return application


app = create_app()
