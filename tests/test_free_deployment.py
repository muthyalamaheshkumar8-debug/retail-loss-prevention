"""Check the free deployment boundary and its security-sensitive startup inputs."""
import importlib.util
from pathlib import Path
import pytest
from app.config import settings

spec = importlib.util.spec_from_file_location(
    "render_start", Path(__file__).resolve().parents[1] / "deploy/render/start.py"
)
render_start = importlib.util.module_from_spec(spec)
spec.loader.exec_module(render_start)


def test_free_upload_limits_reach_browser(env, monkeypatch):
    _, client, login = env
    login()
    monkeypatch.setattr(settings, "max_upload_bytes", 20 * 1024 * 1024)
    monkeypatch.setattr(settings, "max_duration", 120)
    monkeypatch.setattr(settings, "cv_enabled", False)
    config = client.get("/api/settings").json()
    assert config["max_upload_mb"] == 20
    assert config["max_duration_minutes"] == 2
    assert config["cv_enabled"] is False


@pytest.fixture
def startup_env():
    return {
        "RENDER_EXTERNAL_URL": "https://retail-demo.onrender.com",
        "JWT_SECRET": "test-only-secret-that-is-longer-than-32-characters",
        "ADMIN_EMAIL": "test@example.com",
        "ADMIN_PASSWORD": "test-only-password",
        "MONGODB_URI": "mongodb+srv://test:dummy@cluster.example.test/",
    }


def test_free_startup_preserves_database_secret_and_secure_origin(startup_env):
    configured, port = render_start.configure(startup_env)
    assert configured["MONGODB_URI"] == startup_env["MONGODB_URI"]
    assert configured["APP_ORIGIN"] == "https://retail-demo.onrender.com"
    assert configured["COOKIE_SECURE"] == "true"
    assert configured["DATA_DIR"] == "/data"
    assert port == 10000


@pytest.mark.parametrize("change", [
    {"APP_ORIGIN": "http://insecure.test"},
    {"APP_ORIGIN": "https://example.test/private"},
    {"PORT": "8000"},
    {"JWT_SECRET": "short"},
    {"ADMIN_PASSWORD": "short"},
    {"MONGODB_URI": ""},
])
def test_free_startup_rejects_invalid_settings(startup_env, change):
    with pytest.raises(ValueError):
        render_start.configure(startup_env | change)
