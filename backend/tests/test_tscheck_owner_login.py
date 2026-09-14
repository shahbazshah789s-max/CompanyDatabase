"""Owner login criterion: owner can sign in with provided credentials and gets a
valid session; wrong password is rejected."""

import httpx


OWNER_EMAIL = "shahbazshah789s@gmail.com"
OWNER_PASSWORD = "Owner@123456"


def test_owner_login_success(client: httpx.Client):
    resp = client.post("/auth/login", json={"email": OWNER_EMAIL, "password": OWNER_PASSWORD})
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["user"]["role"] == "owner"
    assert body["user"]["email"] == OWNER_EMAIL
    assert "wingman_session" in resp.cookies

    me = client.get("/auth/me", cookies=resp.cookies)
    assert me.status_code == 200, me.text
    assert me.json()["email"] == OWNER_EMAIL


def test_owner_login_wrong_password_rejected(client: httpx.Client):
    resp = client.post("/auth/login", json={"email": OWNER_EMAIL, "password": "WrongPassword123"})
    assert resp.status_code == 401, resp.text
