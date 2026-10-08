"""Render SnarkAPI to static files that GitHub Pages can serve.

The FastAPI application stays the only place a page is defined: this script asks
it for every route in-process through Starlette's test client, then writes each
answer to disk. What a static host cannot do is answered here instead:

- A page is written as `<path>.html`, which Pages serves at `<path>` itself.
- A 301 becomes a small page that sends the browser on.
- Anything that is not HTML (the quote list, robots.txt, the sitemap, the
  favicon) is written at its exact path.
- The product pages in `docs/` are published under `/about/`.
- Every internal link in every written page must land on a written file;
  otherwise the build fails naming the page and the link.

    python build_site.py            # build into site/
    python build_site.py --serve    # build, then serve site/ on localhost
"""

from __future__ import annotations

import argparse
import functools
import html
import http.server
import os
import pathlib
import re
import shutil
import sys
from urllib.parse import urljoin, urlsplit

REPO_ROOT = pathlib.Path(__file__).resolve().parent
DEFAULT_OUT = REPO_ROOT / "site"
PRODUCT_PAGES = REPO_ROOT / "docs"
PRODUCT_PATH = "about"
DEFAULT_PORT = 8000
LOCAL_HOST = "127.0.0.1"

EXIT_OK = 0
EXIT_BROKEN_LINKS = 1

HTML_SUFFIX = ".html"
INDEX_FILE = "index.html"
NOT_FOUND_FILE = "404.html"
CNAME_FILE = "CNAME"

_LINK_ATTRIBUTE = re.compile(r"""\b(?:href|src)\s*=\s*["']([^"']+)["']""")

REDIRECT_PAGE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Moved</title>
<meta name="robots" content="noindex">
<link rel="canonical" href="{target}">
<meta http-equiv="refresh" content="0; url={target}">
</head>
<body><p>This page has moved to <a href="{target}">{target}</a>.</p></body>
</html>
"""

NOT_FOUND_PAGE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Page not found</title>
<meta name="robots" content="noindex">
</head>
<body><p>There is no page here. <a href="/">Go and get insulted</a>.</p></body>
</html>
"""


def resolve(out: pathlib.Path, url_path: str) -> pathlib.Path | None:
    """The written file a URL path is served from; None when there is none.

    The order is the file itself, then `<path>.html`, then `<path>/index.html`.
    """
    relative = url_path.strip("/")
    if not relative:
        return out / INDEX_FILE if (out / INDEX_FILE).is_file() else None
    candidates = (
        out / relative,
        out / f"{relative}{HTML_SUFFIX}",
        out / relative / INDEX_FILE,
    )
    return next((path for path in candidates if path.is_file()), None)


def output_path(out: pathlib.Path, url_path: str, is_html: bool) -> pathlib.Path:
    """Where a response for `url_path` is written."""
    relative = url_path.strip("/")
    if not relative:
        return out / INDEX_FILE
    if is_html and not relative.endswith(HTML_SUFFIX):
        return out / f"{relative}{HTML_SUFFIX}"
    return out / relative


def broken_links(out: pathlib.Path, site_url: str) -> list[str]:
    """Every `page -> link` in the written pages that lands on no written file.

    Each page is read from disk, so the product pages copied in from `docs/` are
    checked exactly as the rendered ones are.
    """
    host = urlsplit(site_url).netloc
    broken = []
    for page in sorted(out.rglob(f"*{HTML_SUFFIX}")):
        page_path = "/" + page.relative_to(out).as_posix()
        for link in _LINK_ATTRIBUTE.findall(page.read_text(encoding="utf-8")):
            parts = urlsplit(urljoin(urljoin(site_url, page_path), link))
            if parts.scheme in ("http", "https") and parts.netloc == host:
                if resolve(out, parts.path) is None:
                    broken.append(f"{page_path} -> {link}")
    return broken


def refuse_unsafe_out(out: pathlib.Path) -> None:
    """Stop when `out` holds the repository, since the build clears it first."""
    if out.resolve() in (REPO_ROOT, *REPO_ROOT.parents):
        raise SystemExit(f"Refusing to clear {out}: it holds the repository.")


def route_paths(routes, prefix: str = "") -> set[str]:
    """Every GET route without a path parameter, however FastAPI holds them.

    FastAPI up to 0.128 flattens each included router into `app.routes`; later
    releases keep it nested with its prefix in an `include_context`. Both are
    walked so an upgrade cannot silently empty the site.
    """
    from fastapi.routing import APIRoute

    found: set[str] = set()
    for route in routes:
        included = getattr(route, "include_context", None)
        if included is not None:
            nested = included.included_router.routes
            found |= route_paths(nested, prefix + included.prefix)
        elif isinstance(route, APIRoute) and "GET" in route.methods:
            if "{" not in route.path:
                found.add(prefix + route.path)
    return found


def _write(path: pathlib.Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)


def _render_routes(client, app, out: pathlib.Path, site_url: str) -> int:
    """Write every route's answer; answer how many were written."""
    paths = sorted(route_paths(app.routes))
    for path in paths:
        response = client.get(path, follow_redirects=False)
        if response.is_redirect:
            target = urljoin(site_url, response.headers["location"])
            page = REDIRECT_PAGE.format(target=html.escape(target, quote=True))
            _write(output_path(out, path, is_html=True), page.encode())
            continue
        response.raise_for_status()
        is_html = "text/html" in response.headers.get("content-type", "")
        _write(output_path(out, path, is_html=is_html), response.content)
    return len(paths)


def _copy_static_mounts(app, out: pathlib.Path) -> None:
    """Copy each directory the application mounts, exactly as it mounts it."""
    from starlette.routing import Mount
    from starlette.staticfiles import StaticFiles

    for route in app.routes:
        if isinstance(route, Mount) and isinstance(route.app, StaticFiles):
            target = out / route.path.strip("/")
            shutil.copytree(route.app.directory, target, dirs_exist_ok=True)


def build(out: pathlib.Path) -> int:
    """Build the site into `out`; answer the exit code."""
    refuse_unsafe_out(out)

    # The app resolves templates/ and static/ against the working directory,
    # so the build runs from the repository root wherever it starts.
    os.chdir(REPO_ROOT)

    from fastapi.testclient import TestClient

    from app.core.config import settings
    from app.main import app

    site_url = settings.site_url
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)

    with TestClient(app, base_url=site_url.rstrip("/")) as client:
        count = _render_routes(client, app, out, site_url)
    _copy_static_mounts(app, out)
    shutil.copytree(PRODUCT_PAGES, out / PRODUCT_PATH, dirs_exist_ok=True)
    _write(out / NOT_FOUND_FILE, NOT_FOUND_PAGE.encode())
    _write(out / CNAME_FILE, f"{urlsplit(site_url).hostname}\n".encode())

    broken = broken_links(out, site_url)
    if broken:
        print(f"{len(broken)} internal link(s) land on nothing:", file=sys.stderr)
        for line in broken:
            print(f"  {line}", file=sys.stderr)
        return EXIT_BROKEN_LINKS
    written = sum(1 for path in out.rglob("*") if path.is_file())
    print(f"Built {count} routes ({written} files) into {out}")
    return EXIT_OK


class _SiteHandler(http.server.SimpleHTTPRequestHandler):
    """Serves the built site with the same path rules as `resolve`."""

    def translate_path(self, path: str) -> str:
        out = pathlib.Path(self.directory)
        found = resolve(out, urlsplit(path).path)
        return str(found) if found else super().translate_path(path)


def serve(out: pathlib.Path, port: int) -> None:
    handler = functools.partial(_SiteHandler, directory=str(out))
    with http.server.ThreadingHTTPServer((LOCAL_HOST, port), handler) as server:
        print(f"Serving {out} at http://{LOCAL_HOST}:{port}/ (Ctrl+C stops it)")
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--out",
        type=pathlib.Path,
        default=DEFAULT_OUT,
        help=f"output directory (default: {DEFAULT_OUT})",
    )
    parser.add_argument(
        "--serve", action="store_true", help="serve the build on localhost"
    )
    parser.add_argument(
        "--port", type=int, default=DEFAULT_PORT, help="port for --serve"
    )
    args = parser.parse_args(argv)
    out = args.out.resolve()
    code = build(out)
    if code == EXIT_OK and args.serve:
        serve(out, args.port)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
