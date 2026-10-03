from pymongo import MongoClient, ASCENDING
from .config import settings

client = MongoClient(settings.mongodb_uri, serverSelectionTimeoutMS=5000)
db = client[settings.database_name]


def initialize():
    client.admin.command("ping")
    db.users.create_index("email", unique=True)
    db.videos.create_index([("status", ASCENDING), ("uploaded_at", ASCENDING)])
    db.incidents.create_index([("store_id", ASCENDING), ("created_at", ASCENDING)])
    db.events.create_index([("video_id", ASCENDING), ("timestamp", ASCENDING)])
    db.investigations.create_index("incident_id")
    db.audit.create_index([("target_id", ASCENDING), ("at", ASCENDING)])
