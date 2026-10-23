"""Admin pages: dashboard shell and sample pages."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from app.auth.deps import (
    SESSION_VERSION_KEY,
    get_or_create_csrf_token,
    get_session_user,
    require_user_html,
    verify_csrf,
)
from app.auth.passwords import hash_password, verify_password
from app.auth.users import (
    clean_display_name,
    clean_password,
    get_user_by_id,
    role_at_least,
    set_display_name,
    set_password,
)
from app.ui.paths import TEMPLATES_DIR
from app.ui.shell import (
    CONTENT_WIDTH_COOKIE,
    CONTENT_WIDTHS,
    DEFAULT_CONTENT_WIDTH,
    DEFAULT_SHELL_LAYOUT,
    SHELL_COOKIE,
    SHELL_LAYOUTS,
    current_content_width,
    current_shell_layout,
    safe_shell_next,
)

router = APIRouter()
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
PROFILE_PATH = "/ui/settings"
ACCOUNT_PATH = "/ui/settings/account"

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
        "content_width": current_content_width(request),
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


def _remember_toast(request: Request, message: str) -> None:
    request.session["toast"] = {"message": message, "level": "ok"}


def _profile_page(
    request: Request,
    user: dict,
    *,
    display_name: str,
    form_error: str | None,
    status_code: int = 200,
):
    ctx = shell_ctx(request, user, active="settings")
    ctx["toast"] = request.session.pop("toast", None)
    ctx["display_name_value"] = display_name
    ctx["form_error"] = form_error
    return templates.TemplateResponse(
        request,
        "pages/settings_profile.html",
        ctx,
        status_code=status_code,
    )


@router.get("/settings", response_class=HTMLResponse)
async def settings_profile(
    request: Request,
    user: dict = Depends(require_user_html),
):
    return _profile_page(
        request,
        user,
        display_name=user.get("display_name") or "",
        form_error=None,
    )


@router.get("/settings/profile", response_class=HTMLResponse)
async def settings_profile_redirect():
    return RedirectResponse(url=PROFILE_PATH, status_code=303)


@router.get("/settings/appearance", response_class=HTMLResponse)
async def settings_appearance(
    request: Request,
    user: dict = Depends(require_user_html),
):
    return templates.TemplateResponse(
        request,
        "pages/settings.html",
        shell_ctx(request, user, active="settings"),
    )


@router.post(
    "/settings",
    response_class=HTMLResponse,
    dependencies=[Depends(verify_csrf)],
)
@router.post(
    "/settings/profile",
    response_class=HTMLResponse,
    dependencies=[Depends(verify_csrf)],
)
async def save_settings_profile(
    request: Request,
    user: dict = Depends(require_user_html),
    display_name: str = Form(""),
):
    try:
        clean_label = clean_display_name(display_name)
    except ValueError as exc:
        return _profile_page(
            request,
            user,
            display_name=display_name,
            form_error=str(exc),
            status_code=400,
        )
    updated = await set_display_name(user["id"], clean_label)
    if updated is None:
        return await render_not_found(request)
    _remember_toast(request, "Display name saved")
    return RedirectResponse(url=PROFILE_PATH, status_code=303)


def _account_page(
    request: Request,
    user: dict,
    *,
    form_error: str | None,
    status_code: int = 200,
):
    ctx = shell_ctx(request, user, active="settings")
    ctx["toast"] = request.session.pop("toast", None)
    ctx["form_error"] = form_error
    return templates.TemplateResponse(
        request,
        "pages/settings_account.html",
        ctx,
        status_code=status_code,
    )


@router.get("/settings/account", response_class=HTMLResponse)
async def settings_account(
    request: Request,
    user: dict = Depends(require_user_html),
):
    return _account_page(request, user, form_error=None)


@router.post(
    "/settings/account",
    response_class=HTMLResponse,
    dependencies=[Depends(verify_csrf)],
)
async def save_settings_account(
    request: Request,
    user: dict = Depends(require_user_html),
    current_password: str = Form(""),
    password: str = Form(""),
    password_confirm: str = Form(""),
):
    record = await get_user_by_id(user["id"])
    if record is None:
        return await render_not_found(request)
    if not verify_password(current_password, record["password_hash"]):
        return _account_page(
            request,
            user,
            form_error="Current password is incorrect.",
            status_code=400,
        )
    try:
        clean_secret = clean_password(password, password_confirm)
    except ValueError as exc:
        return _account_page(
            request,
            user,
            form_error=str(exc),
            status_code=400,
        )
    updated = await set_password(user["id"], hash_password(clean_secret))
    if updated is None:
        return await render_not_found(request)
    request.session[SESSION_VERSION_KEY] = updated["session_version"]
    _remember_toast(request, "Password updated")
    return RedirectResponse(url=ACCOUNT_PATH, status_code=303)


@router.post("/view", dependencies=[Depends(require_user_html), Depends(verify_csrf)])
async def set_content_width(
    width: str = Form(...),
    next_url: str = Form("/ui/settings", alias="next"),
):
    choice = width if width in CONTENT_WIDTHS else DEFAULT_CONTENT_WIDTH
    response = RedirectResponse(url=safe_shell_next(next_url), status_code=303)
    response.set_cookie(
        CONTENT_WIDTH_COOKIE,
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

def _is_htmx_fragment(request: Request) -> bool:
    if request.headers.get("HX-History-Restore-Request") == "true":
        return False
    return request.headers.get("HX-Request") == "true"


async def render_not_found(request: Request) -> HTMLResponse:
    user = await get_session_user(request)
    return templates.TemplateResponse(
        request,
        "pages/not_found.html",
        shell_ctx(request, user, active=""),
        status_code=404,
    )


async def render_forbidden(request: Request) -> HTMLResponse:
    if _is_htmx_fragment(request):
        return HTMLResponse(
            '<div class="alert" role="alert"><section>You do not have permission to do that.</section></div>',
            status_code=403,
        )
    user = await get_session_user(request)
    return templates.TemplateResponse(
        request,
        "pages/forbidden.html",
        shell_ctx(request, user, active=""),
        status_code=403,
    )
