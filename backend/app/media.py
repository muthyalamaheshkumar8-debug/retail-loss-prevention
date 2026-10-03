import json
import shutil
import subprocess
from pathlib import Path
from .config import settings


def ffmpeg(*args):
    result = subprocess.run(
        [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            "-nostdin",
            "-y",
            *map(str, args),
        ],
        capture_output=True,
        text=True,
        timeout=7200,
    )
    if result.returncode:
        raise RuntimeError("Video conversion failed: " + result.stderr[-800:])


def probe(path):
    result = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_format",
            "-show_streams",
            "-of",
            "json",
            str(path),
        ],
        capture_output=True,
        text=True,
        timeout=30,
    )
    if result.returncode:
        raise ValueError("File is not a readable video")
    data = json.loads(result.stdout)
    streams = [s for s in data.get("streams", []) if s.get("codec_type") == "video"]
    if not streams:
        raise ValueError("File has no video stream")
    stream = streams[0]
    duration = float(data.get("format", {}).get("duration", stream.get("duration", 0)))
    if not 0 < duration <= settings.max_duration:
        raise ValueError(f"Video must be between 0 and {settings.max_duration} seconds")
    if stream.get("width", 0) * stream.get("height", 0) > 4096 * 2160:
        raise ValueError("Video resolution must not exceed 4K")
    return {"duration": duration, "width": stream["width"], "height": stream["height"]}


def normalize(source, destination):
    ffmpeg(
        "-i",
        source,
        "-map",
        "0:v:0",
        "-an",
        "-vf",
        r"scale=w=min(1280\,iw):h=-2",
        "-r",
        "15",
        "-c:v",
        "libx264",
        "-preset",
        "veryfast",
        "-pix_fmt",
        "yuv420p",
        "-movflags",
        "+faststart",
        destination,
    )


def evidence(video, incident):
    folder = settings.data_dir / "evidence"
    folder.mkdir(parents=True, exist_ok=True)
    start = max(0, incident["timestamp"] - 10)
    length = min(video["duration"] - start, incident["timestamp"] + 10 - start)
    clip, image = folder / f'{incident["_id"]}.mp4', folder / f'{incident["_id"]}.jpg'
    ffmpeg(
        "-ss",
        start,
        "-i",
        video["playback_path"],
        "-t",
        length,
        "-an",
        "-c:v",
        "libx264",
        "-preset",
        "veryfast",
        "-pix_fmt",
        "yuv420p",
        "-movflags",
        "+faststart",
        clip,
    )
    ffmpeg(
        "-ss",
        incident["timestamp"],
        "-i",
        video["playback_path"],
        "-frames:v",
        "1",
        image,
    )
    if not clip.exists() or not image.exists():
        raise RuntimeError("Evidence could not be generated at this timestamp")
    return {"clip_start": start, "clip_duration": length, "evidence_status": "ready"}
