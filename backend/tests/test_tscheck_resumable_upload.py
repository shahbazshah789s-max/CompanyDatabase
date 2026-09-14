"""Resumable chunked-upload criterion: uploads/init -> uploads/{id}/chunks/{index} ->
uploads/{id}/complete processes a small CSV in the background and lands it in file
history with a correct row count. Also verifies an oversized init request is rejected."""

import io
import time
import uuid

import httpx

OWNER_EMAIL = "shahbazshah789s@gmail.com"
OWNER_PASSWORD = "Owner@123456"


def _login(client: httpx.Client) -> httpx.Cookies:
    resp = client.post("/auth/login", json={"email": OWNER_EMAIL, "password": OWNER_PASSWORD})
    assert resp.status_code == 200, resp.text
    return resp.cookies


def _department_id(client: httpx.Client, cookies: httpx.Cookies) -> str:
    resp = client.get("/departments", cookies=cookies)
    assert resp.status_code == 200, resp.text
    deps = resp.json()
    assert deps, "expected at least one department to exist"
    return deps[0]["id"]


def test_resumable_chunk_upload_completes_and_lists_in_files(client: httpx.Client):
    cookies = _login(client)
    department_id = _department_id(client, cookies)

    slug = uuid.uuid4().hex[:8]
    filename = f"tscheck-upload-{slug}.csv"
    csv_body = "name,value\n" + "".join(f"row{i},val{i}\n" for i in range(5))
    csv_bytes = csv_body.encode()

    init = client.post(
        "/uploads/init",
        json={
            "filename": filename,
            "size_bytes": len(csv_bytes),
            "department_id": department_id,
            "total_chunks": 1,
        },
        cookies=cookies,
    )
    assert init.status_code == 200, init.text
    session = init.json()
    upload_id = session["id"]
    assert session["status"] == "uploading"

    chunk_resp = client.post(
        f"/uploads/{upload_id}/chunks/0",
        files={"chunk": (filename, io.BytesIO(csv_bytes), "text/csv")},
        cookies=cookies,
    )
    assert chunk_resp.status_code == 200, chunk_resp.text
    assert chunk_resp.json()["uploaded_chunks"] == 1

    complete = client.post(f"/uploads/{upload_id}/complete", cookies=cookies)
    assert complete.status_code == 200, complete.text
    assert complete.json()["status"] in ("processing", "complete")

    final_status = None
    for _ in range(30):
        status_resp = client.get(f"/uploads/{upload_id}", cookies=cookies)
        assert status_resp.status_code == 200, status_resp.text
        final_status = status_resp.json()
        if final_status["status"] in ("complete", "failed"):
            break
        time.sleep(1)
    assert final_status is not None
    assert final_status["status"] == "complete", final_status
    file_id = final_status["file_id"]
    assert file_id

    files_resp = client.get("/files", cookies=cookies)
    assert files_resp.status_code == 200, files_resp.text
    matching = [f for f in files_resp.json() if f["id"] == file_id]
    assert matching, "uploaded file did not appear in file history"
    assert matching[0]["name"] == filename
    assert matching[0]["row_count"] == 5

    # cleanup this check's own fixture file
    del_resp = client.delete(f"/files/{file_id}", cookies=cookies)
    assert del_resp.status_code == 200, del_resp.text


def test_upload_init_rejects_oversized_file(client: httpx.Client):
    cookies = _login(client)
    department_id = _department_id(client, cookies)
    over_limit = 1024 * 1024 * 1024 + 1
    resp = client.post(
        "/uploads/init",
        json={
            "filename": "tscheck-too-big.csv",
            "size_bytes": over_limit,
            "department_id": department_id,
            "total_chunks": 2,
        },
        cookies=cookies,
    )
    assert resp.status_code == 413, resp.text
