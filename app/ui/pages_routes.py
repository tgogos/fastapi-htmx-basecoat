"""Admin pages: dashboard shell and sample pages."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from app.auth.deps import (
    get_or_create_csrf_token,
    get_session_user,
    require_user_html,
    verify_csrf,
)
from app.auth.users import role_at_least
from app.ui.paths import TEMPLATES_DIR
from app.ui.shell import (
    DEFAULT_SHELL_LAYOUT,
    SHELL_COOKIE,
    SHELL_LAYOUTS,
    current_shell_layout,
    safe_shell_next,
)

router = APIRouter()
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

# path, template, active, nav_group, extra_css, extra_js, main_class
SHELL_PAGES: list[tuple] = [
    (
        "/dashboard",
        "pages/dashboard.html",
        "dashboard",
        None,
        [],
        [
            "/static/vendor/chart.js/chart.umd.min.js",
            "/static/js/dashboard.js",
        ],
        "",
    ),
    ("/users", "pages/users.html", "users", None, [], [], ""),
    ("/forms", "pages/forms.html", "forms", None, [], [], ""),
    ("/tables", "pages/tables.html", "tables", None, [], [], ""),
    ("/components", "pages/components.html", "components", None, [], [], ""),
    ("/settings", "pages/settings.html", "settings", None, [], [], ""),
    ("/blank", "pages/blank.html", "blank", None, [], [], ""),
    ("/404", "pages/not_found.html", "", None, [], [], ""),
]

def shell_ctx(
    request: Request,
    user: dict | None,
    *,
    active: str,
    nav_group: str | None = None,
    extra_css: list[str] | None = None,
    extra_js: list[str] | None = None,
    main_class: str = "",
) -> dict:
    return {
        "request": request,
        "user": user,
        "csrf_token": get_or_create_csrf_token(request),
        "is_admin": bool(user) and role_at_least(user["role"], "admin"),
        "active": active,
        "nav_group": nav_group,
        "extra_css": extra_css or [],
        "extra_js": extra_js or [],
        "main_class": main_class,
        "shell_layout": current_shell_layout(request),
    }


def _page(
    path: str,
    template_name: str,
    active: str,
    nav_group: str | None,
    extra_css: list[str],
    extra_js: list[str],
    main_class: str,
):
    async def handler(
        request: Request,
        user: dict = Depends(require_user_html),
    ):
        return templates.TemplateResponse(
            request,
            template_name,
            shell_ctx(
                request,
                user,
                active=active,
                nav_group=nav_group,
                extra_css=extra_css,
                extra_js=extra_js,
                main_class=main_class,
            ),
        )

    handler.__name__ = "page_" + path.strip("/").replace("/", "_").replace("-", "_")
    return path, handler


@router.post("/shell", dependencies=[Depends(require_user_html), Depends(verify_csrf)])
async def set_shell_layout(
    layout: str = Form(...),
    next_url: str = Form("/ui/settings", alias="next"),
):
    choice = layout if layout in SHELL_LAYOUTS else DEFAULT_SHELL_LAYOUT
    response = RedirectResponse(url=safe_shell_next(next_url), status_code=303)
    response.set_cookie(
        SHELL_COOKIE,
        choice,
        max_age=60 * 60 * 24 * 365,
        httponly=True,
        samesite="lax",
        path="/",
    )
    return response


for _spec in SHELL_PAGES:
    _path, _handler = _page(*_spec)
    router.add_api_route(
        _path, _handler, methods=["GET"], response_class=HTMLResponse, include_in_schema=False
    )

async def render_not_found(request: Request) -> HTMLResponse:
    user = await get_session_user(request)
    return templates.TemplateResponse(
        request,
        "pages/not_found.html",
        shell_ctx(request, user, active=""),
        status_code=404,
    )
