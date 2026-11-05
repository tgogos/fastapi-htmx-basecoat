"""Unit checks for safe in-app redirect targets."""

from __future__ import annotations

import pytest

from app.ui.redirects import safe_relative_path
from app.ui.shell import safe_shell_next
from app.ui.user_routes import STAFF_PATH, _staff_return

pytestmark = pytest.mark.no_client


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("/ui/dashboard", "/ui/dashboard"),
        ("/ui/admin/users?page=2", "/ui/admin/users?page=2"),
        ("https://evil.example/", "/fallback"),
        ("//evil.example/phish", "/fallback"),
        ("\\/\\/evil.example/phish", "/fallback"),
        ("https:/evil.example", "/fallback"),
        ("", "/fallback"),
        ("ui/relative", "/fallback"),
    ],
)
def test_safe_relative_path(value: str, expected: str):
    assert safe_relative_path(value, fallback="/fallback") == expected


def test_safe_shell_next_fallback():
    assert safe_shell_next("https://evil.example/") == "/ui/settings"
    assert safe_shell_next("/ui/dashboard") == "/ui/dashboard"


def test_staff_return_allowlist():
    assert _staff_return("/ui/admin/users?page=2&size=25") == (
        "/ui/admin/users?page=2&size=25"
    )
    assert _staff_return("/ui/dashboard") == STAFF_PATH
    assert _staff_return("https://evil.example/") == STAFF_PATH
