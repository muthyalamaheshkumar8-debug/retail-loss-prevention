"""Generate a clearly labeled synthetic clip for upload/playback testing, not detector validation."""

import argparse
from pathlib import Path
import cv2
import numpy as np

parser = argparse.ArgumentParser()
parser.add_argument("--output", type=Path, default=Path("runtime/staged-motion.avi"))
args = parser.parse_args()
args.output.parent.mkdir(parents=True, exist_ok=True)
writer = cv2.VideoWriter(
    str(args.output), cv2.VideoWriter_fourcc(*"MJPG"), 15, (640, 360)
)
if not writer.isOpened():
    raise SystemExit("Could not open video encoder")
for index in range(450):
    frame = np.full((360, 640, 3), (45, 55, 48), np.uint8)
    cv2.rectangle(frame, (350, 80), (570, 310), (90, 140, 110), 2)
    cv2.putText(
        frame,
        "SYNTHETIC WORKFLOW TEST",
        (25, 35),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.7,
        (210, 235, 210),
        2,
    )
    cv2.putText(
        frame,
        "Moving shapes are not person detections",
        (25, 345),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.5,
        (180, 200, 180),
        1,
    )
    x = 50 + (index * 2) % 500
    cv2.rectangle(frame, (x, 130), (x + 45, 260), (115, 180, 220), -1)
    writer.write(frame)
writer.release()
print(
    f"Saved {args.output}. Upload and process with tracking disabled to test the manual review workflow."
)
