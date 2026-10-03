from pathlib import Path
import pytest
import mongomock
from fastapi.testclient import TestClient
from app import main, security, common, worker, database
from app.config import settings


@pytest.fixture
def env(monkeypatch, tmp_path):
    mock = mongomock.MongoClient().loss_prevention
    mock.users.create_index("email", unique=True)
    for module in (main, security, common, worker, database):
        monkeypatch.setattr(module, "db", mock)
    monkeypatch.setattr(
        settings, "jwt_secret", "test-only-secret-that-is-longer-than-32-characters"
    )
    monkeypatch.setattr(settings, "data_dir", tmp_path)
    monkeypatch.setattr(settings, "cv_enabled", True)
    (tmp_path / "videos").mkdir()
    (tmp_path / "evidence").mkdir()
    security.attempts.clear()
    for id, role in [
        ("admin", "admin"),
        ("investigator", "investigator"),
        ("other", "investigator"),
        ("reviewer", "reviewer"),
    ]:
        mock.users.insert_one(
            {
                "_id": id,
                "email": id + "@example.com",
                "name": id,
                "role": role,
                "disabled": False,
                "password_hash": security.password_hash.hash("TestPassword123!"),
                "created_at": common.now(),
            }
        )
    # No context manager: bypass production startup checks; each test supplies its database.
    client = TestClient(main.app)

    def sign_in(id="admin"):
        response = client.post(
            "/api/auth/login",
            json={"email": id + "@example.com", "password": "TestPassword123!"},
        )
        assert response.status_code == 200
        return client

    yield mock, client, sign_in
    client.close()


@pytest.fixture
def source_video(tmp_path):
    import cv2
    import numpy as np

    path = tmp_path / "source.avi"
    writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"MJPG"), 10, (320, 240))
    assert writer.isOpened()
    for n in range(40):
        frame = np.full((240, 320, 3), 40, np.uint8)
        cv2.rectangle(frame, (20 + n * 3, 70), (60 + n * 3, 170), (50, 190, 110), -1)
        writer.write(frame)
    writer.release()
    return path


@pytest.fixture
def seeded(env, tmp_path):
    db, client, login = env
    login()
    store = client.post(
        "/api/stores",
        json={"name": "Test Store", "location": "Test", "cameras": ["Checkout"]},
    ).json()
    playback = tmp_path / "videos" / "ready.mp4"
    playback.write_bytes(b"fake-test-media")
    db.videos.insert_one(
        {
            "_id": "VID-ready",
            "filename": "ready.mp4",
            "store_id": store["id"],
            "camera_id": "Checkout",
            "duration": 30,
            "status": "COMPLETED",
            "playback_path": str(playback),
            "uploaded_at": common.now(),
            "zones": [],
        }
    )
    return db, client, login
