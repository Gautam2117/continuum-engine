"""Check specs before pushing: known channel, known scene types, required fields, sane lengths.
Usage: python3 scripts/validate.py [--strict] specs/2026-11-14/*.json"""
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from engine.spec_check import problems  # noqa: E402

args = [a for a in sys.argv[1:] if a != "--strict"]
strict = "--strict" in sys.argv
errors = 0
ids: set = set()
for path in map(pathlib.Path, args):
    try:
        s = json.loads(path.read_text())
    except Exception as e:  # noqa: BLE001
        print(f"{path}: not JSON ({e})"); errors += 1; continue
    for p in problems(s, path.parent.name, strict=strict):
        errors += 1
        print(f"{path}: {p}")
    if s.get("id") in ids:
        errors += 1; print(f"{path}: duplicate id")
    ids.add(s.get("id"))
print("ok" if not errors else f"{errors} problem(s)")
sys.exit(1 if errors else 0)
