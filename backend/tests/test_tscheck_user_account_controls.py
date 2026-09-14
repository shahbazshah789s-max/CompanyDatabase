"""Owner user-account controls criterion: owner can create a user, block/unblock,
bulk-replace access, and delete individually / in bulk. Also verifies a non-owner
is rejected from these endpoints."""

import uuid

import httpx

OWNER_EMAIL = "shahbazshah789s@gmail.com"
OWNER_PASSWORD = "Owner@123456"


def _login(client: httpx.Client, email: str, password: str) -> httpx.Cookies:
    resp = client.post("/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 200, resp.text
    return resp.cookies


def _owner_cookies(client: httpx.Client) -> httpx.Cookies:
    return _login(client, OWNER_EMAIL, OWNER_PASSWORD)


def test_owner_can_create_block_and_delete_user(client: httpx.Client):
    cookies = _owner_cookies(client)
    slug = uuid.uuid4().hex[:8]
    email = f"tscheck-user-{slug}@example.com"

    create = client.post(
        "/users",
        json={"name": f"tscheck user {slug}", "email": email, "password": "Password123", "role": "user", "department_ids": []},
        cookies=cookies,
    )
    assert create.status_code == 200, create.text
    user = create.json()
    user_id = user["id"]
    assert user["status"] == "active"

    block = client.patch(f"/users/{user_id}", json={"status": "disabled"}, cookies=cookies)
    assert block.status_code == 200, block.text
    assert block.json()["status"] == "disabled"

    blocked_login = client.post("/auth/login", json={"email": email, "password": "Password123"})
    assert blocked_login.status_code == 403, blocked_login.text

    unblock = client.patch(f"/users/{user_id}", json={"status": "active"}, cookies=cookies)
    assert unblock.status_code == 200, unblock.text
    assert unblock.json()["status"] == "active"

    departments = client.get("/departments", cookies=cookies).json()
    if departments:
        bulk_access = client.post(
            "/users/bulk-access",
            json={"user_ids": [user_id], "department_ids": [departments[0]["id"]], "mode": "replace"},
            cookies=cookies,
        )
        assert bulk_access.status_code == 200, bulk_access.text

    delete = client.delete(f"/users/{user_id}", cookies=cookies)
    assert delete.status_code == 200, delete.text

    listing = client.get("/users", cookies=cookies).json()
    assert not any(u["id"] == user_id for u in listing)


def test_owner_bulk_delete_users(client: httpx.Client):
    cookies = _owner_cookies(client)
    slug = uuid.uuid4().hex[:8]
    ids = []
    for i in range(2):
        email = f"tscheck-bulk-{slug}-{i}@example.com"
        create = client.post(
            "/users",
            json={"name": f"tscheck bulk {slug} {i}", "email": email, "password": "Password123", "role": "user", "department_ids": []},
            cookies=cookies,
        )
        assert create.status_code == 200, create.text
        ids.append(create.json()["id"])

    bulk_delete = client.post("/users/bulk-delete", json=ids, cookies=cookies)
    assert bulk_delete.status_code == 200, bulk_delete.text
    assert bulk_delete.json()["affected"] == 2

    listing = client.get("/users", cookies=cookies).json()
    assert not any(u["id"] in ids for u in listing)


def test_non_owner_cannot_list_users(client: httpx.Client):
    cookies = _owner_cookies(client)
    slug = uuid.uuid4().hex[:8]
    email = f"tscheck-nonowner-{slug}@example.com"
    create = client.post(
        "/users",
        json={"name": f"tscheck nonowner {slug}", "email": email, "password": "Password123", "role": "user", "department_ids": []},
        cookies=cookies,
    )
    assert create.status_code == 200, create.text
    user_id = create.json()["id"]

    user_cookies = _login(client, email, "Password123")
    resp = client.get("/users", cookies=user_cookies)
    assert resp.status_code == 403, resp.text

    client.delete(f"/users/{user_id}", cookies=cookies)
