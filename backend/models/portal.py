from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class UserPublic(BaseModel):
    id: str
    name: str
    email: str
    role: Literal["owner", "admin", "user"]
    status: Literal["active", "pending", "disabled"]
    department_ids: list[str] = Field(default_factory=list)
    created_at: datetime
    last_login: datetime | None = None


class AuthResponse(BaseModel):
    user: UserPublic
    message: str


class LoginRequest(BaseModel):
    email: str
    password: str


class SignupRequest(BaseModel):
    name: str
    email: str
    password: str


class PasswordChangeRequest(BaseModel):
    current_password: str
    new_password: str


class ForgotPasswordRequest(BaseModel):
    email: str


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str


class Department(BaseModel):
    id: str
    name: str
    description: str = ""
    record_count: int = 0
    user_count: int = 0
    created_at: datetime


class DepartmentCreate(BaseModel):
    name: str
    description: str = ""


class DashboardStats(BaseModel):
    total_records: int
    active_departments: int
    active_users: int
    pending_requests: int
    recent_files: list["FileAsset"] = Field(default_factory=list)
    department_breakdown: list[dict[str, Any]] = Field(default_factory=list)


class RecordRow(BaseModel):
    id: str
    file_id: str
    file_name: str
    department_id: str
    department_name: str
    data: dict[str, str]
    created_at: datetime


class RecordSearchResponse(BaseModel):
    items: list[RecordRow]
    total: int
    page: int
    page_size: int
    fields: list[str] = Field(default_factory=list)


class BulkLookupRequest(BaseModel):
    query: str
    department_id: str | None = None


class BulkLookupResponse(BaseModel):
    items: list[RecordRow]
    total_queries: int
    matched_queries: int


class FileAsset(BaseModel):
    id: str
    name: str
    department_id: str
    department_name: str
    size_bytes: int
    row_count: int
    inserted_count: int
    skipped_count: int
    uploaded_by: str
    uploaded_at: datetime


class FileUploadResponse(BaseModel):
    file: FileAsset
    message: str


class UploadInitRequest(BaseModel):
    filename: str
    size_bytes: int
    department_id: str
    total_chunks: int
    replace_file_id: str | None = None


class UploadSession(BaseModel):
    id: str
    filename: str
    size_bytes: int
    department_id: str
    total_chunks: int
    uploaded_chunks: int = 0
    status: Literal["uploading", "processing", "complete", "failed"]
    progress: int = 0
    message: str = ""
    file_id: str | None = None


class BrandSettings(BaseModel):
    company_name: str = "Company Database"
    logo_data_url: str | None = None
    nav_labels: dict[str, str] = Field(default_factory=lambda: {
        "dashboard": "Dashboard", "search": "Search", "files": "Files",
        "departments": "Departments", "users": "Users",
    })


class BrandSettingsUpdate(BrandSettings):
    pass


class ActionResponse(BaseModel):
    message: str
    affected: int = 0


class UserCreate(BaseModel):
    name: str
    email: str
    password: str
    role: Literal["admin", "user"] = "user"
    department_ids: list[str] = Field(default_factory=list)


class UserUpdate(BaseModel):
    status: Literal["active", "disabled"] | None = None
    role: Literal["admin", "user"] | None = None
    department_ids: list[str] | None = None


class BulkAccessRequest(BaseModel):
    user_ids: list[str]
    department_ids: list[str]
    mode: Literal["replace", "grant", "revoke"] = "replace"


class ApprovalAction(BaseModel):
    action: Literal["approve", "decline"]


class ApprovalSummary(BaseModel):
    id: str
    name: str
    email: str
    created_at: datetime
