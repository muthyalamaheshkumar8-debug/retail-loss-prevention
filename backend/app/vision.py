"""Neutral, per-video tracking. No identity, criminality scores or automated incidents."""

import cv2
import os
from pathlib import Path
from .config import settings as app_settings


class ZoneEngine:
    def __init__(self, zones):
        self.zones = zones
        self.previous = {}

    def update(self, track_id, x, y, timestamp):
        active = {
            z["name"]
            for z in self.zones
            if z["x1"] <= x <= z["x2"] and z["y1"] <= y <= z["y2"]
        }
        old = self.previous.get(track_id, set())
        self.previous[track_id] = active
        return [
            {
                "timestamp": round(timestamp, 3),
                "track_id": str(track_id),
                "zone": name,
                "event_type": kind,
            }
            for names, kind in [
                (active - old, "zone_entered"),
                (old - active, "zone_left"),
            ]
            for name in sorted(names)
        ]


def analyze(source, target, zones, model_path, stride, progress, emit):
    config_dir = Path(
        os.environ.get("YOLO_CONFIG_DIR", str(app_settings.data_dir / "ultralytics"))
    )
    config_dir.mkdir(parents=True, exist_ok=True)
    os.environ["YOLO_CONFIG_DIR"] = str(config_dir.resolve())
    from ultralytics import YOLO, settings as yolo_settings

    yolo_settings.update({"sync": False})

    model = YOLO(model_path)
    cap = cv2.VideoCapture(str(source))
    fps = cap.get(cv2.CAP_PROP_FPS)
    count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    width, height = int(cap.get(3)), int(cap.get(4))
    # A variable-rate input has already been normalized by ffmpeg.
    out = cv2.VideoWriter(
        str(target), cv2.VideoWriter_fourcc(*"mp4v"), fps / stride, (width, height)
    )
    if not cap.isOpened() or not out.isOpened():
        cap.release()
        out.release()
        raise RuntimeError("Cannot open video decoder or annotation encoder")
    engine = ZoneEngine(zones)
    index = 0
    event_count = 0
    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                break
            if index % stride == 0:
                result = model.track(
                    frame,
                    persist=True,
                    tracker="bytetrack.yaml",
                    classes=[0],
                    conf=0.35,
                    verbose=False,
                )[0]
                if result.boxes is not None and result.boxes.id is not None:
                    for box, tid, confidence in zip(
                        result.boxes.xyxy.cpu().tolist(),
                        result.boxes.id.cpu().tolist(),
                        result.boxes.conf.cpu().tolist(),
                    ):
                        x1, y1, x2, y2 = box
                        for event in engine.update(
                            int(tid), (x1 + x2) / (2 * width), y2 / height, index / fps
                        ):
                            if event_count < 10000:
                                emit(
                                    {
                                        **event,
                                        "detection_confidence": round(confidence, 3),
                                    }
                                )
                                event_count += 1
                        cv2.rectangle(
                            frame,
                            (int(x1), int(y1)),
                            (int(x2), int(y2)),
                            (70, 210, 180),
                            2,
                        )
                        cv2.putText(
                            frame,
                            f"P{int(tid)}",
                            (int(x1), max(20, int(y1) - 8)),
                            cv2.FONT_HERSHEY_SIMPLEX,
                            0.6,
                            (70, 210, 180),
                            2,
                        )
                for z in zones:
                    a, b = (int(z["x1"] * width), int(z["y1"] * height)), (
                        int(z["x2"] * width),
                        int(z["y2"] * height),
                    )
                    cv2.rectangle(frame, a, b, (220, 170, 80), 2)
                    cv2.putText(
                        frame,
                        z["name"],
                        (a[0], max(20, a[1])),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.5,
                        (220, 170, 80),
                        1,
                    )
                out.write(frame)
                if index % (stride * 20) == 0:
                    progress(min(90, 25 + int(index / max(count, 1) * 65)))
            index += 1
    finally:
        cap.release()
        out.release()
    if index == 0:
        raise RuntimeError("Video contains no decodable frames")
    return event_count
