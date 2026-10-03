"""Translate Render settings without writing credentials to disk or stdout."""
import os
from pathlib import Path
from urllib.parse import quote, urlsplit


def configure(environ):
    env = dict(environ)
    port = int(env.get("PORT", "10000"))
    if not 1024 <= port <= 65535 or port == 8000:
        raise ValueError("PORT must be between 1024 and 65535 and differ from 8000")
    origin = env.get("APP_ORIGIN") or env.get("RENDER_EXTERNAL_URL", "")
    parsed = urlsplit(origin)
    if (parsed.scheme != "https" or not parsed.hostname or parsed.username
            or parsed.password or parsed.path not in ("", "/")
            or parsed.query or parsed.fragment):
        raise ValueError("APP_ORIGIN or RENDER_EXTERNAL_URL must be an HTTPS origin")
    env["APP_ORIGIN"] = origin.rstrip("/")
    env["COOKIE_SECURE"] = "true"
    env["DATA_DIR"] = "/data"
    env["YOLO_CONFIG_DIR"] = "/data/ultralytics"
    if not env.get("MONGODB_URI"):
        for key in ("MONGODB_HOST", "MONGODB_USER", "MONGODB_PASSWORD"):
            if not env.get(key):
                raise ValueError(f"Missing {key}")
        host = env["MONGODB_HOST"]
        if any(char not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789.-" for char in host):
            raise ValueError("MONGODB_HOST must be a hostname")
        user = quote(env["MONGODB_USER"], safe="")
        password = quote(env["MONGODB_PASSWORD"], safe="")
        env["MONGODB_URI"] = f"mongodb://{user}:{password}@{host}:27017/?authSource=admin"
    if len(env.get("JWT_SECRET", "")) < 32 or env["JWT_SECRET"].startswith("replace-"):
        raise ValueError("JWT_SECRET must contain at least 32 random characters")
    if len(env.get("ADMIN_PASSWORD", "")) < 12 or env["ADMIN_PASSWORD"].startswith("replace-"):
        raise ValueError("ADMIN_PASSWORD must contain at least 12 characters")
    if "@" not in env.get("ADMIN_EMAIL", ""):
        raise ValueError("Set ADMIN_EMAIL")
    return env, port


if __name__ == "__main__":
    env, port = configure(os.environ)
    for name in ("", "videos", "evidence", "models", "ultralytics"):
        path = Path("/data") / name
        path.mkdir(parents=True, exist_ok=True)
        os.chown(path, 10001, 10001)
    template = Path("/app/deploy/nginx.conf.template").read_text()
    Path("/etc/nginx/conf.d/retail-review.conf").write_text(template.replace("__PORT__", str(port)))
    os.execve("/usr/bin/supervisord", ["supervisord", "-c", "/app/deploy/supervisord.conf"], env)
