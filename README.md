# FastAPI HTMX Basecoat

A FastAPI boilerplate you fork and grow, kept boring on purpose. The same app serves the people who use the pages and the programs that call its API. Pages are server-rendered HTML, with HTMX and a CSS library, so the UI has no build step. The database is SQLite and SQL written by hand, so there is no ORM. The aim is a lightweight start, with few dependencies, that you can still read as it grows.

## What it uses

- **FastAPI**, async on the request path. **Pydantic** validates HTTP input and output.
- **SQLite**, with parameterized SQL and no ORM.
- **Jinja** templates and **HTMX 4.0.0**. The shell is [Basecoat](https://basecoatui.com/introduction/) 1.0.2, shadcn/ui components shipped as CSS and JavaScript and vendored under `app/ui/static/vendor/basecoat/`. There is no Tailwind or npm build.
- A cookie session and CSRF for the pages. Opaque Bearer tokens for `/api`.
- **Docker Compose**, [uv](https://docs.astral.sh/uv/), and pytest. Python 3.14.

## What is already wired

Books is included as an example, with the pages to list, open, create, edit, and delete a book. Search, filters, sorting, and pagination swap part of the page and update the URL. That is the HTMX these screens are here to show. An admin can manage users. The signed-in person can change their display name, password, and the shell layout from Settings.

Each user has a role. A **viewer** can read. An **editor** can change books. An **admin** can also manage users.

Two extra HTTP examples sit outside the admin UI. `/items` is an in-memory list. `/db-items` shows the same idea with async MongoDB (Motor). While those demos ship here, Compose starts Mongo and the app connects on startup; the full test suite needs that Mongo too. A fork that does not want them deletes the demo code and dependencies — there is no switch to leave Mongo off.

Books is the place to copy when you add your own data: take its routes and replace the noun. The steps are in [`docs/ENGINEERING.md`](docs/ENGINEERING.md).

The dashboard and the Samples group in the sidebar are layout examples. They do not read or write application data.

## A good fit

This repo fits a server-rendered admin that grows by copying the books screens, with a JSON API in the same process.

Look elsewhere for an ORM and migrations, background jobs, OAuth, or a client-side frontend.

## Quick start

**Requires:** Docker Compose. Python 3.14 if you run the app on the host. Make is optional. Dependencies are managed with uv (`pyproject.toml` + `uv.lock`).

```bash
make dotenv   # .env.example → .env
make upd      # build + start (detached)

# http://localhost:8000              → /ui/dashboard (login first)
# http://localhost:8000/auth/login
# http://localhost:8000/ui/books     → books
# http://localhost:8000/docs         → OpenAPI (JSON API)
```

The first start creates an **admin** when the users table is empty: `DEMO_USERNAME` / `DEMO_PASSWORD` (defaults `admin` / `admin123`). Change these and **`SECRET_KEY`** before any shared deploy.

```bash
make seed     # optional viewer and editor (password demo123) and sample books
make test
make down
```

### Local development with uv (optional)

Compose remains the supported way to run the full stack and `make test`. On the host you still need a reachable Mongo for lifespan and for `pytest` (set `MONGO_HOST` and the other `MONGO_*` values, or leave Compose’s Mongo published and point at it).

```bash
uv sync --all-groups
uv run fastapi dev app/main.py --port 8000 --host 0.0.0.0
uv run pytest
```

## Auth

Pages keep a cookie session. A form or an HTMX request that changes data also sends a CSRF token.

The JSON API accepts an opaque Bearer token from `POST /api/auth/token`. It also accepts the session cookie. A session that writes to `/api` still sends `X-CSRF-Token`. A Bearer token does not.

```bash
curl -s -X POST http://localhost:8000/api/auth/token \
  -H 'Content-Type: application/json' \
  -d '{"username":"admin","password":"admin123"}'
```

Sessions, CSRF, and Bearer tokens: [`docs/auth.md`](docs/auth.md).

## Layout

```
app/
  auth/     # passwords, users, tokens, route checks
  db/       # SQLite connection, schema, and SQL
  routes/   # JSON API, plus the /items and /db-items examples
  ui/       # HTML, HTMX, and the vendored Basecoat shell
  models/   # Pydantic request and response schemas
  core/     # settings and logging
docs/
pyproject.toml
uv.lock
```

## Further reading

- Architecture and conventions: [`docs/ENGINEERING.md`](docs/ENGINEERING.md)
- Sessions, CSRF, and Bearer tokens: [`docs/auth.md`](docs/auth.md)
- Vendored Chart.js and Basecoat notices: [`LICENSES.md`](LICENSES.md)
- This repo started from the [FastAPI HTMX starter](https://github.com/tgogos/fastapi-htmx-starter)

## License

MIT — see [LICENSE](LICENSE). Third-party notices for vendored front-end files are in [LICENSES.md](LICENSES.md).
