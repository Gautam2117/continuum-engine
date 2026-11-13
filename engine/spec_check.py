"""One place that decides whether a spec is fit to render. Used by scripts/validate.py and by the Autopilot."""
import re

from .scenes import SCENES
from .styles import CHANNEL_STYLE

REQUIRED = {"title": ["text"], "number": ["value"], "bars": ["items"], "orbit": ["ratio"], "fall": ["items"],
            "list": ["items"], "timeline": ["events"], "verdict": ["scores"], "image": [], "persona": ["who"], "b3d": ["scene"]}
PLACEHOLDER = re.compile(r"lorem|todo|tbd|\[[^\]]*\]|\{[^}]*\}|as an ai|insert ", re.I)
WPM = 150


def narration_words(spec: dict) -> int:
    return sum(len(sc.get("say", "").split()) for sc in spec.get("scenes", []))


def problems(spec: dict, folder: str | None = None, *, strict: bool = False) -> list[str]:
    """Return human-readable problems. strict=True adds the Autopilot's quality gates."""
    out: list[str] = []
    for k in ("id", "channel", "format", "title", "description", "scenes"):
        if k not in spec:
            out.append(f"missing {k}")
    if out:
        return out
    if spec["channel"] not in CHANNEL_STYLE:
        out.append(f"unknown channel {spec['channel']!r}")
    fmt = spec["format"]
    if fmt not in ("long", "short"):
        out.append("format must be long or short")
    if len(spec["title"]) > 100:
        out.append("title over 100 characters")
    if folder and not spec["id"].startswith(folder):
        out.append("id should start with its date folder")
    scenes = spec["scenes"]
    for i, sc in enumerate(scenes):
        show = sc.get("show") or {"type": "say"}
        t = show.get("type")
        if t not in SCENES:
            out.append(f"scene {i}: unknown type {t!r}")
            continue
        for f in REQUIRED.get(t, []):
            if f not in show:
                out.append(f"scene {i}: {t} needs {f}")
        if t == "image" and not (show.get("query") or show.get("image_url")):
            out.append(f"scene {i}: image needs query or image_url")
        if t == "b3d":
            from .b3d import SCENE_NAMES
            if show.get("scene") not in SCENE_NAMES:
                out.append(f"scene {i}: unknown 3D scene {show.get('scene')!r}")
            fb = (show.get("fallback") or {}).get("type")
            if fb and fb not in SCENES:
                out.append(f"scene {i}: unknown fallback type {fb!r}")
        if t == "bars" and len(show.get("items", [])) < 2:
            out.append(f"scene {i}: bars needs at least 2 items")
        if strict and PLACEHOLDER.search(sc.get("say", "")):
            out.append(f"scene {i}: placeholder-looking text in narration")
    words = narration_words(spec)
    minutes = words / WPM
    if fmt == "short" and minutes > 0.95:
        out.append(f"short narration too long (~{minutes * 60:.0f}s; keep under ~55s)")
    if fmt == "long" and minutes < (6.5 if strict else 3):
        out.append(f"long-form narration only ~{minutes:.1f} min; aim for 8+")
    if strict:
        if fmt == "short":
            if words < 60:
                out.append(f"short too thin ({words} words; aim 80 to 130)")
            if len(scenes) < 6:
                out.append("short needs at least 6 scenes for pacing")
            first = scenes[0].get("say", "") if scenes else ""
            if len(first.split()) > 18:
                out.append("opening line too long to hook; keep under 18 words")
        else:
            if len(scenes) < 18:
                out.append("long-form needs at least 18 scenes for visual variety")
        kinds = [(sc.get("show") or {}).get("type", "say") for sc in scenes]
        run = best = 1
        for a, b in zip(kinds, kinds[1:]):
            run = run + 1 if a == b else 1
            best = max(best, run)
        if best > 3 and fmt == "short" or best > 5:
            out.append("too many identical scene types in a row; vary the visuals")
        if scenes and (scenes[-1].get("show") or {}).get("type") != "end":
            out.append("last scene should be an end card")
        if not spec.get("tags"):
            out.append("needs tags")
        if len(spec.get("description", "")) < 120:
            out.append("description too short (needs sources and context)")
    return out
