# FastAPI HTMX Basecoat

Server-driven admin UI: the FastAPI + HTMX backend (SQLite books, session/CSRF, Bearer API). The browser shell is moving from Bootstrap to [Basecoat](https://basecoatui.com/introduction/) 1.0.2.

This is a copy of the Bootstrap admin app. The books API, session, and roles are unchanged. Basecoat's Vega stylesheet and JavaScript are vendored under `app/ui/static/vendor/basecoat/`. Page markup still uses Bootstrap classes, so the shell is not restyled yet.

Browsers get HTML (Jinja + HTMX 4.0.0). Machines get `/api` with Bearer tokens. One user store, Docker Compose, pytest.

Architecture: [`docs/ENGINEERING.md`](docs/ENGINEERING.md).  
Sessions, CSRF, and Bearer: [`docs/auth.md`](docs/auth.md).  
Vendored Bootstrap, Bootstrap Icons, and Chart.js notices: [`LICENSES.md`](LICENSES.md).

## Primary path vs demos

| | Role |
|--|------|
| **Primary** | SQLite **books** · roles (viewer / editor / admin) · session + CSRF for `/ui` and `/auth` · Bearer (or session) for `/api/books` · Basecoat (vendored) + HTMX; shell markup still Bootstrap |
| **Demos** (thin, removable) | `/items` in-memory CRUD · `/db-items` MongoDB CRUD |

## Quick start

**Requires:** Docker Compose. Make is optional. Dependencies are managed with [uv](https://docs.astral.sh/uv/) (`pyproject.toml` + `uv.lock`).

```bash
make dotenv   # .env.example → .env
make upd      # build + start (detached)

# http://localhost:8000              → /ui/dashboard (login first)
# http://localhost:8000/auth/login
# http://localhost:8000/ui/books     → books CRUD
# http://localhost:8000/docs         → OpenAPI (JSON API only)
```

Demo user (seeded when `users` is empty) is an **admin**: `DEMO_USERNAME` / `DEMO_PASSWORD` (defaults `admin` / `admin123`). Change these and **`SECRET_KEY`** before any shared deploy.

```bash
make seed     # optional viewer + editor users and sample books
make test
make down
```

### Local development with uv (optional)

```bash
uv sync --all-groups
uv run fastapi dev app/main.py --port 8000 --host 0.0.0.0
uv run pytest
```

## UI

The shell is `app/ui/templates/layout.html` (navbar, sidebar, footer). Sample pages keep their own routes:

| Page | Path |
|------|------|
| Dashboard | `/ui/dashboard` |
| Users, Forms, Tables | `/ui/users`, `/ui/forms`, `/ui/tables` |
| Components, Cheatsheet, Palette lab | `/ui/components`, `/ui/cheatsheet`, `/ui/palette-lab` |
| Settings, Blank, 404 | `/ui/settings`, `/ui/blank`, `/ui/404` |
| Header specimens | `/ui/headers/simple` (and centered, buttons, dark, account, product, double, icons) |
| Sidebar specimens | `/ui/sidebars/dark` (and light, icons, collapsible, list-group) |
| Sign in | `/auth/login` |

Working data pages use the same shell:

| Page | Path |
|------|------|
| Books | `/ui/books` |
| Book | `/ui/books/{id}` |
| New book | `/ui/books/new` |
| Edit book | `/ui/books/{id}/edit` |
| Search books | `/ui/books/search` |
| Staff (admin) | `/ui/admin/users` |

The sidebar is split into **App** (the product) and **Samples** (the original Bootstrap pages). To add a page, copy `app/ui/templates/pages/blank.html`, register it in `SHELL_PAGES` in `app/ui/pages_routes.py`, and add a sidebar link under the matching group in `app/ui/templates/partials/sidebar.html`.

## Auth in brief

- **Browser / HTMX:** cookie session + CSRF on mutating HTML (`/auth`, `/ui`).
- **API:** Bearer via `POST /api/auth/token`, or session cookie. Session writes to `/api` need `X-CSRF-Token`. Bearer skips CSRF.

```bash
curl -s -X POST http://localhost:8000/api/auth/token \
  -H 'Content-Type: application/json' \
  -d '{"username":"admin","password":"admin123"}'
```

## Layout

```
app/
  auth/     # passwords, users, tokens, deps
  db/       # SQLite connection + schema (primary)
  routes/   # JSON API (/api/..., demos)
  ui/       # HTML/HTMX templates + Bootstrap static
  models/   # Pydantic schemas
  core/     # settings + logging
docs/
pyproject.toml
uv.lock
```

## License

MIT — see [LICENSE](LICENSE). Third-party notices for vendored front-end files are in [LICENSES.md](LICENSES.md).
