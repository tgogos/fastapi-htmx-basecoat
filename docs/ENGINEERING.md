# Engineering notes

Decisions for this boilerplate. Prefer simple, robust, boring.

This file is the source of truth for architecture and conventions. When a decision or the code changes, update this document in the same change so it stays accurate for future readers (and agents). Do not refer to chat threads, option letters, or temporary debate labels.

## Goals

- Mature shape (clear modules, auth, tests, Docker) without shortcuts that fight growth.
- One primary full-stack path; optional demos stay thin and removable.
- Async-first; raw SQL (no ORM); Pydantic at the HTTP edge only.
- **HTML-first / HTMX** for the browser UI; `/api` JSON for machines. Not an SPA. HTMX is pinned to **4.0.0** in `app/ui/static/js/htmx.min.js`. Teach and copy from [four.htmx.org](https://four.htmx.org/docs).

### HTMX 4

Books markup already puts `hx-get`, `hx-target`, and `hx-swap` on the element that makes the request, so those buttons do not rely on attribute inheritance. These parts are specific to 4.0.0:

- `app.js` listens for `htmx:config:request` and writes the CSRF token on `event.detail.ctx.request.headers`. The 2.x names `htmx:configRequest` and `event.detail.headers` do not fire.
- The same file listens for `htmx:after:history:push` (the 2.x name was `htmx:pushedIntoHistory`). The page-size control calls `htmx.ajax` with `push`, and the select carries `hx-indicator`. `pushUrl` and `indicator` are not `htmx.ajax` arguments in 4.0.0.
- Back and Forward refetch the URL and still send `HX-Request`. `_wants_books_partial` returns the full page when `HX-History-Restore-Request` is set, and the table fragment otherwise. `/ui/books` and `/ui/books/search` both use it.
- HTTP 4xx and 5xx responses swap into the target. A books form that returns `400` with table HTML shows that HTML.

## UI architecture (HTML-first)

Prefer boring, server-driven UI over client frameworks. Concrete HTMX usage is under **HTMX patterns in use**.

### Principles

| Principle | Meaning |
|-----------|---------|
| **Server owns the truth** | Pages and HTMX fragments are the UI. Do not grow a client-side app store or SPA router. |
| **HTML first** | First paint and list/filter/mutation flows are server-rendered HTML (Jinja + the Bootstrap admin shell). |
| **HTMX for interaction** | Search, filters, pagination, and forms use HTMX swaps. |
| **Small JS islands** | Vanilla JS only where the browser must own a bit of widget state (confirm modal, toasts, CSRF header, page-size select). Prefer one focused script (`app/ui/static/js/app.js`). |
| **Progressive enhancement** | Pagination links keep usable `href`s; forms still work without JS where practical. |
| **Shareable URLs** | List/search use `hx-push-url`. |

### What not to add by default

- **No Alpine, React, Vue, Svelte, or similar** — local reactivity is not a reason. Add a client library only when a concrete widget cannot be done with HTMX + a small vanilla island, and document why in this file in the same change.
- **No SPA routing or frontend build step** — no Vite/Webpack app shell; static CSS/JS under `app/ui/static/` is enough.
- **No client i18n framework** — if i18n lands, prefer server-side templates.

### Island boundary

Use an island when interaction is inherently client-side (dialog, toast DOM, attaching a request header). Prefer HTMX when the server can return the next HTML fragment. Do not move list/table/form flows into islands “for speed.”

### Admin shell

The shared shell (`templates/layout.html`) loads Basecoat 1.0.2. Files: `app/ui/static/vendor/basecoat/basecoat.min.css` (the standalone Vega bundle, `basecoat.cdn.min.css` from `basecoat-css@1.0.2`) and `app/ui/static/vendor/basecoat/js/all.min.js`. Jinja macros from the same package are in `app/ui/templates/basecoat/`. There is no Tailwind or npm build: the standalone bundle already contains the component CSS, but not every Tailwind utility. Page layout that the bundle does not provide lives in `app/ui/static/css/app.css`. Interactive Basecoat components call `window.basecoat.initAll()` after HTMX inserts HTML, and `window.basecoat.initAll({ force: true })` when HTMX restores a page from history.

Dashboard, books, staff, and the sample pages (users, forms, tables, components, settings, blank) use Basecoat classes. `/ui/components` is the component reference: one example each of the pieces in the Basecoat docs, plus a type specimen of plain headings. Vega resets `h1`–`h6` to the body size; a card title is the styled heading. A page title is `.page-head h1`. Chart.js stays vendored because the dashboard chart loads it. Do not load a second stylesheet beside the Basecoat bundle.

`templates/layout.html` is the shell. The sidebar (`partials/sidebar.html`) is the Basecoat sidebar: brand in its header, and the App and Samples groups in its section. Each link starts with an inline icon; Basecoat sizes that SVG. The default layout also paints a content header in the column beside the sidebar: the same toggle button, Basecoat's theme switcher, and an account menu. The breadcrumb (`{% block breadcrumb %}`) is the first thing in the page, in both layouts. The menu trigger is a Basecoat avatar button with the username's initials. Its items are Settings and Sign out. Sign out stays a POST with the CSRF token. The switcher calls `window.basecoat.theme.toggle()` and stores the mode in `localStorage.themeMode`. A palette button beside it stores `localStorage.colorTheme` (`default`, `blue`, `teal`, or `grey`) and sets `data-color` on the document. Default leaves the Vega tokens alone. The other three override the primary, ring, and sidebar-primary colors only, with a light set and a dark set. The other layout is the sidebar alone; the theme switcher and the same account menu then sit in the sidebar footer, and `partials/navbar.html` is only the toggle. Basecoat does not ship an icon-only rail, a floating sidebar, or an inset sidebar, so those are not options. The choice is the `shell_layout` cookie (`header` or `sidebar`), set by `POST /ui/shell` (session CSRF, signed-in user) from the Settings page. It is a display preference, not a credential. Operational pages extend the layout and replace `{% block content %}` and `{% block breadcrumb %}`.

The sidebar has two groups. **App** is the product: Dashboard, Books, Search books, and Staff (`/ui/admin/users`, admin only). **Samples** is the page set kept as UI copy sources (users, forms, tables, components, settings, blank). Sample pages are not the product. The Users sample stays separate from Staff. Move a link from Samples to App when that page starts reading or writing application data.

Tables use Basecoat’s `table` inside `table-container`. Basecoat has no pagination component. Book lists share one pager under the table: the row count and the rows-per-page select on the left, and on the right “Page X of Y”, first, previous, a short run of page numbers, next, and last. The current page is an outline button. The other pages and the step buttons are ghost buttons. A gap in the run is an ellipsis. `app/ui/static/css/app.css` is the shell layout helpers, the HTMX indicator, and the books table sort caret. `app/ui/static/js/app.js` is the HTMX island (confirm dialog, toasts, CSRF header, page-size select, theme toggle).

To add a page: copy `templates/pages/blank.html`, add a row to `SHELL_PAGES` in `app/ui/pages_routes.py`, add a sidebar link in `partials/sidebar.html` under App or Samples with an `active` key and an icon, and set the breadcrumb block. A page for one entity puts its main action, such as Add book, in `.page-head` beside the title. Do not introduce a client-side HTML include loader.

## Product shape

| Surface | Role |
|---------|------|
| SQLite + session/CSRF + HTMX UI + protected books JSON API | Primary path — fork and grow this |
| `/items` (in-memory) | Minimal teaching CRUD — no auth, no UI |
| `/db-items` (MongoDB) | Optional NoSQL demo — removable |

Do not add auth, HTMX, or shared abstractions to the memory/Mongo demos unless the point is to teach that idea. Keep demos thin on purpose. `/items` and `/db-items` teach storage. Delete them when a fork does not need them.

Books is the reference domain in this repo, not a requirement of every fork. Copy `app/routes/books.py`, `app/db/books.py`, and `app/ui/books_routes.py` for the next entity, then replace books. Keep the URL split (`/api`, `/auth`, `/ui`), session/CSRF, Bearer tokens, roles, and the list contract (`page`, `size`, allowlisted `ordering`, `innerHTML` swaps). Demo routes keep the thin **Item** naming so they are not a second product.

## Roles

Three hierarchical roles on `users.role`:

| Role | Capabilities |
|------|----------------|
| `viewer` | Read books (UI + API GET) |
| `editor` | Create / update / delete books |
| `admin` | Editor powers + `/ui/admin/users` (list users, change roles) |

Enforcement is always on the server (`require_user` / `require_editor` / `require_admin` and HTML variants). Templates hide buttons; never trust the UI alone.

The seeded demo user is an **admin** (`DEMO_USERNAME` / `DEMO_PASSWORD`).

Startup only ensures that admin when `users` is empty. Richer demo data (sample `viewer` / `editor` accounts and books) is opt-in via `python -m app.seed` / `make seed` — idempotent (skips existing usernames). The sample catalog is about 100 well-known titles so page size and column sorting are easy to exercise. Re-running the seed inserts missing titles and refreshes the shelf category on titles it already knows. Other books are left alone.

## Code style (primary path)

Write primary-path code like the SQL and web layers:

- Thin route handlers: validate → call a helper → map to the response model.
- SQL in small modules (`app/db/…`, `app/auth/users.py`) with parameterized queries.
- Schema in `app/db/schema.sql`.
- Pydantic models are request/response schemas only, not persistence objects.
- Prefer FastAPI dependencies for auth over ad-hoc checks in every handler.

Reference implementations: `app/routes/books.py`, `app/db/books.py`, `app/ui/books_routes.py`.

The in-memory and Mongo routes may stay more verbose (logic in the handler, broad try/except). That style is for demos only — do not copy it into the primary path.

## URL layout

Path indicates the client. Do not serve HTML under `/api`, and do not issue API tokens from the HTML `/auth` routes.

| Prefix | Client | Auth | Response |
|--------|--------|------|----------|
| `/api/...` | Machines (curl, Swagger, services) | Bearer (session also allowed where useful) | JSON |
| `/auth/...` | Browsers | Session cookie + CSRF | HTML (forms, redirects) |
| `/ui/...` | Browsers and HTMX | Session + CSRF on mutations | HTML pages and fragments |
| `/items`, `/db-items` | Teaching demos | None | JSON |
| `/`, `/health`, `/docs` | Ops / docs | — | unchanged |

**Browser auth routes:** `GET/POST /auth/login`, `POST /auth/logout` — establish or clear a session. Logout is POST-only with CSRF (no GET logout). No token issuance here.

**API auth routes:** `POST /api/auth/token` (issue), `DELETE /api/auth/token` (revoke current Bearer), `GET /api/auth/me` (introspect, includes `role`).

**HTMX:** pages and partials share the `/ui/...` prefix (same router). Do not add a separate `/htmx` prefix. Use `templates/` for full pages and `templates/partials/` for fragments.

Primary mounts:

| Surface | Path |
|---------|------|
| UI list / HTMX | `/ui/books` (full page or partial via `HX-Request`) |
| Book page | `/ui/books/{id}` |
| New book page | `/ui/books/new` (editor+). Add book in the list header opens this page. |
| Edit book page | `/ui/books/{id}/edit` — full page on a visit; the table row when `HX-Request` is set |
| Advanced search | `/ui/books/search` (filters outside swap target) |
| Books table | `/ui/books/table` (set filters, row menu, page selection) |
| Staff | `/ui/admin/users` (admin only) |
| JSON API | `/api/books` (reads: login; writes: editor+; filter query params) |
| Root | `/` → `/ui/dashboard` |

Demos remain at `/items` and `/db-items`.

### Books fields and N+1

Books include scalars (`category`, `isbn`, `page_count`, `available`) and `added_by_user_id` → `users`. List/get **LEFT JOIN** users so `added_by_username` is loaded in the same query — do not resolve the adder with a per-row `get_user_by_id` (classic N+1).

### HTMX patterns in use

See **UI architecture** for the HTML-first contract. Patterns below are what this app actually ships (Bootstrap shell + `app.js`). Do not add Idiomorph, `hx-boost` shells, or OOB toasts unless they land in code and this file in the same change.

- **`HX-Request` dual response** — one list route returns the full page or `partials/books_table.html`. A history restore (`HX-History-Restore-Request`) gets the full page even though it also sends `HX-Request`.
- **Book pages** — `/ui/books/new`, `/ui/books/{id}`, and `/ui/books/{id}/edit` are whole pages. The edit URL still returns the table row when the list sends `HX-Request`. A title link keeps the list query (`page`, `size`, `ordering`, search filters, and `return_to` for the books list or search). The book and edit pages read that query the same way the list does, and Back uses `_books_list_url`. A visit with no list query still returns to `/ui/books`. Delete from the edit page sends `redirect=1` and `HX-Redirect` to that list.
- **Search** — `q` on title/author/ISBN with debounce + `hx-push-url`. Keep the search/filter form **outside** the HTMX swap target so inputs are not replaced (focus stays while typing).
- **Advanced filters** — `/ui/books/search`: selects + debounced text update live; year inputs update on `change`/explicit Apply (avoid mid-typing requests). Active filter chips render inside the results partial. Delete keeps filter query params via `return_to`.
- **Pagination and sort** — URL is the source of truth: `page`, `size` (`10`, `25`, `50`, `100`; default 10), and `ordering` (allowlisted column, prefix `-` for descending; default `title`). Sort links, page numbers, and the page-size control swap the list panel with `innerHTML` and `hx-push-url`. Each control keeps an `href`. The number run is `1 2 3 4 … last` near the start, `1 … current−1 current current+1 … last` in the middle, and `1 … last−3 last−2 last−1 last` near the end. Five pages or fewer show every number. Filter forms keep a hidden `ordering` so a search does not drop the sort. Unknown `ordering` values fall back to the default. Same contract on `/api/books` and `/ui/books/table`. Swaps stay `innerHTML`; do not add Idiomorph for this.
- **Books table** — `/ui/books/table` is the tabular pattern to copy. It keeps `page`, `size`, and `ordering`. Category is a repeated query parameter (`category=fiction&category=mystery`): a book matches when its category is any of those values. Availability is the same kind of set (`available=1` and `available=0`); selecting both means no availability filter. Different filters apply together, and that filtering happens in SQL before `LIMIT`/`OFFSET`. Clear drops one filter. Reset drops the sets and keeps the search text. The search box stays outside `#books-table-panel`. Row actions sit in a menu. Checkboxes select rows on the current page only; Delete posts those ids. Column visibility is not part of this pattern. `/api/books` accepts the same repeated `category` parameter. The original `/ui/books` list is unchanged.
- **Indicator** — shared `#books-indicator` via `hx-indicator` (search, pagination, sort, create). CSS-only spinner; HTMX toggles `.htmx-request` / opacity. Keep the indicator outside the swap target.
- Progressive enhancement: pagination links keep usable `href`s.
- **Confirm modal** — Bootstrap modal + small JS (`app/ui/static/js/app.js`); delete buttons use `hx-trigger="confirmed-delete"` after the user confirms (no `window.confirm`).
- **Toasts** — Bootstrap toasts. A swap can send `HX-Trigger: {"showToast": {...}}` (table save and delete). A full-page save or a delete that leaves the edit page stores the same message for the next page.

## Authentication

Teaching overview (cookies, CSRF, Bearer): [`auth.md`](auth.md).

One user store; two client mechanisms:

1. **Browsers / HTMX** — signed session cookie. Mutating HTML/HTMX requests require CSRF (`require_user_html`, `verify_csrf`).
2. **Machine clients** — opaque Bearer token from `POST /api/auth/token` (username/password). Store tokens in SQLite so revocation is deleting a row. Do not default to JWT unless this document is updated to say so.
3. **Protected JSON routes** — `require_user` accepts a valid session **or** a valid Bearer token. If the client uses the **session cookie** on a mutating method (`POST`/`PUT`/`PATCH`/`DELETE`), CSRF is required (`X-CSRF-Token` header or form field). **Bearer requests skip CSRF.** Role gates: `require_editor`, `require_admin`.
4. **Same-origin JS calling `/api`** — either send the session cookie with `credentials: "include"` **and** `X-CSRF-Token` (from the page meta tag), or use a Bearer token. Prefer Bearer for non-HTML clients; session+CSRF is fine for page scripts.
5. **Swagger `/docs`** — use HTTP Bearer for `/api` routes. Cookie login is for the UI, not the main docs Authorize flow.

In-memory and Mongo demos remain unauthenticated unless that changes deliberately.

Implemented: session + CSRF for the UI and for session-authenticated `/api` writes; `POST/DELETE /api/auth/token` + opaque tokens in `api_tokens`; `require_user` accepts Bearer or session; Swagger shows HTTP Bearer via `HTTPBearer` on API deps.

## Logging

Stdlib `logging` to **stdout** (Docker/12-factor). No log files, Loguru, or structlog.

| Setting | Role |
|---------|------|
| `LOG_LEVEL` | `DEBUG` / `INFO` / `WARNING` / `ERROR` / `CRITICAL`. Default `INFO`. How chatty the app is. |
| `ENVIRONMENT` | `production` → one JSON object per line (for a log shipper). Anything else → human-readable text. |
| `DEBUG` | When true, dump masked settings at startup (`log_config_values`). Independent of `LOG_LEVEL`. |

Configure once in `app/core/logging.py` (`setup_logging` from the lifespan). Use `logging.getLogger(__name__)` in modules. `LOG_LEVEL` applies to the `app` logger (and uvicorn). The root logger stays at INFO so third-party DEBUG does not flood stdout. `pymongo` / `motor` / `httpx` / `httpcore` / `urllib3` are pinned to WARNING (PyMongo otherwise logs a topology heartbeat every ~10s at DEBUG). Uvicorn access logs stay at INFO even if `LOG_LEVEL` is higher.

Do not log passwords, session cookies, Bearer tokens, or CSRF secrets. Examples: failed HTML login and failed `POST /api/auth/token` log `username=` only.

## Schema / local SQLite

`CREATE TABLE IF NOT EXISTS` does not migrate existing databases. Startup runs a small additive migrate for new `books` columns when missing; for larger shape changes, delete local `data/*.db` (and test DBs) and restart. Prefer recreate / tiny ALTER helpers over Alembic.

## Non-negotiables

- **Async-first** on the request path (async handlers, aiosqlite, Motor). Avoid new sync I/O in handlers. Sync `bcrypt` is an accepted exception; do not add more blocking work without noting it here.
- **No ORM** (no SQLAlchemy, SQLModel, Tortoise, etc.). SQL strings + parameters.
- **Removable modules** — Mongo, web UI, and demos must stay deletable via the README checklist pattern; do not entangle them into the primary path.
- **Document new patterns here** in the same change that introduces them.

## Patterns in use (primary path)

- Lifespan for connect / schema / seed / shutdown (not deprecated `@on_event`).
- Process-wide SQLite connection via `app/db/connection.py` (simple single-process setup; not a pool).
- Repository-style helpers return dicts (or simple structures); routes map to Pydantic.
- Separate dependencies for JSON vs HTML auth: `require_user` (Bearer or session) vs `require_user_html` + `LoginRequired` (session only); plus `require_editor` / `require_admin` (and HTML variants).
- Opaque API tokens hashed (SHA-256) in `api_tokens`; plaintext returned once from `POST /api/auth/token`.
- Settings via Pydantic Settings (`app/core/config.py`).
- Stdlib logging to stdout (`app/core/logging.py`); `LOG_LEVEL` env; JSON when `ENVIRONMENT=production`.
- Shared identity helpers in `app/auth/` (passwords, users, tokens, deps). HTTP routes live in `app/routes/` (JSON) and `app/ui/` (HTML).
- **uv** for Python deps: `pyproject.toml` + committed `uv.lock`; Docker installs with `uv sync --frozen`. Do not reintroduce `requirements.txt` as a second source of truth. Target CPython **3.14** (`.python-version`, `requires-python`).

## Out of scope

Unless this document is updated first:

- ORMs and sync DB drivers for the primary path
- SPA frameworks, SPA routers, or a frontend build step (vanilla JS + HTMX + the Bootstrap admin shell)
- Alpine.js / React / Vue / Svelte (or similar) unless a concrete widget forces an island and this doc is updated
- HTMX out-of-band (`hx-swap-oob`) swaps, client-side i18n libraries
- OAuth2 / OIDC providers
- JWT as the default API token
- Django-style generic admin
- Loguru / structlog, log files inside the container, or a bundled log shipper
