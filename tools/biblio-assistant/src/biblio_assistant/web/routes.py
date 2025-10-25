"""Web interface routes."""

from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

router = APIRouter()

# Setup templates
templates_dir = Path(__file__).parent.parent / "templates"
templates = Jinja2Templates(directory=str(templates_dir))


@router.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Home page."""
    return templates.TemplateResponse(
        "index.html", {"request": request, "title": "Biblio Assistant"}
    )


@router.get("/validate", response_class=HTMLResponse)
async def validate_page(request: Request):
    """Citation validation page."""
    return templates.TemplateResponse(
        "validate.html", {"request": request, "title": "Citation Validator"}
    )


@router.get("/process", response_class=HTMLResponse)
async def process_page(request: Request):
    """Paper processing page."""
    return templates.TemplateResponse(
        "process.html", {"request": request, "title": "Paper Processor"}
    )


@router.get("/convert", response_class=HTMLResponse)
async def convert_page(request: Request):
    """Format conversion page."""
    return templates.TemplateResponse(
        "convert.html", {"request": request, "title": "Format Converter"}
    )


@router.get("/review", response_class=HTMLResponse)
async def review_page(request: Request):
    """Literature review page."""
    return templates.TemplateResponse(
        "review.html", {"request": request, "title": "Literature Reviewer"}
    )


@router.get("/settings", response_class=HTMLResponse)
async def settings_page(request: Request):
    """Settings page."""
    return templates.TemplateResponse(
        "settings.html", {"request": request, "title": "Settings"}
    )
