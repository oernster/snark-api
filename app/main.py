from pathlib import Path

from fastapi import FastAPI, status
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.requests import Request

from app.core.config import settings
from app.services.sarcasm_service import SarcasmService
from app.version import __version__

app = FastAPI(
    title=settings.app_name,
    version=__version__,
)

templates = Jinja2Templates(directory="app/templates")

PAGE_TITLE = "SnarkAPI: professional-grade condescension, on demand"
STATIC_DIR = Path(__file__).resolve().parent.parent / "static"
QUOTES_PATH = Path(__file__).resolve().parent / "data" / "quotes.json"

# Serve files from ./static at /static
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/quotes.json", include_in_schema=False)
def quotes_json() -> FileResponse:
    """The whole quote list, from which the homepage picks in the browser.

    The site is published as static files, which cannot choose a line per
    request, so the choice moved to the page and this file replaced the old
    plain-text endpoint.
    """

    return FileResponse(path=str(QUOTES_PATH), media_type="application/json")


@app.get("/favicon.ico", include_in_schema=False)
def favicon() -> FileResponse:
    """Browser-default favicon endpoint.

    We store the favicon as a PNG at ./static/favicon.png.
    """

    favicon_path = STATIC_DIR / "favicon.png"
    return FileResponse(
        path=str(favicon_path),
        media_type="image/png",
        headers={"Cache-Control": "public, max-age=86400"},
    )


@app.get("/robots.txt", include_in_schema=False)
def robots_txt() -> FileResponse:
    """Crawler policy; must be served at the host root to be read."""

    return FileResponse(
        path=str(STATIC_DIR / "robots.txt"),
        media_type="text/plain",
        headers={"Cache-Control": "public, max-age=86400"},
    )


@app.get("/sitemap.xml", include_in_schema=False)
def sitemap_xml() -> FileResponse:
    """Sitemap for the snarkapi.com host, referenced from robots.txt."""

    return FileResponse(
        path=str(STATIC_DIR / "sitemap.xml"),
        media_type="application/xml",
        headers={"Cache-Control": "public, max-age=86400"},
    )


@app.get("/", include_in_schema=False)
def root(request: Request):
    """Homepage: render the styled sarcasm page with one quote already in it."""

    quote = SarcasmService(str(QUOTES_PATH)).get_quote()
    return templates.TemplateResponse(
        request=request,
        name="sarcasm.html",
        context={"title": PAGE_TITLE, "quote": quote},
    )


@app.get("/sarcasm", include_in_schema=False)
def sarcasm_page() -> RedirectResponse:
    """Legacy alias for the homepage.

    This once rendered its own copy of the homepage, which published a second
    crawlable URL for identical content. It now redirects so the site has one
    indexable page.
    """

    return RedirectResponse(url="/", status_code=status.HTTP_301_MOVED_PERMANENTLY)
