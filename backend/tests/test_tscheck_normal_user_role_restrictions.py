"""Normal User cannot browse/download files nor bulk-delete records via the API."""

import os
import time

import httpx
import pytest

BACKEND_URL = os.environ.get("BACKEND_URL", "http://localhost:8001")
API_URL = f"{BACKEND_URL}/api"


def api_url(path: str = "") -> str:
    return f"{API_URL}{path}"


OWNER_EMAIL = "shahbazshah789s@gmail.com"
OWNER_PASSWORD = "Owner@123456"


@pytest.fixture
def normal_user():
    owner = httpx.Client(base_url=api_url(), timeout=30.0)
    resp = owner.post("/auth/login", json={"email": OWNER_EMAIL, "password": OWNER_PASSWORD})
    assert resp.status_code == 200, resp.text

    depts = owner.get("/departments")
    assert depts.status_code == 200, depts.text
    dept_id = depts.json()[0]["id"]

    slug = str(int(time.time() * 1000))
    email = f"tscheck-role-restrict-{slug}@example.com"
    password = "Password123"
    create = owner.post(
        "/users",
        json={
            "name": f"tscheck-role-restrict-{slug}",
            "email": email,
            "password": password,
            "role": "user",
            "department_ids": [dept_id],
        },
    )
    assert create.status_code == 200, create.text
    user_id = create.json()["id"]

    yield email, password

    delete = owner.delete(f"/users/{user_id}")
    assert delete.status_code == 200, delete.text
    owner.close()


def _login_as(email: str, password: str) -> httpx.Client:
    c = httpx.Client(base_url=api_url(), timeout=30.0)
    resp = c.post("/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 200, resp.text
    return c


def test_normal_user_files_list_forbidden(normal_user):
    email, password = normal_user
    c = _login_as(email, password)
    resp = c.get("/files")
    assert resp.status_code == 403, resp.text
    c.close()


def test_normal_user_file_download_forbidden(normal_user):
    email, password = normal_user
    c = _login_as(email, password)
    resp = c.get("/files/nonexistent-id/download")
    assert resp.status_code == 403, resp.text
    c.close()


def test_normal_user_bulk_delete_forbidden(normal_user):
    email, password = normal_user
    c = _login_as(email, password)
    resp = c.post("/search/bulk-delete", json=["nonexistent-id"])
    assert resp.status_code == 403, resp.text
    c.close()
