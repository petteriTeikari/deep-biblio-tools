"""FastAPI application factory."""

from pathlib import Path
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from ..api import (
    conversion_router,
    processing_router,
    review_router,
    validation_router,
)
from ..web import web_router


def create_app(config: dict[str, Any] = None) -> FastAPI:
    """Create and configure FastAPI application."""
    config = config or {}

    # Create app
    app = FastAPI(
        title="Biblio Assistant",
        description="Web interface for Deep Biblio Tools",
        version="1.0.0",
    )

    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Mount static files
    static_dir = Path(__file__).parent.parent / "static"
    if static_dir.exists():
        app.mount(
            "/static", StaticFiles(directory=str(static_dir)), name="static"
        )

    # Include routers
    app.include_router(web_router, tags=["web"])
    app.include_router(validation_router, prefix="/api", tags=["validation"])
    app.include_router(processing_router, prefix="/api", tags=["processing"])
    app.include_router(conversion_router, prefix="/api", tags=["conversion"])
    app.include_router(review_router, prefix="/api", tags=["review"])

    # Store config in app state
    app.state.config = config

    # Add startup event
    @app.on_event("startup")
    async def startup_event():
        """Initialize application on startup."""
        print("Biblio Assistant started successfully")

    # Add health check
    @app.get("/health")
    async def health_check():
        """Health check endpoint."""
        return {"status": "healthy", "version": "1.0.0"}

    return app
