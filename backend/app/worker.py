"""One durable polling worker per deployment; queued jobs survive API restarts."""

import logging
import signal
import time
from pymongo import ReturnDocument
from .database import db, initialize
from .config import settings
from .common import now, uid, audit
from .media import normalize, evidence
from .vision import analyze

log = logging.getLogger("worker")
running = True


def process_video(video):
    vid = video["_id"]
    folder = settings.data_dir / "videos"
    playback, overlay = folder / f"{vid}-playback.mp4", folder / f"{vid}-overlay.mp4"
    temporary = folder / f"{vid}-tracking.mp4"
    try:
        db.events.delete_many({"video_id": vid})
        db.videos.update_one({"_id": vid}, {"$set": {"progress": 5}})
        normalize(video["source_path"], playback)
        update = {"playback_path": str(playback), "progress": 25}
        db.videos.update_one({"_id": vid}, {"$set": update})
        if video.get("detect"):
            if not settings.cv_enabled:
                raise RuntimeError(
                    "CV is disabled. Requeue without tracking or enable CV_ENABLED."
                )
            db.videos.update_one({"_id": vid}, {"$set": {"status": "ANALYZING"}})

            def emit(event):
                db.events.insert_one(
                    {"_id": uid("EVT"), "video_id": vid, **event, "created_at": now()}
                )

            model_path = settings.yolo_model
            if model_path == "yolo11n.pt":
                model_dir = settings.data_dir / "models"
                model_dir.mkdir(parents=True, exist_ok=True)
                model_path = str(model_dir / model_path)
            analyze(
                playback,
                temporary,
                video["zones"],
                model_path,
                settings.frame_stride,
                lambda p: db.videos.update_one({"_id": vid}, {"$set": {"progress": p}}),
                emit,
            )
            normalize(temporary, overlay)
            update["overlay_path"] = str(overlay)
            temporary.unlink(missing_ok=True)
        update.update(status="COMPLETED", progress=100, completed_at=now(), error=None)
        db.videos.update_one({"_id": vid}, {"$set": update})
        audit(vid, "worker", "processing_completed")
    except Exception as exc:
        log.exception("Video job failed: %s", vid)
        db.videos.update_one(
            {"_id": vid}, {"$set": {"status": "FAILED", "error": str(exc)[:1000]}}
        )


def process_evidence(item):
    try:
        video = db.videos.find_one({"_id": item["video_id"]})
        result = evidence(video, item)
        db.incidents.update_one({"_id": item["_id"]}, {"$set": result})
    except Exception as exc:
        log.exception("Evidence job failed")
        db.incidents.update_one(
            {"_id": item["_id"]},
            {"$set": {"evidence_status": "failed", "evidence_error": str(exc)[:1000]}},
        )


def run_once():
    item = db.incidents.find_one_and_update(
        {"evidence_status": "queued"},
        {"$set": {"evidence_status": "processing"}},
        return_document=ReturnDocument.AFTER,
    )
    if item:
        process_evidence(item)
        return True
    video = db.videos.find_one_and_update(
        {"status": "QUEUED"},
        {"$set": {"status": "PROCESSING", "started_at": now()}},
        sort=[("uploaded_at", 1)],
        return_document=ReturnDocument.AFTER,
    )
    if video:
        process_video(video)
        return True
    return False


def stop(*_):
    global running
    running = False


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s"
    )
    initialize()
    # This installation intentionally runs ONE worker. Interrupted jobs are explicit failures.
    db.videos.update_many(
        {"status": {"$in": ["PROCESSING", "ANALYZING"]}},
        {
            "$set": {
                "status": "FAILED",
                "error": "Worker restarted; reprocess the video to retry.",
            }
        },
    )
    db.incidents.update_many(
        {"evidence_status": "processing"}, {"$set": {"evidence_status": "queued"}}
    )
    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    while running:
        try:
            if not run_once():
                time.sleep(2)
        except Exception:
            log.exception("Worker database unavailable; retrying")
            time.sleep(5)
