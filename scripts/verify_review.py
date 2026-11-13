"""Check technical consistency of a rendered review package."""
import json
import math
import re
import subprocess
import shutil
import sys
from pathlib import Path

from PIL import Image


def verify(spec: dict, pack: dict, probe: dict, thumbnail: Path) -> None:
    for key in ("id", "channel", "format", "publishAt"):
        if pack.get(key) != spec.get(key):
            raise ValueError(f"Pack {key} differs from the spec")
    dimensions = {"long": (1920, 1080), "short": (1080, 1920)}[spec["format"]]
    streams = probe["streams"]
    video = next((s for s in streams if s["codec_type"] == "video"), {})
    audio = next((s for s in streams if s["codec_type"] == "audio"), {})
    if video.get("codec_name") != "h264" or (video.get("width"), video.get("height")) != dimensions:
        raise ValueError("Unexpected video codec or dimensions")
    if audio.get("codec_name") != "aac":
        raise ValueError("Missing AAC audio")
    duration = float(probe["format"]["duration"])
    planned = float(pack["durationSec"])
    # Scene frames are quantized separately, so allow one video frame per scene.
    tolerance = 0.25 + len(spec["scenes"]) / 24
    if not math.isfinite(duration) or not math.isfinite(planned) or min(duration, planned) <= 0 or abs(duration - planned) > tolerance:
        raise ValueError("Media duration disagrees with the render pack")
    with Image.open(thumbnail) as image:
        if image.format != "JPEG":
            raise ValueError("Expected JPEG thumbnail")
        image.load()

    # Model-generated content is not accepted just because it parsed as JSON.
    # Review scores must be present and exceed the editorial minimums. This
    # rejects old specs with null scores that previously slipped through.
    meta = spec.get("meta") or {}
    if meta.get("generator") == "autopilot":
        review = meta.get("review") or {}
        for name, minimum in (("hook", 6), ("originality", 6), ("accuracy", 7)):
            score = review.get(name)
            if type(score) is not int or score < minimum or score > 10:
                raise ValueError(f"Unapproved Autopilot editorial score: {name}")


def verify_audio(video: Path) -> tuple[float, float]:
    """Reject a practically silent master; video stream decoding alone misses mute bugs."""
    proc = subprocess.run(
        ["ffmpeg", "-nostdin", "-hide_banner", "-nostats", "-i", str(video),
         "-map", "0:a:0", "-vn", "-af", "volumedetect", "-f", "null", "-"],
        capture_output=True, text=True, timeout=180, check=False,
    )
    if proc.returncode != 0:
        raise ValueError(f"Audio decoding failed: {proc.stderr[-250:]}")
    values = {}
    for key in ("mean_volume", "max_volume"):
        match = re.search(rf"\b{key}:\s*(-?(?:\d+(?:\.\d+)?|inf))\s*dB", proc.stderr)
        if not match:
            raise ValueError(f"Missing {key} measurement from audio")
        values[key] = float(match.group(1))
    if not all(math.isfinite(value) for value in values.values()):
        raise ValueError("Silent or invalid audio levels")
    if values["mean_volume"] < -50 or values["max_volume"] < -40:
        raise ValueError("Audio is effectively silent")
    return values["mean_volume"], values["max_volume"]


if __name__ == "__main__":
    spec_path, result = map(Path, sys.argv[1:])
    spec = json.loads(spec_path.read_text())
    pack = json.loads((result / "pack.json").read_text())
    probe = json.loads((result / "probe.json").read_text())
    verify(spec, pack, probe, result / "thumb.jpg")
    mean_db, max_db = verify_audio(result / "video.mp4")
    print(f"Audio check passed: mean {mean_db:.1f} dBFS, max {max_db:.1f} dBFS")
    recorded_spec = result / "spec.json"
    if spec_path.resolve() != recorded_spec.resolve():
        shutil.copyfile(spec_path, recorded_spec)
