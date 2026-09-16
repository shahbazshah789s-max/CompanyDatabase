"""Owner and Pro Admin retain scoped browse behavior (no blank-search restriction unlike normal Users)."""

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
def owner_client():
    c = httpx.Client(base_url=api_url(), timeout=30.0)
    resp = c.post("/auth/login", json={"email": OWNER_EMAIL, "password": OWNER_PASSWORD})
    assert resp.status_code == 200, resp.text
    yield c
    c.close()


@pytest.fixture
def pro_admin(owner_client):
    depts = owner_client.get("/departments")
    assert depts.status_code == 200, depts.text
    dept_id = depts.json()[0]["id"]

    slug = str(int(time.time() * 1000))
    email = f"tscheck-proadmin-browse-{slug}@example.com"
    password = "Password123"
    create = owner_client.post(
        "/users",
        json={
            "name": f"tscheck-proadmin-browse-{slug}",
            "email": email,
            "password": password,
            "role": "pro_admin",
            "department_ids": [dept_id],
        },
    )
    assert create.status_code == 200, create.text
    user_id = create.json()["id"]

    yield email, password, dept_id

    delete = owner_client.delete(f"/users/{user_id}")
    assert delete.status_code == 200, delete.text


def _login_as(email: str, password: str) -> httpx.Client:
    c = httpx.Client(base_url=api_url(), timeout=30.0)
    resp = c.post("/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 200, resp.text
    return c


def test_owner_can_browse_without_query(owner_client):
    resp = owner_client.get("/search")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["total"] > 0, "Owner blank search should browse all data, not return 0"


def test_pro_admin_can_browse_assigned_team_without_query(pro_admin):
    email, password, dept_id = pro_admin
    c = _login_as(email, password)
    resp = c.get("/search")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["total"] > 0, "Pro Admin blank search should browse assigned-team data, not return 0"
    for item in body["items"]:
        assert item["department_id"] == dept_id
    c.close()
