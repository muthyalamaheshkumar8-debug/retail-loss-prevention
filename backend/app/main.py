from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from collections import Counter
from io import BytesIO, StringIO
import csv
import json
import logging
import re
import shutil
from xml.sax.saxutils import escape
from fastapi import (
    FastAPI,
    Depends,
    HTTPException,
    Request,
    Response,
    UploadFile,
    File,
    Form,
    Query,
)
from fastapi.responses import FileResponse, StreamingResponse, JSONResponse
from pymongo.errors import PyMongoError, DuplicateKeyError
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from .config import settings
from .database import db, initialize
from .security import current_user, admin, password_hash, token, throttle, DUMMY_HASH
from .models import (
    Login,
    UserCreate,
    StoreCreate,
    ProcessRequest,
    IncidentCreate,
    Review,
    Assignment,
)
from .common import public, required, now, uid, audit, incident_access, incident_scope
from .media import probe

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("api")


@asynccontextmanager
async def lifespan(app):
    if len(settings.jwt_secret) < 32 or settings.jwt_secret.startswith("replace-"):
        raise RuntimeError("Set JWT_SECRET to at least 32 random characters in .env")
    if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
        raise RuntimeError(
            "FFmpeg and ffprobe are required. Use Docker Compose or install FFmpeg."
        )
    initialize()
    for folder in ["videos", "evidence"]:
        (settings.data_dir / folder).mkdir(parents=True, exist_ok=True)
    if db.users.count_documents({}) == 0:
        if len(settings.admin_password) < 12 or settings.admin_password.startswith(
            "replace-"
        ):
            raise RuntimeError(
                "Set ADMIN_PASSWORD to a strong password of at least 12 characters"
            )
        db.users.insert_one(
            {
                "_id": uid("USR"),
                "name": "Administrator",
                "email": settings.admin_email.lower(),
                "role": "admin",
                "password_hash": password_hash.hash(settings.admin_password),
                "disabled": False,
                "created_at": now(),
            }
        )
    yield


app = FastAPI(
    title="Retail Review API",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
    redoc_url=None,
)


@app.middleware("http")
async def security_headers(request, call_next):
    if request.method in {"POST", "PATCH", "PUT", "DELETE"}:
        origin = request.headers.get("origin")
        if origin and origin != settings.app_origin:
            return JSONResponse({"detail": "Origin not allowed"}, status_code=403)
        if request.headers.get("sec-fetch-site") == "cross-site":
            return JSONResponse(
                {"detail": "Cross-site request blocked"}, status_code=403
            )
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Cache-Control"] = "no-store"
    return response


@app.exception_handler(PyMongoError)
async def db_error(request, exc):
    log.error("Database operation failed: %s", type(exc).__name__)
    return JSONResponse({"detail": "Database temporarily unavailable"}, status_code=503)


@app.get("/api/health")
def health():
    db.command("ping")
    return {"status": "ok"}


@app.post("/api/auth/login")
def login(body: Login, request: Request, response: Response):
    throttle(request.client.host if request.client else "unknown")
    user = db.users.find_one({"email": body.email.lower()})
    valid = password_hash.verify(
        body.password, user["password_hash"] if user else DUMMY_HASH
    )
    if not user or not valid or user.get("disabled"):
        raise HTTPException(401, "Invalid email or password")
    response.set_cookie(
        "session",
        token(user["_id"]),
        max_age=28800,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="strict",
        path="/",
    )
    return public(user)


@app.post("/api/auth/logout")
def logout(response: Response):
    response.delete_cookie("session", path="/")
    return {"ok": True}


@app.get("/api/auth/me")
def me(user=Depends(current_user)):
    return public(user)


@app.get("/api/users")
def users(user=Depends(admin)):
    return [public(u) for u in db.users.find().sort("created_at", -1).limit(200)]


@app.post("/api/users", status_code=201)
def add_user(body: UserCreate, user=Depends(admin)):
    doc = {
        "_id": uid("USR"),
        "name": body.name,
        "email": body.email.lower(),
        "role": body.role,
        "password_hash": password_hash.hash(body.password),
        "disabled": False,
        "created_at": now(),
    }
    try:
        db.users.insert_one(doc)
    except DuplicateKeyError:
        raise HTTPException(409, "Email already exists")
    audit(doc["_id"], user["_id"], "user_created")
    return public(doc)


@app.patch("/api/users/{id}/disabled")
def disable_user(id: str, disabled: bool, user=Depends(admin)):
    if id == user["_id"]:
        raise HTTPException(400, "You cannot disable yourself")
    required("users", id)
    db.users.update_one({"_id": id}, {"$set": {"disabled": disabled}})
    audit(id, user["_id"], "user_disabled" if disabled else "user_enabled")
    return {"ok": True}


@app.get("/api/stores")
def stores(user=Depends(current_user)):
    return [public(s) for s in db.stores.find().sort("name", 1).limit(200)]


@app.post("/api/stores", status_code=201)
def add_store(body: StoreCreate, user=Depends(admin)):
    doc = {"_id": uid("STR"), **body.model_dump(), "created_at": now()}
    db.stores.insert_one(doc)
    audit(doc["_id"], user["_id"], "store_created")
    return public(doc)


@app.put("/api/stores/{id}")
def update_store(id: str, body: StoreCreate, user=Depends(admin)):
    required("stores", id)
    db.stores.update_one({"_id": id}, {"$set": body.model_dump()})
    audit(id, user["_id"], "store_updated")
    return public(required("stores", id))


@app.post("/api/videos/upload", status_code=201)
def upload(
    file: UploadFile = File(...),
    store_id: str = Form(...),
    camera_id: str = Form(...),
    user=Depends(current_user),
):
    store = required("stores", store_id)
    if camera_id not in store["cameras"]:
        raise HTTPException(422, "Choose a camera belonging to this store")
    name = Path((file.filename or "").replace("\\", "/")).name
    extension = Path(name).suffix.lower()
    if extension not in {".mp4", ".mov", ".avi", ".mkv"}:
        raise HTTPException(415, "Supported formats: MP4, MOV, AVI, MKV")
    vid = uid("VID")
    dest = settings.data_dir / "videos" / (vid + extension)
    size = 0
    try:
        with dest.open("wb") as output:
            while chunk := file.file.read(1024 * 1024):
                size += len(chunk)
                if size > settings.max_upload_bytes:
                    raise HTTPException(413, "Maximum video size is 500 MB")
                output.write(chunk)
        try:
            metadata = probe(dest)
        except (ValueError, RuntimeError) as exc:
            raise HTTPException(422, str(exc))
        doc = {
            "_id": vid,
            "filename": name[:200],
            "store_id": store_id,
            "camera_id": camera_id,
            "source_path": str(dest),
            "size": size,
            **metadata,
            "status": "UPLOADED",
            "progress": 0,
            "zones": [],
            "uploaded_at": now(),
            "uploaded_by": user["_id"],
        }
        db.videos.insert_one(doc)
    except Exception:
        dest.unlink(missing_ok=True)
        raise
    finally:
        file.file.close()
    audit(vid, user["_id"], "video_uploaded")
    return public(doc)


@app.get("/api/videos")
def videos(page: int = Query(1, ge=1), user=Depends(current_user)):
    return {
        "items": [
            public(v)
            for v in db.videos.find()
            .sort("uploaded_at", -1)
            .skip((page - 1) * 24)
            .limit(24)
        ],
        "total": db.videos.count_documents({}),
        "page": page,
    }


@app.get("/api/videos/{id}")
def video_detail(id: str, user=Depends(current_user)):
    video = required("videos", id)
    return {
        **public(video),
        "has_playback": bool(video.get("playback_path")),
        "has_overlay": bool(video.get("overlay_path")),
    }


@app.post("/api/videos/{id}/process", status_code=202)
def start_processing(id: str, body: ProcessRequest, user=Depends(current_user)):
    video = required("videos", id)
    if body.detect and not settings.cv_enabled:
        raise HTTPException(422, "Tracking is disabled on this server")
    names = set()
    for z in body.zones:
        if z.x1 >= z.x2 or z.y1 >= z.y2 or z.name in names:
            raise HTTPException(
                422, "Zones need unique names and positive width and height"
            )
        names.add(z.name)
    if video["status"] == "COMPLETED":
        raise HTTPException(
            409,
            "Completed videos are immutable. Upload again to analyze different zones.",
        )
    changed = db.videos.update_one(
        {"_id": id, "status": {"$in": ["UPLOADED", "FAILED"]}},
        {
            "$set": {
                "status": "QUEUED",
                "zones": [z.model_dump() for z in body.zones],
                "detect": body.detect,
                "progress": 0,
                "error": None,
            }
        },
    )
    if not changed.modified_count:
        raise HTTPException(409, "Video already processing")
    audit(id, user["_id"], "processing_queued")
    return {"status": "QUEUED"}


@app.get("/api/videos/{id}/events")
def events(id: str, page: int = Query(1, ge=1), user=Depends(current_user)):
    required("videos", id)
    query = {"video_id": id}
    return {
        "items": [
            public(v)
            for v in db.events.find(query)
            .sort("timestamp", 1)
            .skip((page - 1) * 100)
            .limit(100)
        ],
        "total": db.events.count_documents(query),
        "page": page,
    }


@app.get("/api/videos/{id}/media")
def video_media(id: str, variant: str = "playback", user=Depends(current_user)):
    video = required("videos", id)
    fields = {
        "original": "source_path",
        "playback": "playback_path",
        "overlay": "overlay_path",
    }
    if variant not in fields:
        raise HTTPException(422, "Invalid media variant")
    path = video.get(fields[variant])
    if not path or not Path(path).is_file():
        raise HTTPException(404, "Video media not ready")
    return FileResponse(path, media_type="video/mp4" if variant != "original" else None)


@app.post("/api/incidents", status_code=201)
def create_incident(body: IncidentCreate, user=Depends(current_user)):
    video = required("videos", body.video_id)
    if video["status"] != "COMPLETED":
        raise HTTPException(409, "Complete video processing first")
    if body.timestamp >= video["duration"]:
        raise HTTPException(422, "Timestamp must be within the video")
    if body.event_id:
        event = required("events", body.event_id)
        if event["video_id"] != body.video_id:
            raise HTTPException(422, "Event must belong to this video")
    incident = {
        "_id": uid("INC"),
        **body.model_dump(),
        "store_id": video["store_id"],
        "camera_id": video["camera_id"],
        "status": "NEEDS_REVIEW",
        "created_by": user["_id"],
        "reviewer_id": user["_id"],
        "created_at": now(),
        "version": 0,
        "evidence_status": "queued",
        "history": [
            {
                "action": "created",
                "actor": user["_id"],
                "at": now(),
                "notes": body.notes,
            }
        ],
    }
    db.incidents.insert_one(incident)
    audit(incident["_id"], user["_id"], "incident_created_by_human")
    return public(incident)


def filtered_incidents(
    user,
    search="",
    status="",
    category="",
    store_id="",
    camera_id="",
    date="",
    reviewer_id="",
):
    query = incident_scope(user)
    for key, value in [
        ("status", status),
        ("category", category),
        ("store_id", store_id),
        ("camera_id", camera_id),
        ("reviewer_id", reviewer_id),
    ]:
        if value:
            query[key] = value
    if date:
        try:
            datetime.strptime(date, "%Y-%m-%d")
        except ValueError:
            raise HTTPException(422, "Date must be YYYY-MM-DD")
        query["created_at"] = {"$regex": "^" + date}
    if search:
        query["$and"] = [
            {
                "$or": [
                    {k: {"$regex": re.escape(search[:100]), "$options": "i"}}
                    for k in ["_id", "notes", "camera_id", "store_id"]
                ]
            }
        ]
    return query


@app.get("/api/incidents")
def incidents(
    search: str = "",
    status: str = "",
    category: str = "",
    store_id: str = "",
    camera_id: str = "",
    date: str = "",
    reviewer_id: str = "",
    page: int = Query(1, ge=1),
    user=Depends(current_user),
):
    q = filtered_incidents(
        user, search, status, category, store_id, camera_id, date, reviewer_id
    )
    return {
        "items": [
            public(i)
            for i in db.incidents.find(q, {"history": 0})
            .sort("created_at", -1)
            .skip((page - 1) * 25)
            .limit(25)
        ],
        "total": db.incidents.count_documents(q),
        "page": page,
    }


@app.get("/api/incidents/{id}")
def incident_detail(id: str, user=Depends(current_user)):
    incident = incident_access(id, user)
    return {
        **public(incident),
        "video": public(required("videos", incident["video_id"])),
    }


@app.post("/api/incidents/{id}/opened")
def opened(id: str, user=Depends(current_user)):
    incident_access(id, user)
    audit(id, user["_id"], "incident_opened")
    return {"ok": True}


@app.patch("/api/incidents/{id}")
@app.post("/api/incidents/{id}/review")
def review(id: str, body: Review, user=Depends(current_user)):
    incident = incident_access(id, user)
    at = now()
    entry = {
        "action": "review",
        "status": body.status,
        "notes": body.notes,
        "actor": user["_id"],
        "at": at,
    }
    values = {
        "status": body.status,
        "notes": body.notes,
        "reviewed_by": user["_id"],
        "reviewed_at": at,
    }
    if not incident.get("first_reviewed_at"):
        values["first_reviewed_at"] = at
    # Atomic version check and embedded history keep the decision and its audit together.
    result = db.incidents.update_one(
        {"_id": id, "version": body.version},
        {"$set": values, "$inc": {"version": 1}, "$push": {"history": entry}},
    )
    if not result.modified_count:
        raise HTTPException(
            409, "Another reviewer updated this incident. Reload before saving."
        )
    audit(id, user["_id"], "review_submitted", body.status)
    return public(required("incidents", id))


@app.patch("/api/incidents/{id}/assignment")
def assignment(id: str, body: Assignment, user=Depends(admin)):
    required("incidents", id)
    if body.reviewer_id:
        reviewer = required("users", body.reviewer_id)
        if reviewer.get("disabled"):
            raise HTTPException(422, "Cannot assign a disabled user")
    result = db.incidents.update_one(
        {"_id": id, "version": body.version},
        {
            "$set": {"reviewer_id": body.reviewer_id},
            "$inc": {"version": 1},
            "$push": {
                "history": {
                    "action": "assigned",
                    "actor": user["_id"],
                    "at": now(),
                    "notes": body.reviewer_id or "Unassigned",
                }
            },
        },
    )
    if not result.modified_count:
        raise HTTPException(409, "Incident changed; reload")
    return public(required("incidents", id))


@app.get("/api/incidents/{id}/audit")
def history(id: str, user=Depends(current_user)):
    incident = incident_access(id, user)
    return {
        "history": incident["history"],
        "access_log": [
            public(v)
            for v in db.audit.find({"target_id": id}).sort("at", -1).limit(100)
        ],
    }


@app.post("/api/incidents/{id}/evidence/retry")
def retry_evidence(id: str, user=Depends(current_user)):
    incident_access(id, user)
    result = db.incidents.update_one(
        {"_id": id, "evidence_status": "failed"},
        {"$set": {"evidence_status": "queued", "evidence_error": None}},
    )
    if not result.modified_count:
        raise HTTPException(409, "Only failed evidence can be retried")
    return {"ok": True}


@app.get("/api/incidents/{id}/evidence/{kind}")
def evidence_media(id: str, kind: str, user=Depends(current_user)):
    incident = incident_access(id, user)
    extension = {"clip": ".mp4", "thumbnail": ".jpg"}.get(kind)
    if not extension:
        raise HTTPException(404, "Unknown evidence format")
    path = settings.data_dir / "evidence" / (incident["_id"] + extension)
    if incident["evidence_status"] != "ready" or not path.is_file():
        raise HTTPException(404, "Evidence not ready")
    return FileResponse(
        path, media_type="video/mp4" if kind == "clip" else "image/jpeg"
    )


@app.get("/api/investigations")
def investigations(user=Depends(current_user)):
    docs = (
        db.incidents.find({**incident_scope(user), "reviewed_at": {"$exists": True}})
        .sort("reviewed_at", -1)
        .limit(100)
    )
    return [public(d) for d in docs]


@app.get("/api/analytics/summary")
def analytics(user=Depends(current_user)):
    items = list(db.incidents.find(incident_scope(user), {"history": 0}))
    outcomes = Counter(i["status"] for i in items)
    resolved = sum(outcomes[k] for k in ["NOT_AN_INCIDENT", "ESCALATED", "CLOSED"])
    waits = [
        (
            datetime.fromisoformat(i["first_reviewed_at"])
            - datetime.fromisoformat(i["created_at"])
        ).total_seconds()
        / 60
        for i in items
        if i.get("first_reviewed_at")
    ]

    def grouped(key):
        return [
            {"name": k, "count": v}
            for k, v in sorted(Counter(i.get(key, "Unknown") for i in items).items())
        ]

    return {
        "videos": db.videos.count_documents({}),
        "processed": db.videos.count_documents({"status": "COMPLETED"}),
        "events": db.events.count_documents({}),
        "incidents": len(items),
        "reviewed": sum(bool(i.get("reviewed_at")) for i in items),
        "resolved": resolved,
        "escalated": outcomes["ESCALATED"],
        "resolution_rate": round(resolved / len(items) * 100, 1) if items else 0,
        "average_first_review_minutes": (
            round(sum(waits) / len(waits), 1) if waits else None
        ),
        "categories": grouped("category"),
        "stores": grouped("store_id"),
        "outcomes": grouped("status"),
        "days": [
            {"name": k, "count": v}
            for k, v in sorted(Counter(i["created_at"][:10] for i in items).items())
        ],
        "scope": "assigned_or_created" if user["role"] == "investigator" else "all",
    }


@app.get("/api/reports/incidents.csv")
def export_csv(user=Depends(current_user)):
    fields = [
        "id",
        "video_id",
        "store_id",
        "camera_id",
        "timestamp",
        "category",
        "priority",
        "status",
        "created_at",
        "reviewed_at",
        "reviewed_by",
        "notes",
    ]

    def generate():
        buf = StringIO()
        writer = csv.DictWriter(buf, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        yield buf.getvalue()
        for item in db.incidents.find(incident_scope(user)):
            buf.seek(0)
            buf.truncate(0)
            # Prevent formula execution when opening CSV in spreadsheet tools.
            safe = {
                k: (
                    "'" + v
                    if isinstance(v, str)
                    and v.startswith(("=", "+", "-", "@", "\t", "\r"))
                    else v
                )
                for k, v in public(item).items()
            }
            writer.writerow(safe)
            yield buf.getvalue()

    return StreamingResponse(
        generate(),
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="incidents.csv"'},
    )


@app.get("/api/incidents/{id}/report")
def report(id: str, format: str = "json", user=Depends(current_user)):
    incident = incident_access(id, user)
    doc = public(incident)
    doc["evidence_url"] = f"/api/incidents/{id}/evidence/clip"
    doc["statement"] = (
        "Human-authored review record. Automated zone observations do not establish wrongdoing."
    )
    if format == "json":
        return Response(
            json.dumps(doc, indent=2),
            media_type="application/json",
            headers={"Content-Disposition": f'attachment; filename="{id}.json"'},
        )
    if format != "pdf":
        raise HTTPException(422, "Choose json or pdf")
    buffer = BytesIO()
    styles = getSampleStyleSheet()
    flow = [
        Paragraph("Retail Review · Investigation Report", styles["Title"]),
        Spacer(1, 18),
    ]
    for key in [
        "id",
        "store_id",
        "camera_id",
        "timestamp",
        "category",
        "priority",
        "status",
        "created_at",
        "reviewed_at",
        "notes",
        "evidence_url",
        "statement",
    ]:
        flow += [
            Paragraph(
                f'<b>{escape(key.replace("_", " ").title())}</b>', styles["Heading3"]
            ),
            Paragraph(
                escape(str(doc.get(key, "—"))).replace("\n", "<br/>"),
                styles["BodyText"],
            ),
        ]
    flow += [Spacer(1, 16), Paragraph("Review history", styles["Heading2"])]
    for entry in doc["history"]:
        flow.append(
            Paragraph(
                escape(
                    f'{entry["at"]} | {entry["actor"]} | {entry["action"]}: {entry.get("status", "")} {entry.get("notes", "")}'
                ),
                styles["BodyText"],
            )
        )
        flow.append(Spacer(1, 8))
    SimpleDocTemplate(buffer).build(flow)
    return Response(
        buffer.getvalue(),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{id}.pdf"'},
    )


@app.get("/api/settings")
def system_settings(user=Depends(current_user)):
    return {
        "cv_enabled": settings.cv_enabled,
        "model": Path(settings.yolo_model).name,
        "max_upload_mb": 500,
        "max_duration_minutes": settings.max_duration // 60,
        "tracking": "ByteTrack; IDs reset per video",
        "event_limit_per_video": 10000,
    }
