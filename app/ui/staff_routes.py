"""HTML routes for staff accounts. Admin only. The sample /ui/users page is separate."""

from __future__ import annotations

from urllib.parse import urlencode

from fastapi import APIRouter, Depends, Form, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from app.auth.deps import (
    SESSION_VERSION_KEY,
    get_or_create_csrf_token,
    require_admin_html,
    verify_csrf,
)
from app.auth.passwords import hash_password
from app.auth.users import (
    ROLE_ORDER,
    ROLES,
    UsernameTaken,
    clean_display_name,
    clean_password,
    clean_username,
    count_admins,
    create_user,
    get_user_by_id,
    list_users,
    role_at_least,
    set_password,
    update_user,
)
from app.ui.pages_routes import render_not_found
from app.ui.paths import TEMPLATES_DIR
from app.ui.shell import current_shell_layout

router = APIRouter()
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

STAFF_PATH = "/ui/admin/users"


def _ctx(request: Request, user: dict, **extra):
    ctx = {
        "request": request,
        "user": user,
        "csrf_token": get_or_create_csrf_token(request),
        "can_edit": role_at_least(user["role"], "editor"),
        "is_admin": True,
        "active": "staff",
        "nav_group": None,
        "extra_css": [],
        "extra_js": [],
        "main_class": "",
        "shell_layout": current_shell_layout(request),
        "roles": ROLE_ORDER,
    }
    ctx.update(extra)
    ctx["toast"] = request.session.pop("toast", None)
    return ctx


def _remember_toast(request: Request, message: str) -> None:
    request.session["toast"] = {"message": message, "level": "ok"}


def _staff_return(value: str | None) -> str:
    path = (value or "").strip()
    if path == STAFF_PATH or path.startswith(f"{STAFF_PATH}?"):
        return path
    return STAFF_PATH


def _list_href(q: str, role: str) -> str:
    pairs: list[tuple[str, str]] = []
    if q:
        pairs.append(("q", q))
    if role in ROLES:
        pairs.append(("role", role))
    if not pairs:
        return STAFF_PATH
    return f"{STAFF_PATH}?{urlencode(pairs)}"


def _public_row(row: dict) -> dict:
    return {
        "id": row["id"],
        "username": row["username"],
        "display_name": row["display_name"],
        "role": row["role"],
        "created_at": row["created_at"],
    }


@router.get("/admin/users", response_class=HTMLResponse)
async def staff_page(
    request: Request,
    user: dict = Depends(require_admin_html),
    q: str = Query(""),
    role: str = Query(""),
):
    chosen_role = role if role in ROLES else ""
    rows = await list_users(q=q, role=chosen_role or None)
    return templates.TemplateResponse(
        request,
        "admin_users.html",
        _ctx(
            request,
            user,
            users=[_public_row(row) for row in rows],
            q=q.strip(),
            role=chosen_role,
            list_href=_list_href(q.strip(), chosen_role),
        ),
    )


@router.get("/admin/users/new", response_class=HTMLResponse)
async def new_staff_page(
    request: Request,
    user: dict = Depends(require_admin_html),
    return_to: str = Query(""),
):
    back = _staff_return(return_to)
    return templates.TemplateResponse(
        request,
        "staff_new.html",
        _ctx(
            request,
            user,
            values=_blank_values(),
            form_error=None,
            return_to=back,
        ),
    )


@router.post(
    "/admin/users/new",
    response_class=HTMLResponse,
    dependencies=[Depends(verify_csrf)],
)
async def create_staff(
    request: Request,
    user: dict = Depends(require_admin_html),
    username: str = Form(""),
    display_name: str = Form(""),
    role: str = Form("viewer"),
    password: str = Form(""),
    password_confirm: str = Form(""),
    return_to: str = Form(""),
):
    back = _staff_return(return_to)
    values = {
        "username": username,
        "display_name": display_name,
        "role": role if role in ROLES else "viewer",
    }
    try:
        clean_name = clean_username(username)
        clean_label = clean_display_name(display_name)
        if role not in ROLES:
            raise ValueError("Invalid role.")
        clean_secret = clean_password(password, password_confirm)
        await create_user(
            clean_name,
            hash_password(clean_secret),
            role=role,
            display_name=clean_label,
        )
    except UsernameTaken:
        return _new_form(request, user, values, "That username is already in use.", back)
    except ValueError as exc:
        return _new_form(request, user, values, str(exc), back)

    _remember_toast(request, f"Added {clean_name}")
    return RedirectResponse(url=back, status_code=303)


@router.get("/admin/users/{user_id}/edit", response_class=HTMLResponse)
async def edit_staff_page(
    request: Request,
    user_id: int,
    user: dict = Depends(require_admin_html),
    return_to: str = Query(""),
):
    target = await get_user_by_id(user_id)
    if target is None:
        return await render_not_found(request)
    back = _staff_return(return_to)
    return templates.TemplateResponse(
        request,
        "staff_edit.html",
        _ctx(
            request,
            user,
            target=_public_row(target),
            values={
                "display_name": target["display_name"] or "",
                "role": target["role"],
            },
            form_error=None,
            return_to=back,
        ),
    )


@router.post(
    "/admin/users/{user_id}/edit",
    response_class=HTMLResponse,
    dependencies=[Depends(verify_csrf)],
)
async def edit_staff(
    request: Request,
    user_id: int,
    user: dict = Depends(require_admin_html),
    display_name: str = Form(""),
    role: str = Form(""),
    return_to: str = Form(""),
):
    target = await get_user_by_id(user_id)
    if target is None:
        return await render_not_found(request)
    back = _staff_return(return_to)
    values = {
        "display_name": display_name,
        "role": role if role in ROLES else target["role"],
    }
    try:
        clean_label = clean_display_name(display_name)
        if role not in ROLES:
            raise ValueError("Invalid role.")
    except ValueError as exc:
        return _edit_form(request, user, target, values, str(exc), back)

    if target["role"] == "admin" and role != "admin" and await count_admins() <= 1:
        return _edit_form(
            request,
            user,
            target,
            values,
            "Cannot demote the last admin.",
            back,
        )

    updated = await update_user(user_id, display_name=clean_label, role=role)
    if updated is None:
        return await render_not_found(request)
    _remember_toast(request, f"Updated {updated['username']}")
    return RedirectResponse(url=back, status_code=303)


@router.get("/admin/users/{user_id}/password", response_class=HTMLResponse)
async def staff_password_page(
    request: Request,
    user_id: int,
    user: dict = Depends(require_admin_html),
    return_to: str = Query(""),
):
    target = await get_user_by_id(user_id)
    if target is None:
        return await render_not_found(request)
    return templates.TemplateResponse(
        request,
        "staff_password.html",
        _ctx(
            request,
            user,
            target=_public_row(target),
            form_error=None,
            return_to=_staff_return(return_to),
        ),
    )


@router.post(
    "/admin/users/{user_id}/password",
    response_class=HTMLResponse,
    dependencies=[Depends(verify_csrf)],
)
async def staff_password(
    request: Request,
    user_id: int,
    user: dict = Depends(require_admin_html),
    password: str = Form(""),
    password_confirm: str = Form(""),
    return_to: str = Form(""),
):
    target = await get_user_by_id(user_id)
    if target is None:
        return await render_not_found(request)
    back = _staff_return(return_to)
    try:
        clean_secret = clean_password(password, password_confirm)
    except ValueError as exc:
        return templates.TemplateResponse(
            request,
            "staff_password.html",
            _ctx(
                request,
                user,
                target=_public_row(target),
                form_error=str(exc),
                return_to=back,
            ),
            status_code=400,
        )

    updated = await set_password(user_id, hash_password(clean_secret))
    if updated is None:
        return await render_not_found(request)
    if updated["id"] == user["id"]:
        request.session[SESSION_VERSION_KEY] = updated["session_version"]
    _remember_toast(request, f"Password updated for {updated['username']}")
    return RedirectResponse(url=back, status_code=303)


def _blank_values() -> dict:
    return {"username": "", "display_name": "", "role": "viewer"}


def _new_form(request, user, values, form_error, return_to):
    return templates.TemplateResponse(
        request,
        "staff_new.html",
        _ctx(
            request,
            user,
            values=values,
            form_error=form_error,
            return_to=return_to,
        ),
        status_code=400,
    )


def _edit_form(request, user, target, values, form_error, return_to):
    return templates.TemplateResponse(
        request,
        "staff_edit.html",
        _ctx(
            request,
            user,
            target=_public_row(target),
            values=values,
            form_error=form_error,
            return_to=return_to,
        ),
        status_code=400,
    )
