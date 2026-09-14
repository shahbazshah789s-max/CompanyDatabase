import base64
import csv
import hashlib
import io
import re
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Cookie, File, Form, HTTPException, UploadFile
from fastapi.responses import Response

from lib.db import db
from models.portal import (
    ActionResponse, ApprovalAction, ApprovalSummary, BulkAccessRequest, BulkLookupRequest,
    BulkLookupResponse, DashboardStats, Department, DepartmentCreate, FileAsset, FileUploadResponse,
    RecordRow, RecordSearchResponse, UserCreate, UserPublic, UserUpdate,
)
from routers.auth import current_user, _hash_password, _public, require_owner

router = APIRouter(tags=["portal"])


async def scoped_department_ids(user: dict) -> list[str] | None:
    if user["role"] == "owner":
        return None
    return user.get("department_ids", [])


async def department_map() -> dict[str, dict]:
    return {d["id"]: d async for d in db.departments.find({})}


def _file(doc: dict, departments: dict[str, dict]) -> FileAsset:
    department = departments.get(doc.get("department_id"), {})
    return FileAsset(
        id=doc["id"], name=doc["name"], department_id=doc.get("department_id", ""),
        department_name=department.get("name", "All departments"), size_bytes=doc.get("size_bytes", 0),
        row_count=doc.get("row_count", 0), inserted_count=doc.get("inserted_count", 0),
        skipped_count=doc.get("skipped_count", 0), uploaded_by=doc.get("uploaded_by", ""),
        uploaded_at=doc["uploaded_at"],
    )


async def _record(doc: dict, departments: dict[str, dict]) -> RecordRow:
    file_doc = await db.files.find_one({"id": doc["file_id"]})
    return RecordRow(id=doc["id"], file_id=doc["file_id"], file_name=file_doc["name"] if file_doc else "Unknown file",
                     department_id=doc.get("department_id", ""), department_name=departments.get(doc.get("department_id"), {}).get("name", "Unassigned"),
                     data=doc.get("data", {}), created_at=doc["created_at"])


@router.get("/dashboard", response_model=DashboardStats)
async def dashboard(wingman_session: str | None = Cookie(default=None)):
    user = await current_user(wingman_session)
    scopes = await scoped_department_ids(user)
    record_filter = {} if scopes is None else {"department_id": {"$in": scopes}}
    files_filter = {} if scopes is None else {"department_id": {"$in": scopes}}
    departments = await db.departments.count_documents({} if scopes is None else {"id": {"$in": scopes}})
    users = await db.users.count_documents({"status": "active"})
    pending = await db.users.count_documents({"status": "pending"}) if user["role"] in ("owner", "admin") else 0
    docs = await db.files.find(files_filter).sort("uploaded_at", -1).limit(5).to_list(5)
    breakdown = await db.records.aggregate([{"$match": record_filter}, {"$group": {"_id": "$department_id", "count": {"$sum": 1}}}, {"$sort": {"count": -1}}]).to_list(20)
    dep_map = await department_map()
    return DashboardStats(total_records=await db.records.count_documents(record_filter), active_departments=departments,
                          active_users=users, pending_requests=pending, recent_files=[_file(f, dep_map) for f in docs],
                          department_breakdown=[{"department_id": x["_id"], "name": dep_map.get(x["_id"], {}).get("name", "Unassigned"), "count": x["count"]} for x in breakdown])


@router.get("/departments", response_model=list[Department])
async def list_departments(wingman_session: str | None = Cookie(default=None)):
    user = await current_user(wingman_session)
    scopes = await scoped_department_ids(user)
    query = {} if scopes is None else {"id": {"$in": scopes}}
    result = []
    async for d in db.departments.find(query).sort("name", 1):
        result.append(Department(id=d["id"], name=d["name"], description=d.get("description", ""),
                                 record_count=await db.records.count_documents({"department_id": d["id"]}),
                                 user_count=await db.users.count_documents({"department_ids": d["id"], "status": "active"}), created_at=d["created_at"]))
    return result


@router.post("/departments", response_model=Department)
async def create_department(payload: DepartmentCreate, wingman_session: str | None = Cookie(default=None)):
    user = await current_user(wingman_session); require_owner(user)
    if await db.departments.find_one({"name": {"$regex": f"^{re.escape(payload.name.strip())}$", "$options": "i"}}):
        raise HTTPException(status_code=409, detail="A department with this name already exists")
    d = {"id": str(uuid.uuid4()), "name": payload.name.strip(), "description": payload.description.strip(), "created_at": datetime.now(timezone.utc)}
    await db.departments.insert_one(d)
    return Department(**d)


@router.post("/departments/bulk-delete", response_model=ActionResponse)
async def delete_departments(ids: list[str], wingman_session: str | None = Cookie(default=None)):
    user = await current_user(wingman_session); require_owner(user)
    await db.records.delete_many({"department_id": {"$in": ids}}); result = await db.departments.delete_many({"id": {"$in": ids}})
    await db.users.update_many({}, {"$pull": {"department_ids": {"$in": ids}}})
    return ActionResponse(message="Departments deleted", affected=result.deleted_count)


@router.get("/files", response_model=list[FileAsset])
async def list_files(wingman_session: str | None = Cookie(default=None)):
    user = await current_user(wingman_session); scopes = await scoped_department_ids(user); query = {} if scopes is None else {"department_id": {"$in": scopes}}
    dep_map = await department_map(); return [_file(f, dep_map) for f in await db.files.find(query).sort("uploaded_at", -1).to_list(200)]


async def save_upload(upload: UploadFile, department_id: str, user: dict) -> FileUploadResponse:
    if not upload.filename or not upload.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV files are supported")
    content = await upload.read()
    if len(content) > 15 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="CSV must be smaller than 15 MB")
    try:
        text = content.decode("utf-8-sig")
        rows = list(csv.DictReader(io.StringIO(text)))
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Could not parse CSV: {exc}") from exc
    if not rows or not rows[0]:
        raise HTTPException(status_code=400, detail="CSV must include a header row and at least one record")
    file_id = str(uuid.uuid4()); now = datetime.now(timezone.utc)
    existing = await db.records.find({"department_id": department_id}, {"fingerprint": 1}).to_list(100000)
    fingerprints = {x.get("fingerprint") for x in existing}
    docs = []
    for row in rows:
        data = {str(k).strip(): str(v or "").strip() for k, v in row.items() if k}
        fingerprint = hashlib.sha256("|".join(data.values()).lower().encode()).hexdigest()
        if fingerprint in fingerprints: continue
        fingerprints.add(fingerprint)
        docs.append({"id": str(uuid.uuid4()), "file_id": file_id, "department_id": department_id, "data": data,
                     "search_text": " ".join(data.values()).lower(), "fingerprint": fingerprint, "created_at": now})
    if docs: await db.records.insert_many(docs)
    f = {"id": file_id, "name": upload.filename, "department_id": department_id, "size_bytes": len(content), "row_count": len(rows),
         "inserted_count": len(docs), "skipped_count": len(rows) - len(docs), "uploaded_by": user["email"], "uploaded_at": now,
         "content_b64": base64.b64encode(content).decode()}
    await db.files.insert_one(f); dep_map = await department_map()
    return FileUploadResponse(file=_file(f, dep_map), message=f"{len(docs)} records added; {len(rows)-len(docs)} duplicates skipped")


@router.post("/files/upload", response_model=FileUploadResponse)
async def upload_file(file: UploadFile = File(...), department_id: str = Form(...), wingman_session: str | None = Cookie(default=None)):
    user = await current_user(wingman_session); scopes = await scoped_department_ids(user)
    if scopes is not None and department_id not in scopes: raise HTTPException(status_code=403, detail="You do not have access to this department")
    return await save_upload(file, department_id, user)


@router.post("/files/{file_id}/reupload", response_model=FileUploadResponse)
async def reupload_file(file_id: str, file: UploadFile = File(...), wingman_session: str | None = Cookie(default=None)):
    user = await current_user(wingman_session); old = await db.files.find_one({"id": file_id})
    if not old: raise HTTPException(status_code=404, detail="File not found")
    await db.records.delete_many({"file_id": file_id}); await db.files.delete_one({"id": file_id})
    return await save_upload(file, old["department_id"], user)


@router.get("/files/{file_id}/download")
async def download_file(file_id: str, wingman_session: str | None = Cookie(default=None)):
    user = await current_user(wingman_session); f = await db.files.find_one({"id": file_id})
    if not f: raise HTTPException(status_code=404, detail="File not found")
    scopes = await scoped_department_ids(user)
    if scopes is not None and f["department_id"] not in scopes: raise HTTPException(status_code=403, detail="You do not have access to this file")
    return Response(content=base64.b64decode(f["content_b64"]), media_type="text/csv", headers={"Content-Disposition": f'attachment; filename="{f["name"]}"'})


@router.delete("/files/{file_id}", response_model=ActionResponse)
async def delete_file(file_id: str, wingman_session: str | None = Cookie(default=None)):
    user = await current_user(wingman_session); require_owner(user)
    result = await db.files.delete_one({"id": file_id}); await db.records.delete_many({"file_id": file_id})
    if not result.deleted_count: raise HTTPException(status_code=404, detail="File not found")
    return ActionResponse(message="File and its records deleted", affected=1)


@router.get("/search", response_model=RecordSearchResponse)
async def search_records(q: str = "", department_id: str = "", page: int = 1, page_size: int = 25, wingman_session: str | None = Cookie(default=None)):
    user = await current_user(wingman_session); scopes = await scoped_department_ids(user); query: dict = {}
    allowed = scopes if not department_id else [department_id]
    if scopes is not None and department_id and department_id not in scopes: return RecordSearchResponse(items=[], total=0, page=page, page_size=page_size)
    if allowed is not None: query["department_id"] = {"$in": allowed}
    if q.strip(): query["search_text"] = {"$regex": re.escape(q.strip().lower()), "$options": "i"}
    page = max(1, page); page_size = min(100, max(1, page_size)); total = await db.records.count_documents(query); docs = await db.records.find(query).sort("created_at", -1).skip((page-1)*page_size).limit(page_size).to_list(page_size)
    dep_map = await department_map(); return RecordSearchResponse(items=[await _record(x, dep_map) for x in docs], total=total, page=page, page_size=page_size, fields=sorted({k for x in docs for k in x.get("data", {})}))


@router.post("/search/bulk", response_model=BulkLookupResponse)
async def bulk_lookup(payload: BulkLookupRequest, wingman_session: str | None = Cookie(default=None)):
    user = await current_user(wingman_session); scopes = await scoped_department_ids(user); values = list(dict.fromkeys([x.strip().lower() for x in payload.query.splitlines() if x.strip()]))[:500]
    allowed = scopes if not payload.department_id else [payload.department_id]
    query: dict = {"search_text": {"$regex": "|".join(re.escape(v) for v in values), "$options": "i"}} if values else {"id": "never"}
    if allowed is not None: query["department_id"] = {"$in": allowed}
    docs = await db.records.find(query).limit(500).to_list(500); dep_map = await department_map(); matched = {v for v in values if any(v in x.get("search_text", "") for x in docs)}
    return BulkLookupResponse(items=[await _record(x, dep_map) for x in docs], total_queries=len(values), matched_queries=len(matched))


@router.post("/search/bulk-delete", response_model=ActionResponse)
async def bulk_delete_records(ids: list[str], wingman_session: str | None = Cookie(default=None)):
    user = await current_user(wingman_session)
    if user["role"] not in ("owner", "admin"): raise HTTPException(status_code=403, detail="Admin permission required")
    scopes = await scoped_department_ids(user); query = {"id": {"$in": ids}} if scopes is None else {"id": {"$in": ids}, "department_id": {"$in": scopes}}
    result = await db.records.delete_many(query); return ActionResponse(message="Selected records deleted", affected=result.deleted_count)


@router.get("/users", response_model=list[UserPublic])
async def list_users(wingman_session: str | None = Cookie(default=None)):
    user = await current_user(wingman_session); require_owner(user)
    return [_public(x) async for x in db.users.find({}).sort("created_at", -1)]


@router.post("/users", response_model=UserPublic)
async def create_user(payload: UserCreate, wingman_session: str | None = Cookie(default=None)):
    owner = await current_user(wingman_session); require_owner(owner); email = payload.email.strip().lower()
    if await db.users.find_one({"email": email}): raise HTTPException(status_code=409, detail="An account with this email already exists")
    d = {"id": str(uuid.uuid4()), "name": payload.name.strip(), "email": email, "password_hash": _hash_password(payload.password), "role": payload.role, "status": "active", "department_ids": payload.department_ids, "created_at": datetime.now(timezone.utc)}
    await db.users.insert_one(d); return _public(d)


@router.patch("/users/{user_id}", response_model=UserPublic)
async def update_user(user_id: str, payload: UserUpdate, wingman_session: str | None = Cookie(default=None)):
    owner = await current_user(wingman_session); require_owner(owner); updates = payload.model_dump(exclude_none=True)
    if not updates: raise HTTPException(status_code=400, detail="No changes supplied")
    await db.users.update_one({"id": user_id, "role": {"$ne": "owner"}}, {"$set": updates}); d = await db.users.find_one({"id": user_id})
    if not d: raise HTTPException(status_code=404, detail="User not found")
    return _public(d)


@router.delete("/users/{user_id}", response_model=ActionResponse)
async def delete_user(user_id: str, wingman_session: str | None = Cookie(default=None)):
    owner = await current_user(wingman_session); require_owner(owner); result = await db.users.delete_one({"id": user_id, "role": {"$ne": "owner"}})
    if not result.deleted_count: raise HTTPException(status_code=400, detail="Owner account cannot be deleted")
    return ActionResponse(message="User account deleted", affected=1)


@router.post("/users/bulk-access", response_model=ActionResponse)
async def bulk_access(payload: BulkAccessRequest, wingman_session: str | None = Cookie(default=None)):
    owner = await current_user(wingman_session); require_owner(owner); update = {"$set": {"department_ids": payload.department_ids}}
    if payload.mode == "grant": update = {"$addToSet": {"department_ids": {"$each": payload.department_ids}}}
    if payload.mode == "revoke": update = {"$pull": {"department_ids": {"$in": payload.department_ids}}}
    result = await db.users.update_many({"id": {"$in": payload.user_ids}, "role": {"$ne": "owner"}}, update)
    return ActionResponse(message="Department access updated", affected=result.modified_count)


@router.get("/admin/approvals", response_model=list[ApprovalSummary])
async def approvals(wingman_session: str | None = Cookie(default=None)):
    user = await current_user(wingman_session)
    if user["role"] not in ("owner", "admin"): raise HTTPException(status_code=403, detail="Admin permission required")
    return [ApprovalSummary(id=x["id"], name=x["name"], email=x["email"], created_at=x["created_at"]) async for x in db.users.find({"status": "pending"}).sort("created_at", -1)]


@router.post("/admin/approvals/{user_id}", response_model=ActionResponse)
async def act_approval(user_id: str, payload: ApprovalAction, wingman_session: str | None = Cookie(default=None)):
    actor = await current_user(wingman_session)
    if actor["role"] not in ("owner", "admin"): raise HTTPException(status_code=403, detail="Admin permission required")
    target = await db.users.find_one({"id": user_id, "status": "pending"})
    if not target: raise HTTPException(status_code=404, detail="Pending request not found")
    if payload.action == "approve":
        await db.users.update_one({"id": user_id}, {"$set": {"status": "active", "department_ids": actor.get("department_ids", []), "role": "user"}})
        return ActionResponse(message="User request approved")
    await db.users.delete_one({"id": user_id}); return ActionResponse(message="User request declined")
