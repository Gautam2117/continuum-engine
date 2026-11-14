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
    expected3d = sum((scene.get("show") or {}).get("type") == "b3d" for scene in spec["scenes"])
    expected_images = sum((scene.get("show") or {}).get("type") == "image" for scene in spec["scenes"])
    expected_personas = sum((scene.get("show") or {}).get("type") == "persona" for scene in spec["scenes"])
    evidence = pack.get("renderEvidence") or {}
    if expected3d and (evidence.get("b3dRequested") != expected3d or evidence.get("b3dRendered") != expected3d):
        raise ValueError("Requested 3D scene silently fell back to 2D; creative review is not complete")
    if spec["channel"] == "Pixel Fables" and evidence.get("pixelPosterFromReal3d") is not True:
        raise ValueError("Pixel Fables click surface lacks a real original 3D story frame")
    if expected_images and (not isinstance(evidence.get("imageFallbackScenes"), list) or evidence["imageFallbackScenes"]):
        raise ValueError("Required licensed image was unavailable; creative review is not complete")
    if expected_personas and (not isinstance(evidence.get("personaFallbackScenes"), list) or evidence["personaFallbackScenes"]):
        raise ValueError("Required persona still was unavailable; creative review is not complete")
    if expected_images:
        assets = evidence.get("licensedImageAssets")
        if not isinstance(assets, list) or len(assets) != expected_images:
            raise ValueError("Image attribution and provenance incomplete; release not permitted")
        for asset in assets:
            if not isinstance(asset, dict) or not all(asset.get(key) for key in ("credit", "author", "sourceUrl", "license", "title")):
                raise ValueError("Image attribution and provenance incomplete; release not permitted")
            if asset["credit"] not in pack.get("description", ""):
                raise ValueError("Image attribution missing from final YouTube description")
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
    if spec["channel"] == "10SecScientist" and not 8 <= duration <= 16:
        raise ValueError(f"10SecScientist branded short must run about ten seconds, not {duration:.1f}s")
    # Scene frames are quantized separately, so allow one video frame per scene.
    tolerance = 0.25 + len(spec["scenes"]) / 24
    if not math.isfinite(duration) or not math.isfinite(planned) or min(duration, planned) <= 0 or abs(duration - planned) > tolerance:
        raise ValueError("Media duration disagrees with the render pack")
    with Image.open(thumbnail) as image:
        if image.format != "JPEG":
            raise ValueError("Expected JPEG thumbnail")
        image.load()

    editorial_gate(spec)


def editorial_gate(spec: dict) -> None:
    """Check model critic evidence before any expensive rendering or release.

    This does not constitute human owner approval, but every model-generated
    episode needs documented validated critic scores. Earlier planning output
    with missing/null scores must not be rendered repeatedly on cron.
    """
    meta = spec.get("meta") or {}
    if meta.get("generator") != "autopilot":
        return
    review = meta.get("review") or {}
    if not isinstance(review, dict):
        raise ValueError("Unapproved Autopilot editorial review")
    for name, minimum in (("hook", 6), ("originality", 6), ("accuracy", 7)):
        score = review.get(name)
        if type(score) is not int or score < minimum or score > 10:
            raise ValueError(f"Unapproved Autopilot editorial score: {name}")
    if (review.get("pass") is not True
            or review.get("unsupported_claims") != []
            or review.get("fixes") != []):
        raise ValueError("Unapproved Autopilot editorial decision, fixes, or unsupported claims")


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
