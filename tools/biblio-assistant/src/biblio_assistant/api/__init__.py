"""API endpoints for biblio-assistant."""

from .conversion import router as conversion_router
from .processing import router as processing_router
from .review import router as review_router
from .validation import router as validation_router

__all__ = [
    "validation_router",
    "processing_router",
    "conversion_router",
    "review_router",
]
