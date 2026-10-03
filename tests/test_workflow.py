import shutil
import subprocess
import pytest
from app import worker, common
from app.config import settings
from app.vision import ZoneEngine


def new_incident(client):
    return client.post(
        "/api/incidents",
        json={
            "video_id": "VID-ready",
            "timestamp": 15,
            "category": "other",
            "notes": "A human observation",
            "priority": "medium",
        },
    )


def test_auth_and_roles(env):
    db, c, login = env
    assert c.get("/api/videos").status_code == 401
    assert (
        c.post(
            "/api/auth/login",
            json={"email": "admin@example.com", "password": "incorrect"},
        ).status_code
        == 401
    )
    login("reviewer")
    assert (
        c.post("/api/stores", json={"name": "X", "cameras": ["A"]}).status_code == 403
    )
    assert c.get("/api/users").status_code == 403
    login()
    r = c.post(
        "/api/users",
        json={
            "email": "new@example.com",
            "name": "New",
            "role": "investigator",
            "password": "LongTestPassword12",
        },
    )
    assert r.status_code == 201 and "password_hash" not in r.json()
    assert (
        c.post(
            "/api/users",
            json={
                "email": "new@example.com",
                "name": "New",
                "role": "investigator",
                "password": "LongTestPassword12",
            },
        ).status_code
        == 409
    )
    assert c.patch("/api/users/admin/disabled?disabled=true").status_code == 400
    c.patch("/api/users/reviewer/disabled?disabled=true")
    assert (
        c.post(
            "/api/auth/login",
            json={"email": "reviewer@example.com", "password": "TestPassword123!"},
        ).status_code
        == 401
    )
    assert c.post("/api/auth/logout").status_code == 200
    assert c.get("/api/auth/me").status_code == 401


def test_csrf_and_throttle(env):
    _, c, login = env
    assert (
        c.post(
            "/api/auth/login",
            headers={"Origin": "https://evil.example"},
            json={"email": "admin@example.com", "password": "TestPassword123!"},
        ).status_code
        == 403
    )
    for _ in range(10):
        c.post(
            "/api/auth/login", json={"email": "nobody@example.com", "password": "bad"}
        )
    assert (
        c.post(
            "/api/auth/login", json={"email": "nobody@example.com", "password": "bad"}
        ).status_code
        == 429
    )


def test_incident_review_reports_and_access(seeded):
    db, c, login = seeded
    r = new_incident(c)
    assert r.status_code == 201
    item = r.json()
    id = item["id"]
    assert item["evidence_status"] == "queued"
    r = c.post(
        f"/api/incidents/{id}/review",
        json={
            "status": "ESCALATED",
            "notes": "Additional investigation requested",
            "version": 0,
        },
    )
    assert r.status_code == 200 and r.json()["version"] == 1
    assert (
        c.post(
            f"/api/incidents/{id}/review",
            json={"status": "CLOSED", "notes": "stale update", "version": 0},
        ).status_code
        == 409
    )
    assert (
        c.get(f"/api/incidents/{id}/audit").json()["history"][-1]["status"]
        == "ESCALATED"
    )
    stats = c.get("/api/analytics/summary").json()
    assert stats["escalated"] == 1 and stats["resolution_rate"] == 100
    assert stats["average_first_review_minutes"] >= 0
    assert (
        c.get("/api/incidents?status=ESCALATED&search=Additional").json()["total"] == 1
    )
    assert c.get("/api/incidents?date=invalid").status_code == 422
    assert c.get(f"/api/incidents/{id}/report?format=pdf").content.startswith(b"%PDF")
    assert c.get(f"/api/incidents/{id}/report").json()["id"] == id
    assert "Additional investigation" in c.get("/api/reports/incidents.csv").text
    login("other")
    assert c.get("/api/incidents").json()["total"] == 0
    for suffix in ["", "/audit", "/report", "/evidence/clip"]:
        assert c.get(f"/api/incidents/{id}" + suffix).status_code == 403
    assert (
        c.post(
            f"/api/incidents/{id}/review",
            json={"status": "CLOSED", "notes": "unauthorized", "version": 1},
        ).status_code
        == 403
    )
    login()
    assert (
        c.patch(
            f"/api/incidents/{id}/assignment",
            json={"reviewer_id": "other", "version": 1},
        ).status_code
        == 200
    )
    login("other")
    assert c.get(f"/api/incidents/{id}").status_code == 200


def test_timestamp_media_csv_and_input_validation(seeded):
    db, c, _ = seeded
    assert (
        c.post(
            "/api/incidents",
            json={
                "video_id": "VID-ready",
                "timestamp": 30,
                "notes": "Invalid timestamp",
            },
        ).status_code
        == 422
    )
    assert (
        c.post(
            "/api/incidents",
            json={
                "video_id": "VID-ready",
                "timestamp": -1,
                "notes": "Invalid timestamp",
            },
        ).status_code
        == 422
    )
    assert (
        c.post(
            "/api/videos/VID-ready/process", json={"detect": False, "zones": []}
        ).status_code
        == 409
    )
    r = new_incident(c).json()
    db.incidents.update_one({"_id": r["id"]}, {"$set": {"notes": "=SUM(1,1)"}})
    assert "'=SUM" in c.get("/api/reports/incidents.csv").text
    assert c.get("/api/videos/VID-ready/media").status_code == 200
    assert c.get("/api/videos/VID-ready/media?variant=../../etc").status_code == 422
    assert c.get(f'/api/incidents/{r["id"]}/evidence/clip').status_code == 404


def test_zone_engine_neutral_transitions():
    engine = ZoneEngine(
        [{"name": "checkout", "x1": 0.2, "y1": 0.2, "x2": 0.8, "y2": 0.8}]
    )
    assert engine.update(1, 0.1, 0.1, 0) == []
    assert engine.update(1, 0.5, 0.5, 1)[0]["event_type"] == "zone_entered"
    assert engine.update(1, 0.6, 0.6, 2) == []
    assert engine.update(1, 0.9, 0.9, 3)[0]["event_type"] == "zone_left"
    assert engine.update(2, 0.5, 0.5, 4)[0]["track_id"] == "2"


def test_upload_validation(env, monkeypatch):
    db, c, login = env
    login()
    store = c.post("/api/stores", json={"name": "Test", "cameras": ["C1"]}).json()
    fields = {"store_id": store["id"], "camera_id": "C1"}
    assert (
        c.post(
            "/api/videos/upload", data=fields, files={"file": ("x.txt", b"no")}
        ).status_code
        == 415
    )
    monkeypatch.setattr(settings, "max_upload_bytes", 3)
    assert (
        c.post(
            "/api/videos/upload", data=fields, files={"file": ("x.mp4", b"toolarge")}
        ).status_code
        == 413
    )
    assert list((settings.data_dir / "videos").iterdir()) == []


@pytest.mark.skipif(
    not shutil.which("ffmpeg") or not shutil.which("ffprobe"),
    reason="FFmpeg/ffprobe required for real video integration",
)
def test_real_video_upload_worker_clip_and_playback(env, source_video):
    db, c, login = env
    login()
    s = c.post(
        "/api/stores", json={"name": "Staged test", "cameras": ["Camera"]}
    ).json()
    with source_video.open("rb") as f:
        r = c.post(
            "/api/videos/upload",
            data={"store_id": s["id"], "camera_id": "Camera"},
            files={"file": ("staged.avi", f, "video/x-msvideo")},
        )
    assert r.status_code == 201, r.text
    id = r.json()["id"]
    assert 3.9 < r.json()["duration"] < 4.1
    assert (
        c.post(
            f"/api/videos/{id}/process",
            json={
                "detect": False,
                "zones": [{"name": "bad", "x1": 0.8, "y1": 0, "x2": 0.2, "y2": 1}],
            },
        ).status_code
        == 422
    )
    assert (
        c.post(
            f"/api/videos/{id}/process", json={"detect": False, "zones": []}
        ).status_code
        == 202
    )
    assert (
        c.post(
            f"/api/videos/{id}/process", json={"detect": False, "zones": []}
        ).status_code
        == 409
    )
    assert worker.run_once()
    result = c.get(f"/api/videos/{id}").json()
    assert result["status"] == "COMPLETED", result
    response = c.get(f"/api/videos/{id}/media", headers={"Range": "bytes=0-99"})
    assert response.status_code == 206 and len(response.content) == 100
    incident = c.post(
        "/api/incidents",
        json={
            "video_id": id,
            "timestamp": 2,
            "notes": "Synthetic motion for workflow testing",
        },
    ).json()
    assert worker.run_once()
    record = c.get(f'/api/incidents/{incident["id"]}').json()
    assert record["evidence_status"] == "ready", record
    assert record["clip_start"] == 0 and record["clip_duration"] == 4
    assert (
        c.get(f'/api/incidents/{incident["id"]}/evidence/thumbnail').status_code == 200
    )
    assert c.get(f'/api/incidents/{incident["id"]}/evidence/clip').status_code == 200
    # Observations never create incidents without a human request.
    assert db.incidents.count_documents({}) == 1


def test_failed_worker_is_visible(env, monkeypatch):
    db, c, login = env
    login()
    db.videos.insert_one(
        {
            "_id": "broken",
            "status": "QUEUED",
            "uploaded_at": common.now(),
            "source_path": "missing",
            "detect": False,
        }
    )
    monkeypatch.setattr(
        worker,
        "normalize",
        lambda *a: (_ for _ in ()).throw(RuntimeError("decoder failed")),
    )
    worker.run_once()
    record = c.get("/api/videos/broken").json()
    assert record["status"] == "FAILED" and "decoder failed" in record["error"]
