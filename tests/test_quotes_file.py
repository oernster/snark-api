"""The quote list the homepage picks from in the browser.

The site is published as static files, so the plain-text endpoint that chose a
line per request is gone; the page now loads this list once and chooses itself.
"""

import json

from app.main import QUOTES_PATH


def test_quotes_json_serves_the_quote_list_as_json(client):
    response = client.get("/quotes.json")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/json")
    quotes = response.json()
    assert quotes == json.loads(QUOTES_PATH.read_text(encoding="utf-8"))
    assert quotes and all(isinstance(q, str) and q.strip() for q in quotes)


def test_the_retired_endpoint_is_gone(client):
    assert client.get("/api/v1/sarcasm/").status_code == 404


def test_the_homepage_picks_from_the_quote_file(client):
    page = client.get("/").text

    assert "fetch('/quotes.json'" in page
    assert "/api/v1/sarcasm" not in page
