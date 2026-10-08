"""The static build for GitHub Pages: its path rules, its link check, its output.

The link check is proved by planting a broken link rather than trusted. The
end-to-end test runs the real build in a child process, because the build
changes directory, which must not leak into the rest of the suite.
"""

import subprocess
import sys
from pathlib import Path

import pytest

import build_site
from app.core.config import settings
from app.main import app

SITE_HOST = "www.snarkapi.com"


def _touch(path: Path, content: str = "") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def test_a_page_is_served_from_its_html_file_before_a_directory(tmp_path):
    _touch(tmp_path / "about.html")
    _touch(tmp_path / "about" / "index.html")

    assert build_site.resolve(tmp_path, "/about") == tmp_path / "about.html"


def test_exact_files_and_directory_indexes_resolve(tmp_path):
    _touch(tmp_path / "index.html")
    _touch(tmp_path / "quotes.json")
    _touch(tmp_path / "about" / "index.html")

    assert build_site.resolve(tmp_path, "/") == tmp_path / "index.html"
    assert build_site.resolve(tmp_path, "/quotes.json") == tmp_path / "quotes.json"
    assert build_site.resolve(tmp_path, "/about/") == (
        tmp_path / "about" / "index.html"
    )
    assert build_site.resolve(tmp_path, "/missing") is None
    assert build_site.resolve(tmp_path / "empty", "/") is None


def test_html_is_written_beside_its_url_and_everything_else_at_it(tmp_path):
    assert build_site.output_path(tmp_path, "/", True) == tmp_path / "index.html"
    assert build_site.output_path(tmp_path, "/sarcasm", True) == (
        tmp_path / "sarcasm.html"
    )
    assert build_site.output_path(tmp_path, "/quotes.json", False) == (
        tmp_path / "quotes.json"
    )


def test_the_link_check_names_a_planted_broken_link(tmp_path):
    _touch(tmp_path / "index.html", '<a href="/about/">a</a> <a href="/gone">b</a>')
    _touch(tmp_path / "about" / "index.html", '<a href="why.html">w</a>')
    _touch(tmp_path / "about" / "why.html", '<a href="https://example.com/">x</a>')

    broken = build_site.broken_links(tmp_path, settings.site_url)

    assert broken == ["/index.html -> /gone"]


def test_the_output_may_not_hold_the_repository(tmp_path):
    # Called directly, never through build(): were the guard ever to regress,
    # build() itself would clear the repository.
    for unsafe in (build_site.REPO_ROOT, build_site.REPO_ROOT.parent):
        with pytest.raises(SystemExit, match="Refusing"):
            build_site.refuse_unsafe_out(unsafe)

    build_site.refuse_unsafe_out(tmp_path / "site")


def test_the_route_walk_finds_every_page_route():
    paths = build_site.route_paths(app.routes)

    for route in ("/", "/quotes.json", "/robots.txt", "/sitemap.xml", "/sarcasm"):
        assert route in paths, route


def test_the_real_build_writes_a_servable_site(tmp_path):
    out = tmp_path / "site"
    result = subprocess.run(
        [sys.executable, str(build_site.REPO_ROOT / "build_site.py"), "--out", out],
        capture_output=True,
        text=True,
    )

    assert result.returncode == build_site.EXIT_OK, result.stderr
    for name in ("index.html", "quotes.json", "robots.txt", "sitemap.xml", "404.html"):
        assert (out / name).is_file(), name
    assert (out / "about" / "index.html").is_file()
    assert (out / "about" / "why.html").is_file()
    assert (out / "CNAME").read_text(encoding="utf-8").strip() == SITE_HOST

    moved = (out / "sarcasm.html").read_text(encoding="utf-8")
    assert f"url=https://{SITE_HOST}/" in moved
    assert "fetch('/quotes.json'" in (out / "index.html").read_text(encoding="utf-8")
