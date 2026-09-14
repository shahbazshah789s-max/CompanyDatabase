import hashlib
import secrets
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Cookie, HTTPException, Response

from lib.db import db
from models.portal import (
    ActionResponse,
    AuthResponse,
    ForgotPasswordRequest,
    LoginRequest,
    PasswordChangeRequest,
    ResetPasswordRequest,
    SignupRequest,
    UserPublic,
)

router = APIRouter(prefix="/auth", tags=["auth"])
SESSION_COOKIE = "wingman_session"


def _hash_password(password: str, salt: str | None = None) -> str:
    salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 120_000).hex()
    return f"{salt}${digest}"


def _verify_password(password: str, stored: str) -> bool:
    try:
        salt, digest = stored.split("$", 1)
    except ValueError:
        return False
    check = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 120_000).hex()
    return secrets.compare_digest(check, digest)


def _utc(value: datetime) -> datetime:
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value


def _public(doc: dict) -> UserPublic:
    return UserPublic(
        id=doc["id"], name=doc["name"], email=doc["email"], role=doc["role"],
        status=doc["status"], department_ids=doc.get("department_ids", []),
        created_at=doc["created_at"], last_login=doc.get("last_login"),
    )


async def ensure_demo_owner() -> None:
    email = "shahbazshah789s@gmail.com"
    now = datetime.now(timezone.utc)
    existing = await db.users.find_one({"email": email})
    if existing:
        if not await db.departments.find_one({}):
            await db.departments.insert_one({"id": str(uuid.uuid4()), "name": "General", "description": "Default workspace scope", "created_at": now})
        return
    await db.users.insert_one({
        "id": str(uuid.uuid4()), "name": "Wingman Owner", "email": email,
        "password_hash": _hash_password("Owner@123456"), "role": "owner",
        "status": "active", "department_ids": [], "created_at": now,
    })
    if not await db.departments.find_one({}):
        await db.departments.insert_one({"id": str(uuid.uuid4()), "name": "General", "description": "Default workspace scope", "created_at": now})


async def current_user(session: str | None) -> dict:
    if not session:
        raise HTTPException(status_code=401, detail="Please sign in to continue")
    record = await db.sessions.find_one({"token": session})
    if not record or _utc(record["expires_at"]) < datetime.now(timezone.utc):
        raise HTTPException(status_code=401, detail="Your session has expired")
    user = await db.users.find_one({"id": record["user_id"]})
    if not user or user.get("status") != "active":
        raise HTTPException(status_code=403, detail="This account is not active")
    return user


def require_owner(user: dict) -> None:
    if user.get("role") != "owner":
        raise HTTPException(status_code=403, detail="Owner permission required")


@router.post("/login", response_model=AuthResponse)
async def login(payload: LoginRequest, response: Response):
    user = await db.users.find_one({"email": payload.email.strip().lower()})
    if not user or not _verify_password(payload.password, user.get("password_hash", "")):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    if user.get("status") != "active":
        raise HTTPException(status_code=403, detail="Your account is waiting for approval or is disabled")
    now = datetime.now(timezone.utc)
    token = secrets.token_urlsafe(32)
    await db.sessions.insert_one({"token": token, "user_id": user["id"], "expires_at": now + timedelta(days=7)})
    await db.users.update_one({"id": user["id"]}, {"$set": {"last_login": now}})
    user["last_login"] = now
    response.set_cookie(SESSION_COOKIE, token, httponly=True, samesite="lax", max_age=604800)
    return AuthResponse(user=_public(user), message="Welcome back to Wingman")


@router.post("/signup", response_model=ActionResponse)
async def signup(payload: SignupRequest):
    email = payload.email.strip().lower()
    if len(payload.password) < 8:
        raise HTTPException(status_code=422, detail="Password must be at least 8 characters")
    if await db.users.find_one({"email": email}):
        raise HTTPException(status_code=409, detail="An account with this email already exists")
    await db.users.insert_one({
        "id": str(uuid.uuid4()), "name": payload.name.strip(), "email": email,
        "password_hash": _hash_password(payload.password), "role": "user", "status": "pending",
        "department_ids": [], "created_at": datetime.now(timezone.utc),
    })
    return ActionResponse(message="Account request submitted. An owner must approve access before you can sign in.")


@router.get("/me", response_model=UserPublic)
async def me(wingman_session: str | None = Cookie(default=None)):
    return _public(await current_user(wingman_session))


@router.post("/logout", response_model=ActionResponse)
async def logout(response: Response, wingman_session: str | None = Cookie(default=None)):
    if wingman_session:
        await db.sessions.delete_one({"token": wingman_session})
    response.delete_cookie(SESSION_COOKIE)
    return ActionResponse(message="Signed out successfully")


@router.post("/change-password", response_model=ActionResponse)
async def change_password(payload: PasswordChangeRequest, wingman_session: str | None = Cookie(default=None)):
    user = await current_user(wingman_session)
    if not _verify_password(payload.current_password, user["password_hash"]):
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    if len(payload.new_password) < 8:
        raise HTTPException(status_code=422, detail="New password must be at least 8 characters")
    await db.users.update_one({"id": user["id"]}, {"$set": {"password_hash": _hash_password(payload.new_password)}})
    return ActionResponse(message="Password updated successfully")


@router.post("/forgot-password")
async def forgot_password(payload: ForgotPasswordRequest):
    user = await db.users.find_one({"email": payload.email.strip().lower()})
    if not user:
        return {"message": "If an account exists, a reset code has been generated.", "reset_token": None}
    token = secrets.token_urlsafe(18)
    await db.password_tokens.insert_one({"token": token, "user_id": user["id"], "expires_at": datetime.now(timezone.utc) + timedelta(minutes=30)})
    return {"message": "Reset code generated for this demo. Use it below to set a new password.", "reset_token": token}


@router.post("/reset-password", response_model=ActionResponse)
async def reset_password(payload: ResetPasswordRequest):
    token = await db.password_tokens.find_one({"token": payload.token})
    if not token or _utc(token["expires_at"]) < datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="Reset code is invalid or expired")
    if len(payload.new_password) < 8:
        raise HTTPException(status_code=422, detail="New password must be at least 8 characters")
    await db.users.update_one({"id": token["user_id"]}, {"$set": {"password_hash": _hash_password(payload.new_password)}})
    await db.password_tokens.delete_one({"_id": token["_id"]})
    return ActionResponse(message="Password reset successfully. You can now sign in.")
