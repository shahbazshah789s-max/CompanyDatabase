"""Shared Mongo handle — import `client`/`db` from here (server.py, routers, seed.py)."""

import logging
import os
from pathlib import Path

from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import ASCENDING, DESCENDING, IndexModel

load_dotenv(Path(__file__).parent.parent / ".env")

mongo_url = os.environ["MONGO_URL"]
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ["DB_NAME"]]

logger = logging.getLogger(__name__)

# One entry per collection: every field a route filters, sorts, or dedupes on. Applied by ensure_indexes() at startup.
INDEXES: dict[str, list[IndexModel]] = {
    "status_checks": [IndexModel([("timestamp", DESCENDING)], name="timestamp_desc")],
    "users": [IndexModel([("id", ASCENDING)], name="user_id", unique=True), IndexModel([("email", ASCENDING)], name="user_email", unique=True), IndexModel([("status", ASCENDING)], name="user_status"), IndexModel([("department_ids", ASCENDING), ("role", ASCENDING)], name="user_scope_role")],
    "sessions": [IndexModel([("token", ASCENDING)], name="session_token", unique=True), IndexModel([("expires_at", ASCENDING)], name="session_expiry", expireAfterSeconds=0)],
    "password_tokens": [IndexModel([("token", ASCENDING)], name="reset_token", unique=True), IndexModel([("expires_at", ASCENDING)], name="reset_expiry", expireAfterSeconds=0)],
    "departments": [IndexModel([("id", ASCENDING)], name="department_id", unique=True), IndexModel([("name", ASCENDING)], name="department_name", unique=True), IndexModel([("created_by", ASCENDING)], name="department_creator")],
    "files": [IndexModel([("id", ASCENDING)], name="file_id", unique=True), IndexModel([("uploaded_at", DESCENDING)], name="file_uploaded")],
    "upload_sessions": [IndexModel([("id", ASCENDING)], name="upload_session_id", unique=True), IndexModel([("user_id", ASCENDING), ("created_at", DESCENDING)], name="upload_session_owner")],
    "branding": [IndexModel([("id", ASCENDING)], name="branding_id", unique=True)],
    "records": [IndexModel([("search_text", ASCENDING)], name="record_search"), IndexModel([("department_id", ASCENDING), ("created_at", DESCENDING)], name="record_scope"), IndexModel([("file_id", ASCENDING)], name="record_file"), IndexModel([("fingerprint", ASCENDING)], name="record_fingerprint")],
}


async def ensure_indexes() -> None:
    for collection, models in INDEXES.items():
        for model in models:  # one at a time so a bad spec skips only itself
            try:
                await db[collection].create_indexes([model])
            except Exception as exc:  # never block boot on an index; the log line names what to fix
                logger.error("ensure_indexes(%s.%s): %s", collection, model.document["name"], exc)
