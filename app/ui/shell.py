"""Which admin shell to paint.

`header` is the sidebar plus a content header. `sidebar` is the sidebar alone.
The cookie is a display preference, not a credential.
"""

from __future__ import annotations

from starlette.requests import Request

SHELL_LAYOUTS = ("header", "sidebar")
SHELL_COOKIE = "shell_layout"
DEFAULT_SHELL_LAYOUT = "header"


def current_shell_layout(request: Request) -> str:
    value = request.cookies.get(SHELL_COOKIE, "")
    if value in SHELL_LAYOUTS:
        return value
    return DEFAULT_SHELL_LAYOUT


def safe_shell_next(value: str) -> str:
    if (
        not value.startswith("/")
        or value.startswith("//")
        or "\\" in value
        or "://" in value
    ):
        return "/ui/settings"
    return value
