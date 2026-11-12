"""Check specs before pushing: known channel, known scene types, required fields, sane lengths.
Usage: python3 scripts/validate.py specs/2026-11-14/*.json"""
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from engine.scenes import SCENES  # noqa: E402
from engine.styles import CHANNEL_STYLE  # noqa: E402

REQUIRED = {"title": ["text"], "number": ["value"], "bars": ["items"], "orbit": ["ratio"], "fall": ["items"],
            "list": ["items"], "timeline": ["events"], "verdict": ["scores"], "image": []}
errors = 0
ids = set()
for path in map(pathlib.Path, sys.argv[1:]):
    try:
        s = json.loads(path.read_text())
    except Exception as e:  # noqa: BLE001
        print(f"{path}: not JSON ({e})"); errors += 1; continue
    def bad(msg):
        global errors
        errors += 1
        print(f"{path}: {msg}")
    for k in ("id", "channel", "format", "title", "description", "scenes"):
        if k not in s:
            bad(f"missing {k}")
    if s.get("id") in ids:
        bad("duplicate id")
    ids.add(s.get("id"))
    if s.get("channel") not in CHANNEL_STYLE:
        bad(f"unknown channel {s.get('channel')!r}")
    if s.get("format") not in ("long", "short"):
        bad("format must be long or short")
    if len(s.get("title", "")) > 100:
        bad("title over 100 characters")
    if not s.get("id", "").startswith(path.parent.name):
        bad("id should start with its date folder")
    words = 0
    for i, sc in enumerate(s.get("scenes", [])):
        show = sc.get("show") or {"type": "say"}
        t = show.get("type")
        if t not in SCENES:
            bad(f"scene {i}: unknown type {t!r}")
        for f in REQUIRED.get(t, []):
            if f not in show:
                bad(f"scene {i}: {t} needs {f}")
        if t == "image" and not (show.get("query") or show.get("image_url")):
            bad(f"scene {i}: image needs query or image_url")
        words += len(sc.get("say", "").split())
    minutes = words / 150
    if s.get("format") == "short" and minutes > 0.95:
        bad(f"short narration too long (~{minutes * 60:.0f}s; keep under ~55s)")
    if s.get("format") == "long" and minutes < 3:
        bad(f"long-form narration only ~{minutes:.1f} min; aim for 8+")
print("ok" if not errors else f"{errors} problem(s)")
sys.exit(1 if errors else 0)
