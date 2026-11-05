"""Safe in-app redirect targets (CWE-601).

User-supplied ``next`` / ``return_to`` values must never become an absolute URL
to another host. Prefer tokens the server maps to a URL (books list place). When
a relative path is unavoidable, use ``safe_relative_path``.
"""

from __future__ import annotations

from urllib.parse import urlparse


def safe_relative_path(value: str, *, fallback: str) -> str:
    """Allow only a same-origin path (optional query/fragment); else ``fallback``.

    Mirrors the common ``urlparse`` guard: strip backslashes, reject any URL with
    a scheme or host, require a leading ``/``.
    """
    target = (value or "").strip().replace("\\", "")
    parsed = urlparse(target)
    if (
        target.startswith("/")
        and not parsed.netloc
        and not parsed.scheme
    ):
        return target
    return fallback
