# Agent notes

Before changing this repo, read [`docs/ENGINEERING.md`](docs/ENGINEERING.md) and follow it.

## Must follow

- Prefer the primary path: SQLite, session/CSRF + HTMX UI, protected books JSON API (`/api/books`, `/ui/books`). Keep in-memory and Mongo demos thin and removable.
- **HTML-first / HTMX** — see [`docs/ENGINEERING.md`](docs/ENGINEERING.md) § UI architecture. The shared shell (`templates/layout.html`) uses Basecoat 1.0.2. Vendored files are in `app/ui/static/vendor/basecoat/`. Server owns pages and fragments. Vanilla JS islands only when needed (confirm dialog, toasts, CSRF, theme toggle). Do **not** add Alpine, React, Vue, Svelte, SPA routing, or a Tailwind/npm build step. Sample pages that still use Bootstrap class names share this layout and look wrong until they are restyled. Do not load Bootstrap beside the Basecoat bundle.
- HTMX is pinned to **4.0.0** (`app/ui/static/js/htmx.min.js`). Use [four.htmx.org](https://four.htmx.org/docs). Do not reintroduce HTMX 2 event names (`htmx:configRequest`, `htmx:pushedIntoHistory`) or the `htmx.ajax` options `pushUrl` and `indicator`.
- Async-first on the request path. No ORM — parameterized SQL only. Pydantic for request/response schemas, not persistence.
- Match primary-path style: thin routes, SQL/helpers in `app/db/` (and `app/auth/` for users), HTML/HTMX under `app/ui/`.
- URL intent: `/api` = JSON (machines), `/auth` = HTML session, `/ui` = pages + HTMX fragments. Do not invent a separate `/htmx` prefix.
- Auth direction: browser session + CSRF; API Bearer opaque tokens in SQLite; protected JSON accepts session or Bearer. Session-authenticated mutating `/api` calls require CSRF. Roles: viewer / editor / admin (`require_editor`, `require_admin`). Do not default to JWT or OAuth unless `ENGINEERING.md` says so.
- Books is the reference domain in this repo. For a new product, copy `app/routes/books.py`, `app/db/books.py`, and `app/ui/books_routes.py`, then replace books. Keep the URL split, session/CSRF, Bearer tokens, roles, and the list contract (`page`, `size`, allowlisted `ordering`, `innerHTML` swaps).
- Samples in the sidebar are UI copy sources. Move a link to App only when that page reads or writes application data. Demo routes stay named **items** (`/items`, `/db-items`) and stay removable.
- Do not introduce new architectural patterns without updating `docs/ENGINEERING.md` in the same change.
- Python deps: **uv** only (`pyproject.toml` + `uv.lock`). Do not add `requirements.txt`.
- Logging: stdlib to stdout; `LOG_LEVEL` env; JSON when `ENVIRONMENT=production`. Do not log secrets. See `docs/ENGINEERING.md` § Logging.

## Scope

Only change what the task requires. Do not “improve” demo routes (`/items`, `/db-items`) toward the primary stack unless asked.
