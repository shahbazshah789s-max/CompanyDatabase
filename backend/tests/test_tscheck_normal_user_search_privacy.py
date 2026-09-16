"""Normal-user search privacy: blank/short queries reveal nothing; matching queries reveal only matches."""

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
KNOWN_NUMBER = "14795569494"


@pytest.fixture
def normal_user():
    """Owner creates a temp normal User assigned to Bid Well, yields (email, password), then deletes it."""
    owner = httpx.Client(base_url=api_url(), timeout=30.0)
    resp = owner.post("/auth/login", json={"email": OWNER_EMAIL, "password": OWNER_PASSWORD})
    assert resp.status_code == 200, resp.text

    depts = owner.get("/departments")
    assert depts.status_code == 200, depts.text
    dept_list = depts.json()
    assert len(dept_list) > 0
    dept_id = dept_list[0]["id"]

    slug = str(int(time.time() * 1000))
    email = f"tscheck-search-privacy-{slug}@example.com"
    password = "Password123"
    create = owner.post(
        "/users",
        json={
            "name": f"tscheck-search-privacy-{slug}",
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


def test_blank_search_returns_zero_rows(normal_user):
    email, password = normal_user
    c = _login_as(email, password)
    resp = c.get("/search", params={"q": ""})
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["total"] == 0
    assert body["items"] == []
    c.close()


def test_short_query_returns_zero_rows(normal_user):
    email, password = normal_user
    c = _login_as(email, password)
    for q in ["1", "14"]:
        resp = c.get("/search", params={"q": q})
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["total"] == 0, f"query {q!r} leaked rows: {body}"
    c.close()


def test_matching_query_reveals_only_matching_rows(normal_user):
    email, password = normal_user
    c = _login_as(email, password)
    resp = c.get("/search", params={"q": KNOWN_NUMBER})
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["total"] >= 1, f"expected known number to be found: {body}"
    for item in body["items"]:
        assert KNOWN_NUMBER in str(item.get("data")), item
    c.close()
