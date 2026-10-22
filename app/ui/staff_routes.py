"""HTML routes for user accounts. Admin only. The sample /ui/users page is separate."""

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
    DEFAULT_STAFF_ORDERING,
    ROLE_ORDER,
    ROLES,
    STAFF_SORT_COLUMNS,
    UsernameTaken,
    chosen_staff_roles,
    clean_display_name,
    clean_password,
    clean_username,
    count_admins,
    count_staff_by_role,
    create_user,
    get_user_by_id,
    list_staff_page,
    normalize_staff_ordering,
    role_at_least,
    set_password,
    staff_role_filter,
    staff_total_pages,
    update_user,
)
from app.ui.pages_routes import render_not_found
from app.ui.pagination import (
    DEFAULT_PAGE_SIZE,
    PAGE_SIZES,
    page_size,
    page_window,
    sort_column_state,
)
from app.ui.paths import TEMPLATES_DIR
from app.ui.shell import current_content_width, current_shell_layout

router = APIRouter()
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
templates.env.globals["sort_column_state"] = sort_column_state

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
        "content_width": current_content_width(request),
        "roles": ROLE_ORDER,
    }
    ctx.update(extra)
    if not _wants_staff_partial(request):
        ctx["toast"] = request.session.pop("toast", None)
    return ctx


def _remember_toast(request: Request, message: str) -> None:
    request.session["toast"] = {"message": message, "level": "ok"}


def _staff_return(value: str | None) -> str:
    path = (value or "").strip()
    if path == STAFF_PATH or path.startswith(f"{STAFF_PATH}?"):
        return path
    return STAFF_PATH


def _page_links(href, page: int, total_pages: int) -> list[dict[str, object]]:
    links: list[dict[str, object]] = []
    for item in page_window(page, total_pages):
        if item is None:
            links.append({"ellipsis": True})
            continue
        links.append(
            {
                "ellipsis": False,
                "number": item,
                "url": href(page=item),
                "current": item == page,
            }
        )
    return links


def _toggle_order(current: str, column: str) -> str:
    if current == column:
        return f"-{column}"
    return column


def _toggle_role(selected: list[str], role: str) -> list[str]:
    picked = set(selected)
    if role in picked:
        picked.remove(role)
    else:
        picked.add(role)
    return [item for item in ROLE_ORDER if item in picked]


def _staff_pairs(
    *,
    page: int,
    size: int,
    ordering: str,
    q: str | None,
    roles: list[str],
) -> list[tuple[str, str]]:
    pairs: list[tuple[str, str]] = [
        ("page", str(page)),
        ("size", str(size)),
        ("ordering", ordering),
    ]
    if q:
        pairs.append(("q", q))
    pairs.extend(("role", value) for value in roles)
    return pairs


def _staff_url(**kwargs: object) -> str:
    return f"{STAFF_PATH}?{urlencode(_staff_pairs(**kwargs))}"  # type: ignore[arg-type]


def _wants_staff_partial(request: Request) -> bool:
    if request.headers.get("HX-History-Restore-Request") == "true":
        return False
    return request.headers.get("HX-Request") == "true"


async def _staff_list_data(
    *,
    page: int,
    size: int,
    ordering: str | None,
    q: str | None,
    roles: list[str],
) -> dict:
    size = page_size(size)
    ordering = normalize_staff_ordering(ordering)
    q_value = q.strip() if q and q.strip() else None
    selected = chosen_staff_roles(roles)
    role_filter = staff_role_filter(selected)

    async def _load(page_num: int) -> tuple[list, int, int]:
        rows, total = await list_staff_page(
            page=page_num,
            size=size,
            q=q_value,
            roles=role_filter,
            ordering=ordering,
        )
        pages = staff_total_pages(total, size)
        return rows, total, pages

    rows, total, pages = await _load(page)
    if pages and page > pages:
        page = pages
        rows, total, pages = await _load(page)

    state = {
        "page": page,
        "size": size,
        "ordering": ordering,
        "q": q_value,
        "roles": selected,
    }

    def href(**overrides: object) -> str:
        kwargs = dict(state)
        kwargs.update(overrides)
        return _staff_url(**kwargs)

    counts = await count_staff_by_role(q_value)
    role_options = [
        {
            "label": role,
            "count": counts.get(role, 0),
            "selected": role in selected,
            "href": href(page=1, roles=_toggle_role(selected, role)),
        }
        for role in ROLE_ORDER
    ]
    list_href = href()
    return {
        "users": [
            {
                "id": row["id"],
                "username": row["username"],
                "display_name": row["display_name"],
                "role": row["role"],
                "created_at": row["created_at"],
            }
            for row in rows
        ],
        "total": total,
        "page": page,
        "size": size,
        "page_sizes": PAGE_SIZES,
        "total_pages": pages,
        "ordering": ordering,
        "sort_urls": {
            col: href(page=1, ordering=_toggle_order(ordering, col))
            for col in STAFF_SORT_COLUMNS
        },
        "size_urls": {n: href(page=1, size=n) for n in PAGE_SIZES},
        "q": q_value or "",
        "selected_roles": selected,
        "role_options": role_options,
        "clear_role_url": href(page=1, roles=[]),
        "reset_url": href(page=1, roles=[]),
        "facets_active": bool(selected),
        "list_href": list_href,
        "page_links": _page_links(href, page, pages),
        "first_url": href(page=1) if page > 1 else None,
        "prev_url": href(page=page - 1) if page > 1 else None,
        "next_url": href(page=page + 1) if pages and page < pages else None,
        "last_url": href(page=pages) if pages and page < pages else None,
    }


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
    page: int = Query(1, ge=1),
    size: int = Query(DEFAULT_PAGE_SIZE, ge=1, le=100),
    ordering: str | None = Query(None),
    q: str = Query(""),
):
    data = await _staff_list_data(
        page=page,
        size=size,
        ordering=ordering,
        q=q,
        roles=request.query_params.getlist("role"),
    )
    template = (
        "partials/staff_panel.html"
        if _wants_staff_partial(request)
        else "admin_users.html"
    )
    return templates.TemplateResponse(
        request,
        template,
        _ctx(request, user, **data),
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
