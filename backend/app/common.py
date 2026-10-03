from datetime import datetime, timezone
from uuid import uuid4
from fastapi import HTTPException
from .database import db


def now():
    return datetime.now(timezone.utc).isoformat()


def uid(prefix):
    return f"{prefix}-{uuid4().hex[:16]}"


def public(doc):
    if doc is None:
        return None
    return {
        ("id" if k == "_id" else k): v
        for k, v in doc.items()
        if k not in {"password_hash", "source_path", "playback_path", "overlay_path"}
    }


def required(collection, id):
    doc = db[collection].find_one({"_id": id})
    if not doc:
        raise HTTPException(404, f'{collection.rstrip("s").title()} not found')
    return doc


def incident_access(id, user):
    item = required("incidents", id)
    if (
        user["role"] == "investigator"
        and item.get("reviewer_id") != user["_id"]
        and item.get("created_by") != user["_id"]
    ):
        raise HTTPException(403, "This incident is not assigned to you")
    return item


def incident_scope(user):
    if user["role"] == "investigator":
        return {"$or": [{"reviewer_id": user["_id"]}, {"created_by": user["_id"]}]}
    return {}


def audit(target, actor, action, detail=""):
    db.audit.insert_one(
        {
            "_id": uid("AUD"),
            "target_id": target,
            "actor": actor,
            "action": action,
            "detail": detail,
            "at": now(),
        }
    )
