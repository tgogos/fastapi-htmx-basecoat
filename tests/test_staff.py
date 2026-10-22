"""Users directory and the signed-in person's profile."""

import os
import re

from fastapi.testclient import TestClient

from tests.conftest import create_user_sync, login_as, session_csrf_headers


def _csrf(html: str) -> str:
    return html.split('name="csrf_token" value="', 1)[1].split('"', 1)[0]


def _staff_id(html: str, username: str) -> str:
    row = re.search(
        rf"{re.escape(username)}.*?/ui/admin/users/(\d+)/edit",
        html,
        re.DOTALL,
    )
    assert row, html
    return row.group(1)


def test_staff_list_is_admin_only(client: TestClient):
    create_user_sync("editor2", "editorpass", role="editor")
    login_as(client, "editor2", "editorpass")
    assert client.get("/ui/admin/users").status_code == 403
    assert client.get("/ui/admin/users/new").status_code == 403

    login_as(client, os.environ["DEMO_USERNAME"], os.environ["DEMO_PASSWORD"])
    page = client.get("/ui/admin/users")
    assert page.status_code == 200
    assert "<h1>Users</h1>" in page.text
    assert ">Staff</span>" not in page.text
    assert "Add user" in page.text
    assert "Display name" in page.text
    assert os.environ["DEMO_USERNAME"] in page.text
    assert "alex.rivera@example.com" not in page.text


def test_sample_users_page_stays_a_sample(auth_client: TestClient):
    page = auth_client.get("/ui/users")
    assert page.status_code == 200
    assert "alex.rivera@example.com" in page.text


def test_admin_adds_and_filters_staff(auth_client: TestClient):
    form = auth_client.get("/ui/admin/users/new")
    created = auth_client.post(
        "/ui/admin/users/new",
        data={
            "csrf_token": _csrf(form.text),
            "username": "ada",
            "display_name": "Ada Lovelace",
            "role": "editor",
            "password": "editorpass",
            "password_confirm": "editorpass",
            "return_to": "/ui/admin/users",
        },
        follow_redirects=False,
    )
    assert created.status_code == 303
    assert created.headers["location"] == "/ui/admin/users"

    listed = auth_client.get("/ui/admin/users")
    assert "Ada Lovelace" in listed.text
    assert "ada" in listed.text

    by_name = auth_client.get("/ui/admin/users", params={"q": "Lovelace"})
    assert "ada" in by_name.text
    assert "(you)" not in by_name.text

    by_role = auth_client.get("/ui/admin/users", params={"role": "editor"})
    assert "ada" in by_role.text
    assert "(you)" not in by_role.text

    short = auth_client.post(
        "/ui/admin/users/new",
        data={
            "csrf_token": _csrf(form.text),
            "username": "short",
            "display_name": "",
            "role": "viewer",
            "password": "tiny",
            "password_confirm": "tiny",
        },
    )
    assert short.status_code == 400
    assert "at least 8 characters" in short.text

    duplicate = auth_client.post(
        "/ui/admin/users/new",
        data={
            "csrf_token": _csrf(auth_client.get("/ui/admin/users/new").text),
            "username": "ada",
            "display_name": "Someone else",
            "role": "viewer",
            "password": "editorpass",
            "password_confirm": "editorpass",
        },
    )
    assert duplicate.status_code == 400
    assert "already in use" in duplicate.text


def test_admin_edits_display_name_and_role(auth_client: TestClient):
    create_user_sync("ada", "editorpass", role="viewer")
    listing = auth_client.get("/ui/admin/users")
    user_id = _staff_id(listing.text, "ada")
    form = auth_client.get(f"/ui/admin/users/{user_id}/edit")
    saved = auth_client.post(
        f"/ui/admin/users/{user_id}/edit",
        data={
            "csrf_token": _csrf(form.text),
            "display_name": "Ada Lovelace",
            "role": "editor",
            "return_to": "/ui/admin/users",
        },
        follow_redirects=True,
    )
    assert saved.status_code == 200
    assert re.search(r"ada</td>\s*<td><code>editor</code>", saved.text)


def test_cannot_demote_the_last_admin(auth_client: TestClient):
    listing = auth_client.get("/ui/admin/users")
    user_id = _staff_id(listing.text, os.environ["DEMO_USERNAME"])
    form = auth_client.get(f"/ui/admin/users/{user_id}/edit")
    denied = auth_client.post(
        f"/ui/admin/users/{user_id}/edit",
        data={
            "csrf_token": _csrf(form.text),
            "display_name": "",
            "role": "viewer",
        },
    )
    assert denied.status_code == 400
    assert "last admin" in denied.text


def test_set_password_signs_the_user_out_and_revokes_tokens(client: TestClient):
    create_user_sync("ada", "oldpass123", role="viewer")
    token = client.post(
        "/api/auth/token",
        json={"username": "ada", "password": "oldpass123"},
    )
    assert token.status_code == 200
    raw = token.json()["access_token"]

    login_as(client, "ada", "oldpass123")
    ada_cookies = {cookie.name: cookie.value for cookie in client.cookies.jar}

    login_as(client, os.environ["DEMO_USERNAME"], os.environ["DEMO_PASSWORD"])
    listing = client.get("/ui/admin/users")
    user_id = _staff_id(listing.text, "ada")
    form = client.get(f"/ui/admin/users/{user_id}/password")
    saved = client.post(
        f"/ui/admin/users/{user_id}/password",
        data={
            "csrf_token": _csrf(form.text),
            "password": "newpass123",
            "password_confirm": "newpass123",
            "return_to": "/ui/admin/users",
        },
        follow_redirects=False,
    )
    assert saved.status_code == 303

    stale = client.get("/api/auth/me", headers={"Authorization": f"Bearer {raw}"})
    assert stale.status_code == 401

    client.cookies.clear()
    for name, value in ada_cookies.items():
        client.cookies.set(name, value)
    bounced = client.get("/ui/dashboard", follow_redirects=False)
    assert bounced.status_code == 303
    assert bounced.headers["location"] == "/auth/login"

    old_login = client.post(
        "/auth/login",
        data={
            "username": "ada",
            "password": "oldpass123",
            "csrf_token": _csrf(client.get("/auth/login").text),
        },
        follow_redirects=False,
    )
    assert old_login.status_code == 400

    login_as(client, "ada", "newpass123")
    home = client.get("/ui/dashboard")
    assert home.status_code == 200


def test_me_includes_display_name(client: TestClient):
    login_as(client, os.environ["DEMO_USERNAME"], os.environ["DEMO_PASSWORD"])
    me = client.get("/api/auth/me", headers=session_csrf_headers(client))
    assert me.status_code == 200
    assert me.json()["display_name"] is None

    create_user_sync("ada", "editorpass", role="editor")
    listing = client.get("/ui/admin/users")
    user_id = _staff_id(listing.text, "ada")
    form = client.get(f"/ui/admin/users/{user_id}/edit")
    client.post(
        f"/ui/admin/users/{user_id}/edit",
        data={
            "csrf_token": _csrf(form.text),
            "display_name": "Ada Lovelace",
            "role": "editor",
        },
        follow_redirects=False,
    )
    login_as(client, "ada", "editorpass")
    ada = client.get("/api/auth/me", headers=session_csrf_headers(client))
    assert ada.json()["display_name"] == "Ada Lovelace"
    assert ada.json()["username"] == "ada"
    assert "Ada Lovelace" in client.get("/ui/dashboard").text


def test_staff_list_uses_the_table_contract(auth_client: TestClient):
    create_user_sync("aaa", "editorpass", role="viewer")
    create_user_sync("ada", "editorpass", role="editor")
    create_user_sync("zzz", "editorpass", role="admin")
    for index in range(8):
        create_user_sync(f"page{index}", "editorpass", role="viewer")

    both = auth_client.get(
        "/ui/admin/users",
        params=[("role", "editor"), ("role", "viewer"), ("q", "ada")],
    )
    assert both.status_code == 200
    assert "ada" in both.text
    assert "(you)" not in both.text
    assert "aaa" not in both.text
    reset = re.search(r'href="([^"]+)"[^>]*>\s*Reset', both.text)
    assert reset
    assert "q=ada" in reset.group(1)
    assert "role=" not in reset.group(1)

    everyone = auth_client.get(
        "/ui/admin/users",
        params=[("role", "viewer"), ("role", "editor"), ("role", "admin")],
    )
    assert "(you)" in everyone.text

    ordered = auth_client.get(
        "/ui/admin/users",
        params={"ordering": "-username", "size": 100},
    )
    body = ordered.text.split("<tbody>", 1)[1].split("</tbody>", 1)[0]
    assert body.find("zzz") < body.find("aaa")

    fallback = auth_client.get("/ui/admin/users", params={"ordering": "not-a-column"})
    assert 'href="/ui/admin/users?page=1&amp;size=10&amp;ordering=-username"' in fallback.text

    first = auth_client.get("/ui/admin/users", params={"size": 10})
    assert "Page 1 of 2" in first.text
    second = auth_client.get("/ui/admin/users", params={"page": 2, "size": 10})
    assert "Page 2 of 2" in second.text
    assert "page7" in second.text
    assert "page7" not in first.text

    partial = auth_client.get("/ui/admin/users", headers={"HX-Request": "true"})
    assert 'id="staff-q"' not in partial.text
    assert "Rows per page" in partial.text
    restored = auth_client.get(
        "/ui/admin/users",
        headers={"HX-Request": "true", "HX-History-Restore-Request": "true"},
    )
    assert 'id="staff-q"' in restored.text
    assert "Add user" in restored.text
    assert "data-staff-return" in restored.text


def test_profile_saves_own_display_name(client: TestClient):
    create_user_sync("ada", "editorpass", role="viewer")
    login_as(client, "ada", "editorpass")
    page = client.get("/ui/settings/profile")
    assert page.status_code == 200
    assert 'aria-current="page">Profile</a>' in page.text
    assert 'href="/ui/settings"' in page.text
    assert 'id="profile-username"' in page.text
    assert 'value="ada"' in page.text
    assert 'value="viewer"' in page.text
    assert 'name="role"' not in page.text
    assert 'name="username"' not in page.text
    assert 'type="password"' not in page.text
    assert ">Settings</span>" in page.text

    too_long = client.post(
        "/ui/settings/profile",
        data={"csrf_token": _csrf(page.text), "display_name": "x" * 81},
    )
    assert too_long.status_code == 400
    assert "at most 80" in too_long.text

    saved = client.post(
        "/ui/settings/profile",
        data={
            "csrf_token": _csrf(page.text),
            "display_name": "Ada Lovelace",
            "role": "admin",
        },
        follow_redirects=False,
    )
    assert saved.status_code == 303
    assert saved.headers["location"] == "/ui/settings/profile"

    again = client.get("/ui/settings/profile")
    assert 'value="Ada Lovelace"' in again.text
    assert 'value="viewer"' in again.text
    assert "Display name saved" in again.text
    assert 'aria-label="Ada Lovelace"' in again.text
    me = client.get("/api/auth/me", headers=session_csrf_headers(client))
    assert me.json()["display_name"] == "Ada Lovelace"
    assert me.json()["role"] == "viewer"
    assert me.json()["username"] == "ada"

    cleared = client.post(
        "/ui/settings/profile",
        data={"csrf_token": _csrf(again.text), "display_name": "   "},
        follow_redirects=False,
    )
    assert cleared.status_code == 303
    home = client.get("/ui/dashboard")
    assert 'aria-label="ada"' in home.text
    cleared_me = client.get("/api/auth/me", headers=session_csrf_headers(client))
    assert cleared_me.json()["display_name"] is None
    assert cleared_me.json()["role"] == "viewer"


def test_account_changes_own_password(client: TestClient):
    create_user_sync("ada", "oldpass123", role="viewer")
    token = client.post(
        "/api/auth/token",
        json={"username": "ada", "password": "oldpass123"},
    )
    assert token.status_code == 200
    raw = token.json()["access_token"]

    login_as(client, "ada", "oldpass123")
    page = client.get("/ui/settings/account")
    assert page.status_code == 200
    assert 'aria-current="page">Account</a>' in page.text
    nav = page.text.split('aria-label="Settings"', 1)[1].split("</nav>", 1)[0]
    assert nav.find(">Profile</a>") < nav.find(">Account</a>") < nav.find(">Appearance</a>")
    assert 'name="current_password"' in page.text
    assert 'name="role"' not in page.text

    wrong = client.post(
        "/ui/settings/account",
        data={
            "csrf_token": _csrf(page.text),
            "current_password": "not-the-password",
            "password": "newpass123",
            "password_confirm": "newpass123",
        },
    )
    assert wrong.status_code == 400
    assert "Current password is incorrect." in wrong.text

    mismatch = client.post(
        "/ui/settings/account",
        data={
            "csrf_token": _csrf(page.text),
            "current_password": "oldpass123",
            "password": "newpass123",
            "password_confirm": "otherpass1",
        },
    )
    assert mismatch.status_code == 400
    assert "do not match" in mismatch.text

    saved = client.post(
        "/ui/settings/account",
        data={
            "csrf_token": _csrf(page.text),
            "current_password": "oldpass123",
            "password": "newpass123",
            "password_confirm": "newpass123",
        },
        follow_redirects=False,
    )
    assert saved.status_code == 303
    assert saved.headers["location"] == "/ui/settings/account"

    again = client.get("/ui/settings/account")
    assert again.status_code == 200
    assert "Password updated" in again.text
    me = client.get("/api/auth/me", headers=session_csrf_headers(client))
    assert me.json()["username"] == "ada"
    assert me.json()["role"] == "viewer"

    stale = client.get("/api/auth/me", headers={"Authorization": f"Bearer {raw}"})
    assert stale.status_code == 401
    old = client.post(
        "/api/auth/token",
        json={"username": "ada", "password": "oldpass123"},
    )
    assert old.status_code == 401
    new = client.post(
        "/api/auth/token",
        json={"username": "ada", "password": "newpass123"},
    )
    assert new.status_code == 200
