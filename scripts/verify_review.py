"""Check technical consistency of a rendered review package."""
import json
import math
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


if __name__ == "__main__":
    spec_path, result = map(Path, sys.argv[1:])
    spec = json.loads(spec_path.read_text())
    pack = json.loads((result / "pack.json").read_text())
    probe = json.loads((result / "probe.json").read_text())
    verify(spec, pack, probe, result / "thumb.jpg")
    shutil.copyfile(spec_path, result / "spec.json")
