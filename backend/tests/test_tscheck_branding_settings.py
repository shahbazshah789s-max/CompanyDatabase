"""Owner branding criterion: owner can update company name/logo/nav labels and the
change persists via GET /branding. Also verifies validation rejects an invalid name."""

import uuid

import httpx

OWNER_EMAIL = "shahbazshah789s@gmail.com"
OWNER_PASSWORD = "Owner@123456"

TINY_PNG_DATA_URL = (
    "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII="
)


def _owner_cookies(client: httpx.Client) -> httpx.Cookies:
    resp = client.post("/auth/login", json={"email": OWNER_EMAIL, "password": OWNER_PASSWORD})
    assert resp.status_code == 200, resp.text
    return resp.cookies


def test_owner_updates_branding_and_it_persists(client: httpx.Client):
    cookies = _owner_cookies(client)

    original = client.get("/branding", cookies=cookies)
    assert original.status_code == 200, original.text
    original_body = original.json()

    slug = uuid.uuid4().hex[:6]
    new_name = f"TsCheck Co {slug}"
    payload = {
        "company_name": new_name,
        "logo_data_url": TINY_PNG_DATA_URL,
        "nav_labels": original_body.get("nav_labels", {}),
    }
    update = client.put("/branding", json=payload, cookies=cookies)
    assert update.status_code == 200, update.text
    assert update.json()["company_name"] == new_name
    assert update.json()["logo_data_url"] == TINY_PNG_DATA_URL

    fetched = client.get("/branding", cookies=cookies)
    assert fetched.status_code == 200, fetched.text
    assert fetched.json()["company_name"] == new_name

    # restore original branding so other checks (and the UI) see the default state
    restore_payload = {
        "company_name": original_body.get("company_name", "Company Database"),
        "logo_data_url": original_body.get("logo_data_url"),
        "nav_labels": original_body.get("nav_labels", {}),
    }
    restore = client.put("/branding", json=restore_payload, cookies=cookies)
    assert restore.status_code == 200, restore.text


def test_owner_branding_rejects_invalid_company_name(client: httpx.Client):
    cookies = _owner_cookies(client)
    original = client.get("/branding", cookies=cookies).json()
    resp = client.put(
        "/branding",
        json={"company_name": "A", "logo_data_url": original.get("logo_data_url"), "nav_labels": original.get("nav_labels", {})},
        cookies=cookies,
    )
    assert resp.status_code == 422, resp.text
