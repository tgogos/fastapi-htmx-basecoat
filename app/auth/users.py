"""User queries against SQLite."""

from __future__ import annotations

import re
import sqlite3
from math import ceil
from typing import Any, Optional

from app.db.connection import get_connection

ROLES = frozenset({"viewer", "editor", "admin"})
ROLE_ORDER = ("viewer", "editor", "admin")
ROLE_RANK = {"viewer": 1, "editor": 2, "admin": 3}

MIN_PASSWORD_LENGTH = 8
MAX_PASSWORD_BYTES = 72
MAX_DISPLAY_NAME_LENGTH = 80
_USERNAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")

STAFF_ORDER_SQL = {
    "username": "username COLLATE NOCASE ASC",
    "-username": "username COLLATE NOCASE DESC",
    "display_name": "display_name COLLATE NOCASE ASC",
    "-display_name": "display_name COLLATE NOCASE DESC",
    "role": "role COLLATE NOCASE ASC",
    "-role": "role COLLATE NOCASE DESC",
    "created": "created_at ASC",
    "-created": "created_at DESC",
}
DEFAULT_STAFF_ORDERING = "username"
STAFF_SORT_COLUMNS = ("display_name", "username", "role", "created")

_USER_COLUMNS = (
    "id, username, password_hash, role, display_name, session_version, created_at"
)


class UsernameTaken(Exception):
    """The sign-in name is already in use."""


def normalize_role(role: Optional[str]) -> str:
    if role in ROLES:
        return role  # type: ignore[return-value]
    return "viewer"


def role_at_least(role: str, minimum: str) -> bool:
    return ROLE_RANK.get(normalize_role(role), 0) >= ROLE_RANK[minimum]


def clean_username(value: str) -> str:
    text = value.strip()
    if not _USERNAME_RE.fullmatch(text):
        raise ValueError(
            "Username must start with a letter or number and use only letters, numbers, dots, underscores, or hyphens."
        )
    return text


def clean_display_name(value: str) -> Optional[str]:
    text = value.strip()
    if not text:
        return None
    if len(text) > MAX_DISPLAY_NAME_LENGTH:
        raise ValueError(
            f"Display name must be at most {MAX_DISPLAY_NAME_LENGTH} characters."
        )
    return text


def clean_password(value: str, confirm: str) -> str:
    if value != confirm:
        raise ValueError("Passwords do not match.")
    if len(value) < MIN_PASSWORD_LENGTH:
        raise ValueError(
            f"Password must be at least {MIN_PASSWORD_LENGTH} characters."
        )
    if len(value.encode("utf-8")) > MAX_PASSWORD_BYTES:
        raise ValueError("Password must be at most 72 bytes.")
    return value


def _row_to_user(row) -> dict[str, Any]:
    keys = row.keys()
    raw_name = row["display_name"] if "display_name" in keys else None
    display_name = raw_name.strip() if isinstance(raw_name, str) and raw_name.strip() else None
    if "session_version" in keys and row["session_version"] is not None:
        session_version = int(row["session_version"])
    else:
        session_version = 0
    return {
        "id": row["id"],
        "username": row["username"],
        "password_hash": row["password_hash"],
        "display_name": display_name,
        "role": normalize_role(row["role"] if "role" in keys else None),
        "session_version": session_version,
        "created_at": row["created_at"] if "created_at" in keys else None,
    }


def public_user(user: dict[str, Any]) -> dict[str, Any]:
    raw_name = user.get("display_name")
    display_name = raw_name.strip() if isinstance(raw_name, str) and raw_name.strip() else None
    return {
        "id": user["id"],
        "username": user["username"],
        "display_name": display_name,
        "role": normalize_role(user.get("role")),
    }


def normalize_staff_ordering(ordering: str | None) -> str:
    if ordering and ordering in STAFF_ORDER_SQL:
        return ordering
    return DEFAULT_STAFF_ORDERING


def chosen_staff_roles(values: list[str] | None) -> list[str]:
    """Keep known roles, in role order. Every role selected is the whole set."""
    picked = {value for value in values or [] if value in ROLES}
    return [role for role in ROLE_ORDER if role in picked]


def staff_role_filter(selected: list[str]) -> list[str] | None:
    """A partial set filters. An empty set or every role means no role filter."""
    if not selected or len(selected) == len(ROLE_ORDER):
        return None
    return selected


def _like_pattern(term: str) -> str:
    escaped = term.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escaped}%"


async def get_user_by_id(user_id: int) -> Optional[dict[str, Any]]:
    conn = get_connection()
    async with conn.execute(
        f"SELECT {_USER_COLUMNS} FROM users WHERE id = ?",
        (user_id,),
    ) as cursor:
        row = await cursor.fetchone()
    if row is None:
        return None
    return _row_to_user(row)


async def get_user_by_username(username: str) -> Optional[dict[str, Any]]:
    conn = get_connection()
    async with conn.execute(
        f"SELECT {_USER_COLUMNS} FROM users WHERE username = ?",
        (username,),
    ) as cursor:
        row = await cursor.fetchone()
    if row is None:
        return None
    return _row_to_user(row)


async def count_users() -> int:
    conn = get_connection()
    async with conn.execute("SELECT COUNT(*) AS c FROM users") as cursor:
        row = await cursor.fetchone()
    return int(row["c"])


async def count_admins() -> int:
    conn = get_connection()
    async with conn.execute(
        "SELECT COUNT(*) AS c FROM users WHERE role = 'admin'"
    ) as cursor:
        row = await cursor.fetchone()
    return int(row["c"])


def _user_where(
    q: str | None,
    roles: list[str] | None,
) -> tuple[str, list[Any]]:
    clauses: list[str] = []
    params: list[Any] = []
    if q and q.strip():
        like = _like_pattern(q.strip())
        clauses.append(
            "(username LIKE ? ESCAPE '\\' OR IFNULL(display_name, '') LIKE ? ESCAPE '\\')"
        )
        params.extend([like, like])
    if roles:
        marks = ", ".join("?" for _ in roles)
        clauses.append(f"role IN ({marks})")
        params.extend(roles)
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    return where, params


async def list_users(
    q: str | None = None,
    role: str | None = None,
) -> list[dict[str, Any]]:
    roles = [role] if role in ROLES else None
    where, params = _user_where(q, roles)
    conn = get_connection()
    async with conn.execute(
        f"""
        SELECT {_USER_COLUMNS}
        FROM users
        {where}
        ORDER BY username COLLATE NOCASE
        """,
        params,
    ) as cursor:
        rows = await cursor.fetchall()
    return [_row_to_user(r) for r in rows]


def staff_total_pages(total: int, size: int) -> int:
    return ceil(total / size) if total else 0


async def list_staff_page(
    *,
    page: int,
    size: int,
    q: str | None,
    roles: list[str] | None,
    ordering: str,
) -> tuple[list[dict[str, Any]], int]:
    """One page of staff. Filtering runs before LIMIT/OFFSET."""
    where, params = _user_where(q, roles)
    order_sql = STAFF_ORDER_SQL[ordering]
    conn = get_connection()
    async with conn.execute(
        f"SELECT COUNT(*) AS c FROM users {where}",
        params,
    ) as cursor:
        total = int((await cursor.fetchone())["c"])
    offset = (page - 1) * size
    async with conn.execute(
        f"""
        SELECT {_USER_COLUMNS}
        FROM users
        {where}
        ORDER BY {order_sql}
        LIMIT ? OFFSET ?
        """,
        [*params, size, offset],
    ) as cursor:
        rows = await cursor.fetchall()
    return [_row_to_user(row) for row in rows], total


async def count_staff_by_role(q: str | None) -> dict[str, int]:
    """Role counts for the current search, ignoring any role filter."""
    where, params = _user_where(q, None)
    conn = get_connection()
    async with conn.execute(
        f"SELECT role, COUNT(*) AS c FROM users {where} GROUP BY role",
        params,
    ) as cursor:
        rows = await cursor.fetchall()
    return {row["role"]: int(row["c"]) for row in rows}


async def create_user(
    username: str,
    password_hash: str,
    role: str = "viewer",
    display_name: str | None = None,
) -> dict[str, Any]:
    role = normalize_role(role)
    conn = get_connection()
    try:
        cursor = await conn.execute(
            """
            INSERT INTO users (username, password_hash, role, display_name)
            VALUES (?, ?, ?, ?)
            """,
            (username, password_hash, role, display_name),
        )
        await conn.commit()
    except sqlite3.IntegrityError as exc:
        await conn.rollback()
        raise UsernameTaken(username) from exc
    user = await get_user_by_id(cursor.lastrowid)
    assert user is not None
    return user


async def update_user(
    user_id: int,
    *,
    display_name: str | None,
    role: str,
) -> Optional[dict[str, Any]]:
    role = normalize_role(role)
    if role not in ROLES:
        raise ValueError("Invalid role.")
    conn = get_connection()
    cursor = await conn.execute(
        "UPDATE users SET display_name = ?, role = ? WHERE id = ?",
        (display_name, role, user_id),
    )
    await conn.commit()
    if cursor.rowcount == 0:
        return None
    return await get_user_by_id(user_id)


async def set_user_role(user_id: int, role: str) -> Optional[dict[str, Any]]:
    role = normalize_role(role)
    if role not in ROLES:
        raise ValueError(f"Invalid role: {role}")
    current = await get_user_by_id(user_id)
    if current is None:
        return None
    return await update_user(
        user_id,
        display_name=current["display_name"],
        role=role,
    )


async def set_password(user_id: int, password_hash: str) -> Optional[dict[str, Any]]:
    """Replace the password, bump the session version, and drop API tokens."""
    conn = get_connection()
    cursor = await conn.execute(
        """
        UPDATE users
        SET password_hash = ?, session_version = session_version + 1
        WHERE id = ?
        """,
        (password_hash, user_id),
    )
    await conn.execute("DELETE FROM api_tokens WHERE user_id = ?", (user_id,))
    await conn.commit()
    if cursor.rowcount == 0:
        return None
    return await get_user_by_id(user_id)
