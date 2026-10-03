"""Render a portfolio explainer from a generated still; never run or claim detection.

Requires Pillow, NumPy and FFmpeg. All boxes, IDs and example observations are
scripted illustrations. Use the application locally to test actual YOLO tracking.
"""

import argparse
from pathlib import Path
import shutil
import subprocess

import numpy as np
from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
SIZE = (1280, 720)
FPS = 24
DURATION = 22
SCENE = (24, 112, 896, 504)
NAVY = (12, 23, 32)
PANEL = (21, 37, 48)
WHITE = (237, 244, 248)
MUTED = (160, 180, 194)
MINT = (111, 232, 190)
BLUE = (107, 192, 249)
AMBER = (248, 201, 116)
STEPS = [
    ("01", "Locate people", ["Boxes illustrate where", "people appear in footage."], "ILLUSTRATIVE PERSON BOXES"),
    ("02", "Follow the footage", ["P01 and P02 represent", "IDs within one video."], "PER-VIDEO IDS / NO IDENTITY MATCHING"),
    ("03", "Observe a zone", ["A marked aisle provides", "context for the reviewer."], "EXAMPLE ZONE / NEUTRAL OBSERVATION"),
    ("04", "Review the context", ["A person reviews footage", "before creating a case."], "HUMAN REVIEW / HUMAN DECISION"),
]


def font(size, bold=False):
    name = "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"
    return ImageFont.truetype(name, size)


FONTS = {(size, bold): font(size, bold) for size in (13, 14, 15, 16, 18, 20, 22, 24, 28, 32, 42) for bold in (False, True)}


def text(draw, xy, value, size=18, color=WHITE, bold=False):
    draw.text(xy, value, font=FONTS[size, bold], fill=color)


def pill(draw, xy, value, color=MINT, size=14):
    x, y = xy
    width = draw.textlength(value, font=FONTS[size, True]) + 24
    draw.rounded_rectangle((x, y, x + width, y + 29), radius=8, fill=PANEL, outline=color)
    text(draw, (x + 12, y + 5), value, size, color, True)


def crop_scene(photo, t):
    # A gentle editorial push-in; the shoppers themselves are a still image.
    zoom = 1 + 0.025 * min(t / DURATION, 1)
    pw, ph = photo.size
    cw, ch = pw / zoom, ph / zoom
    left, top = (pw - cw) / 2, (ph - ch) / 2
    image = photo.crop((left, top, left + cw, top + ch)).resize(SCENE[2:], Image.Resampling.LANCZOS)

    def point(x, y):
        return SCENE[0] + (x * pw - left) / cw * SCENE[2], SCENE[1] + (y * ph - top) / ch * SCENE[3]

    return image, point


def person_box(draw, point, coords, label, color, reveal):
    if reveal <= 0:
        return
    a, b = point(coords[0], coords[1]), point(coords[2], coords[3])
    x1, y1 = a
    x2, y2 = b
    # Animated corner brackets rather than invented confidence scores.
    length = 19 * min(reveal, 1)
    draw.rectangle((*a, *b), outline=color, width=2)
    for x, y, dx, dy in [(x1, y1, 1, 1), (x2, y1, -1, 1), (x1, y2, 1, -1), (x2, y2, -1, -1)]:
        draw.line((x, y, x + dx * length, y), fill=color, width=4)
        draw.line((x, y, x, y + dy * length), fill=color, width=4)
    pill(draw, (int(x1), max(SCENE[1] + 16, int(y1) - 36)), label, color, 13)


def render(photo, t):
    canvas = Image.new("RGB", SIZE, NAVY)
    scene, point = crop_scene(photo, t)
    canvas.paste(scene, SCENE[:2])
    draw = ImageDraw.Draw(canvas)
    draw.rounded_rectangle((24, 22, 68, 66), radius=12, fill=MINT)
    # A small camera glyph belongs to the explainer, not to the application UI.
    draw.rounded_rectangle((34, 36, 53, 52), radius=3, fill=NAVY)
    draw.polygon([(53, 40), (61, 36), (61, 52), (53, 48)], fill=NAVY)
    text(draw, (82, 19), "RETAIL REVIEW", 24, WHITE, True)
    text(draw, (83, 52), "A clearer view of the store", 15, MUTED)
    pill(draw, (886, 26), "AI-GENERATED CONCEPT DEMO", AMBER, 15)

    active = max(0, min(3, int((t - 2) / 4)))
    draw.rounded_rectangle((940, 112, 1256, 616), radius=14, fill=PANEL)
    text(draw, (961, 134), "HOW IT WORKS", 14, MUTED, True)
    number, title, lines, caption = STEPS[active]
    text(draw, (961, 169), number, 42, MINT, True)
    text(draw, (961, 224), title, 20, WHITE, True)
    for i, line in enumerate(lines):
        text(draw, (961, 261 + i * 25), line, 16, MUTED)
    draw.line((961, 329, 1235, 329), fill=(49, 69, 82), width=1)
    for i, (_, label, _, _) in enumerate(STEPS):
        y = 351 + i * 45
        color = MINT if i == active else MUTED
        draw.ellipse((962, y + 4, 978, y + 20), fill=color if i <= active else PANEL, outline=color)
        text(draw, (990, y), label, 16, color, i == active)

    # The source is a generated still. These known coordinates are drawn by hand.
    if t >= 2:
        pill(draw, (40, 128), "ILLUSTRATIVE OVERLAYS", WHITE, 13)
        person_box(draw, point, (.329, .285, .448, .752), "PERSON / P01" if t >= 6 else "PERSON", MINT, (t - 2) * 2)
        person_box(draw, point, (.712, .096, .788, .431), "PERSON / P02" if t >= 6 else "PERSON", BLUE, (t - 3) * 2)

    if t >= 10:
        a, b = point(.21, .44), point(.52, .91)
        overlay = Image.new("RGBA", SIZE, (0, 0, 0, 0))
        od = ImageDraw.Draw(overlay)
        od.rectangle((*a, *b), fill=(*AMBER, 22), outline=(*AMBER, 255), width=2)
        canvas = Image.alpha_composite(canvas.convert("RGBA"), overlay).convert("RGB")
        draw = ImageDraw.Draw(canvas)
        pill(draw, (int(a[0]) + 9, int(b[1]) - 39), "EXAMPLE ZONE: PRODUCE AISLE", AMBER, 13)

    if t >= 14:
        draw.rounded_rectangle((44, 519, 475, 596), radius=12, fill=NAVY, outline=MINT)
        text(draw, (61, 533), "Reviewer examines the context", 18, WHITE, True)
        text(draw, (61, 562), "Zone presence alone does not establish an incident.", 14, MUTED)

    text(draw, (963, 562), "Free web demo:", 14, MUTED)
    text(draw, (963, 583), "person tracking is disabled", 14, AMBER)
    draw.rectangle((24, 640, 1256, 643), fill=PANEL)
    draw.rectangle((24, 640, 24 + int(1232 * t / DURATION), 643), fill=MINT)
    text(draw, (24, 660), caption, 14, WHITE, True)
    text(draw, (24, 687), "Generated still + scripted boxes / IDs. Not a model recording or accuracy test.", 14, MUTED)
    text(draw, (1184, 660), f"{int(t):02d}s / 22s", 13, MUTED)

    if t < 2:
        shade = Image.new("RGBA", SIZE, (0, 0, 0, 0))
        sd = ImageDraw.Draw(shade)
        sd.rectangle((24, 112, 920, 616), fill=(*NAVY, 170))
        canvas = Image.alpha_composite(canvas.convert("RGBA"), shade).convert("RGB")
        draw = ImageDraw.Draw(canvas)
        text(draw, (64, 270), "See the footage.", 42, WHITE, True)
        text(draw, (64, 326), "Understand the context.", 42, MINT, True)
        text(draw, (66, 393), "An animated guide to the intended review workflow", 20, WHITE)

    if t >= 18:
        shade = Image.new("RGBA", SIZE, (0, 0, 0, 0))
        sd = ImageDraw.Draw(shade)
        sd.rectangle((24, 112, 920, 616), fill=(*NAVY, 210))
        canvas = Image.alpha_composite(canvas.convert("RGBA"), shade).convert("RGB")
        draw = ImageDraw.Draw(canvas)
        text(draw, (64, 239), "Observations help.", 42, WHITE, True)
        text(draw, (64, 295), "People decide.", 42, MINT, True)
        text(draw, (67, 372), "Explore the code. Run the full tracking setup locally.", 20, WHITE)
        text(draw, (67, 410), "React  /  FastAPI  /  MongoDB  /  optional YOLO + ByteTrack", 18, MUTED)
        pill(draw, (66, 465), "OPEN SOURCE / GITHUB", MINT, 15)
    return canvas


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scene", type=Path, default=ROOT / "docs/demo/store-scene.jpg")
    parser.add_argument("--output", type=Path, default=ROOT / "docs/demo/retail-review-concept.mp4")
    args = parser.parse_args()
    if not shutil.which("ffmpeg"):
        raise SystemExit("Install FFmpeg before rendering.")
    photo = Image.open(args.scene).convert("RGB")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    command = [
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "rawvideo",
        "-pix_fmt", "rgb24", "-s", "1280x720", "-r", str(FPS), "-i", "pipe:0",
        "-an", "-c:v", "libx264", "-preset", "medium", "-crf", "27", "-threads", "2",
        "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(args.output),
    ]
    process = subprocess.Popen(command, stdin=subprocess.PIPE)
    try:
        for frame in range(DURATION * FPS):
            process.stdin.write(np.asarray(render(photo, frame / FPS)).tobytes())
            if frame % (4 * FPS) == 0:
                print(f"Rendered {frame / FPS:.0f}/{DURATION}s", flush=True)
    finally:
        process.stdin.close()
    if process.wait() != 0:
        raise SystemExit("FFmpeg encoding failed.")
    render(photo, 12).save(args.output.parent / "poster.jpg", quality=90, optimize=True)
    # Preview uses the central workflow, not the title or closing card.
    subprocess.run([
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-ss", "2", "-t", "12",
        "-i", str(args.output), "-filter_complex",
        "fps=6,scale=560:-1:flags=lanczos,split[a][b];[a]palettegen=max_colors=96[p];[b][p]paletteuse=dither=bayer:bayer_scale=3",
        "-loop", "0", str(args.output.parent / "preview.gif"),
    ], check=True)
    print(f"Saved {args.output}")


if __name__ == "__main__":
    main()
