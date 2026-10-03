from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    mongodb_uri: str = "mongodb://localhost:27017"
    database_name: str = "loss_prevention"
    jwt_secret: str = ""
    admin_email: str = "admin@example.com"
    admin_password: str = ""
    cookie_secure: bool = False
    app_origin: str = "http://localhost:8080"
    data_dir: Path = Path("runtime")
    cv_enabled: bool = True
    yolo_model: str = "yolo11n.pt"
    frame_stride: int = 3
    max_upload_bytes: int = 500 * 1024 * 1024
    max_duration: int = 3600


settings = Settings()
