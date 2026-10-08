# SnarkAPI

A small site that types one sarcastic remark after another at you over an
animated downpour. It runs at [snarkapi.com](https://www.snarkapi.com/) as static
files on GitHub Pages. A FastAPI app renders every page at build time; the
homepage picks each line in the browser from a published quote list.

The joke is the surface. The point underneath is that a gag can still be built
with a proper service layer, pinned dependencies and a coverage gate that does
not bend.

The plain-text endpoint that once answered `GET /api/v1/sarcasm/` with a fresh
line is retired. A static host cannot choose a line per request, so the choice
moved into the page; `/quotes.json` hands over the whole list instead.

> **Commercial licences available.** SnarkAPI is free and open source under the
> GNU General Public License v3.0. If those terms do not suit what you are
> building, such as a closed-source product, a commercial licence can be bought
> from me separately. It covers my own code; third-party libraries keep their own
> licences. See [commercial licensing](https://ernster.dev/commercial-licensing.html).

## Who it is for

- Anyone who wants an insult from an HTTP call: a bot, a build script, a status
  page, a CI job that needs a closing remark. Fetch `/quotes.json` and pick one;
  `curl -s https://www.snarkapi.com/quotes.json | jq -r '.[]' | shuf -n 1` does it
  from a shell.
- Developers looking at a small, complete FastAPI app they can read end to end
  in a few minutes.

## Who it is not for

- Anyone needing an SLA, authentication, rate limits or a support contract.
  There are none of those.
- Anyone wanting a downloadable application. This is a hosted website; there is
  no installer, no desktop build and no package on PyPI.
- Anyone wanting a random line per request from the server. That endpoint is
  retired; see above.
- Anyone who wants the quotes to be inoffensive. They are aimed squarely at IT
  people and they do not soften.

## What it does

- **One quote file.** `GET /quotes.json` returns the whole supply as a JSON list
  of strings. No key, no quota.
- **A typing homepage.** `GET /` serves the styled page with one line already in
  it. The page loads the quote list once, then picks a different line during
  each pause so the text keeps changing without a reload.
- **One indexable URL.** The legacy `/sarcasm` address is a redirect page that
  sends the browser to `/`, so search engines see a single homepage.
- **Product pages under `/about/`.** The overview and the "why" page from `docs/`
  are published beside the app.
- **Crawler files at the host root.** `/robots.txt` and `/sitemap.xml` sit at the
  root, because a crawler only honours them there.
- **A favicon at the root.** `/favicon.ico` holds the stored PNG, so the
  browser's automatic request does not log a 404 on every visit.
- **A quote supply that cannot blank the page.** If the quote file fails to load
  in the browser, the page keeps typing the line it already has. At build time a
  missing or malformed file drops the first line to a small built-in set.
- **Analytics on the homepage only.** The rendered page loads Plausible's
  analytics script; the quote file is plain JSON.

## Stack

| Concern | Choice |
| --- | --- |
| Language | Python 3.13, locally and in CI |
| Web framework | FastAPI on Starlette |
| Server | uvicorn, in development only |
| Templating | Jinja2 |
| Settings | pydantic-settings |
| Tests | pytest with pytest-cov |
| Formatting | black (88 columns) |
| Linting | flake8 (88 columns) |
| Hosting | GitHub Pages, built by `build_site.py` and deployed by CI |
| Product pages | Static HTML in `docs/`, published under `/about/` |
| Licence | GPL-3.0 |

## Layout

```
app/
  main.py                 routes: homepage, quote file, redirect, crawler files,
                          favicon
  services/               quote loading and selection
  models/                 pydantic shapes
  core/config.py          settings
  data/quotes.json        the quote supply
  templates/              the rendered homepage
  version.py              reads VERSION
static/                   favicon, robots.txt, sitemap.xml
docs/                     the product pages, published under /about/
tests/                    the test suite
VERSION                   the single source of truth for the version
stamp_version.py          copies VERSION into the product pages
build_site.py             renders the app to static files for GitHub Pages
```

## Install and run

Python 3.13, matching CI.

```
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

On macOS or Linux the activate line is `source .venv/bin/activate`.

That serves the homepage on `http://127.0.0.1:8000/` and the quote list on
`http://127.0.0.1:8000/quotes.json`.

To see exactly what will be published, build the static site and serve it:

```
python build_site.py --serve
```

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

`snarkapi.com` is static files on GitHub Pages. A push to `main` runs
`.github/workflows/pages.yml`, which:

1. runs the test gate;
2. runs `python build_site.py`, which renders every route into `site/`, turns the
   `/sarcasm` redirect into a redirect page, copies `docs/` to `/about/` and fails
   on any internal link that lands on nothing;
3. publishes `site/` to Pages;
4. asks the live site for a fixed set of URLs, each of which must answer 200.

The repository's Pages source must be set to GitHub Actions. The build writes
`site/CNAME` from `site_url` in `app/core/config.py`.

## Version

`VERSION` at the repository root is the single source of truth. `app/version.py`
reads it (falling back to a dev placeholder if the file is absent) and FastAPI
reports it in the OpenAPI document. The landing site cannot read a file at render
time, so it carries stamped tokens refreshed by `stamp_version.py`.

## Licence

GPL-3.0. See [LICENSE](LICENSE).

Commercial licences are also available; see [commercial licensing](https://ernster.dev/commercial-licensing.html).
