# SnarkAPI

A small FastAPI web service that answers one HTTP request with one freshly
chosen sarcastic remark. It runs live at
[snarkapi.com](https://www.snarkapi.com/), which serves both a plain-text API
endpoint and a landing page that types its verdict at you over an animated
downpour.

The joke is the surface. The point underneath is that a gag service can still be
built with a proper service layer, pinned dependencies and a coverage gate that
does not bend.

> **Commercial licences available.** SnarkAPI is free and open source under the
> GNU General Public License v3.0. If those terms do not suit what you are
> building, such as a closed-source product, a commercial licence can be bought
> from me separately. It covers my own code; third-party libraries keep their own
> licences. See [commercial licensing](https://ernster.dev/commercial-licensing.html).

## Who it is for

- Anyone who wants a one-line insult from an HTTP call: a bot, a build script, a
  status page, a CI job that needs a closing remark.
- Developers looking at a small, complete FastAPI service they can read end to
  end in a few minutes.

## Who it is not for

- Anyone needing an SLA, authentication, rate limits or a support contract.
  There are none of those.
- Anyone wanting a downloadable application. This is a hosted web service; there
  is no installer, no desktop build and no package on PyPI.
- Anyone who wants the quotes to be inoffensive. They are aimed squarely at IT
  people and they do not soften.

## What it does

- **One endpoint.** `GET /api/v1/sarcasm/` returns a single line as
  `text/plain`, ready to pipe. No key, no quota, no JSON wrapper.
- **A rendered homepage.** `GET /` serves the styled page, which fetches a fresh
  line during each pause so the text keeps changing without a reload.
- **One indexable URL.** The legacy `/sarcasm` alias now answers `301` to `/`, so
  search engines see a single homepage rather than two copies of the same
  content.
- **Crawler files at the host root.** `/robots.txt` and `/sitemap.xml` are served
  by the application itself, because a crawler only honours them at the root.
- **A favicon route.** `/favicon.ico` returns the stored PNG, so the browser's
  automatic request does not log a 404 on every visit.
- **A quote supply that cannot take the service down.** The quotes are read
  from a JSON file on every request, so an edited file takes effect without a
  restart; if that file is missing, malformed or the wrong shape, the service
  falls back to a small built-in set and carries on.
- **Analytics on the homepage only.** The rendered page loads Plausible's
  analytics script; the plain-text endpoint returns the line and nothing else.

## Stack

| Concern | Choice |
| --- | --- |
| Language | Python 3.11 |
| Web framework | FastAPI on Starlette |
| Server | uvicorn |
| Templating | Jinja2 |
| Settings | pydantic-settings |
| Tests | pytest with pytest-cov |
| Formatting | black (88 columns) |
| Linting | flake8 (88 columns) |
| Hosting | Render |
| Landing page | Static HTML in `docs/`, published by GitHub Pages |
| Licence | GPL-3.0 |

## Layout

```
app/
  main.py                 routes: homepage, redirect, crawler files, favicon
  api/v1/sarcasm.py       the one API route
  services/               quote loading and selection
  models/                 pydantic shapes
  core/config.py          settings
  data/quotes.json        the quote supply
  templates/              the rendered homepage
  version.py              reads VERSION
static/                   favicon, robots.txt, sitemap.xml
docs/                     the GitHub Pages landing site
tests/                    the test suite
VERSION                   the single source of truth for the version
stamp_version.py          copies VERSION into the landing site
```

## Install and run

Python 3.11 or newer.

```
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

On macOS or Linux the activate line is `source .venv/bin/activate`.

That serves the homepage on `http://127.0.0.1:8000/` and the endpoint on
`http://127.0.0.1:8000/api/v1/sarcasm/`. Interactive API docs are at `/docs`.

`uvicorn` must be started from the repository root: the template directory, the
static mount and the default quotes path are all resolved relative to the working
directory.

Dependencies are pinned exactly in `requirements.txt` so a rebuild cannot
silently pull a breaking release. Re-freeze deliberately when upgrading.

## Tests

```
python -m pytest
```

A bare run enforces the gate. `addopts` in `pyproject.toml` turns on branch
coverage over the `app` package and fails the run under 100 per cent, so the
gate applies whether or not anyone remembers the flags. Coverage is scoped to
`app` because the tests are not the product.

`pytest-cov` and `coverage` are pinned in `requirements.txt` for that reason:
without `pytest-cov` installed, a bare `pytest` does not quietly skip the gate,
it fails outright on the unrecognised `--cov` arguments.

Lint and format checks:

```
black --check .
flake8
```

## Deployment

There is nothing to build. The service is deployed on Render as a Python web
service:

- Build installs `requirements.txt`.
- Start runs uvicorn against `app.main:app`, bound to `0.0.0.0` on the port
  Render supplies.
- The start command lives in the Render service settings; the repository carries
  no `render.yaml` or `Procfile`.

`snarkapi.com` points at that service. The landing site under `docs/` is
separate: GitHub Pages publishes it, then it links to the live service rather
than embedding it.

## Version

`VERSION` at the repository root is the single source of truth. `app/version.py`
reads it (falling back to a dev placeholder if the file is absent) and FastAPI
reports it in the OpenAPI document. The landing site cannot read a file at render
time, so it carries stamped tokens refreshed by `stamp_version.py`.

## Licence

GPL-3.0. See [LICENSE](LICENSE).

Commercial licences are also available; see [commercial licensing](https://ernster.dev/commercial-licensing.html).
