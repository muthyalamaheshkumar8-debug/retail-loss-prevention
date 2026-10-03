from typing import Literal
from pydantic import BaseModel, Field, field_validator

Role = Literal["admin", "investigator", "reviewer"]
Status = Literal["NEEDS_REVIEW", "IN_REVIEW", "NOT_AN_INCIDENT", "ESCALATED", "CLOSED"]
Category = Literal[
    "checkout_anomaly",
    "item_handling",
    "zone_transition",
    "possible_scan_mismatch",
    "other",
]


class Login(BaseModel):
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=1, max_length=256)


class UserCreate(Login):
    name: str = Field(min_length=1, max_length=100)
    role: Role

    @field_validator("password")
    @classmethod
    def strong(cls, value):
        if len(value) < 12:
            raise ValueError("Use at least 12 characters")
        return value


class StoreCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    location: str = Field(default="", max_length=200)
    cameras: list[str] = Field(min_length=1, max_length=50)

    @field_validator("cameras")
    @classmethod
    def valid_cameras(cls, value):
        if any(not s.strip() or len(s) > 80 for s in value) or len(set(value)) != len(
            value
        ):
            raise ValueError(
                "Camera names must be unique and nonempty, up to 80 characters"
            )
        return value


class Zone(BaseModel):
    name: str = Field(min_length=1, max_length=50)
    x1: float = Field(ge=0, le=1)
    y1: float = Field(ge=0, le=1)
    x2: float = Field(ge=0, le=1)
    y2: float = Field(ge=0, le=1)


class ProcessRequest(BaseModel):
    zones: list[Zone] = Field(default_factory=list, max_length=10)
    detect: bool = True


class IncidentCreate(BaseModel):
    video_id: str
    timestamp: float = Field(ge=0)
    category: Category = "other"
    priority: Literal["low", "medium", "high"] = "medium"
    notes: str = Field(min_length=1, max_length=5000)
    event_id: str | None = None


class Review(BaseModel):
    status: Status
    notes: str = Field(min_length=1, max_length=5000)
    version: int = Field(ge=0)


class Assignment(BaseModel):
    reviewer_id: str | None
    version: int = Field(ge=0)
