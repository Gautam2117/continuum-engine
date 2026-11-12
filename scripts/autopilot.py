"""Autopilot entry point, run on a schedule by GitHub Actions (no laptop, no Claude, no human).

  plan   fill every channel's quota for today and the next days (default 3), so a 2-day buffer always exists
  learn  pull real analytics from Continuum Studio into autopilot/state/feedback.json
  heal   list specs that should have been rendered by now but have no release assets yet
"""
import argparse
import datetime as dt
import json
import os
import pathlib
import subprocess
import sys
import time
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from autopilot import daily, insights  # noqa: E402
from autopilot.llm import LLM  # noqa: E402


def emit(key: str, value: str) -> None:
    print(f"{key}={value}")
    if os.environ.get("GITHUB_OUTPUT"):
        with open(os.environ["GITHUB_OUTPUT"], "a") as f:
            f.write(f"{key}={value}\n")


def cmd_plan(a) -> int:
    now = dt.datetime.now(dt.timezone.utc)
    days = [now.date() + dt.timedelta(days=i) for i in range(a.days)]
    llm = LLM()
    beat = {"at": now.isoformat(timespec="seconds"), "days": [d.isoformat() for d in days], "llm": "none" if not llm.available else [p.name for p in llm.providers]}
    if not llm.available:
        print("No LLM key configured: skipping generation. Existing specs still render and publish.")
        beat["note"] = "no LLM key; nothing generated"
        insights.save("heartbeat.json", beat)
        emit("new", "")
        return 0
    result = daily.plan(days, llm, now, only=a.only or None, max_calls=a.max_calls)
    beat.update(written=len(result["written"]), failed=result["failed"][:20], calls=llm.calls, by_model=llm.by_provider)
    insights.save("heartbeat.json", beat)
    emit("new", " ".join(result["written"]))
    print(json.dumps({k: (v if k != "written" else len(v)) for k, v in result.items()}, indent=1))
    return 0


def cmd_learn(a) -> int:
    secret = os.environ.get("AUTOPILOT_SECRET", "")
    base = os.environ.get("STUDIO_URL", "https://studio.continuumarc.tech").rstrip("/")
    if not secret:
        print("AUTOPILOT_SECRET not set: skipping analytics pull")
        return 0
    req = urllib.request.Request(f"{base}/api/autopilot/feedback?days=60", headers={"authorization": f"Bearer {secret}", "user-agent": "continuum-engine"})
    try:
        with urllib.request.urlopen(req, timeout=90) as r:
            data = json.loads(r.read())
    except Exception as e:  # noqa: BLE001
        print(f"analytics pull failed: {e}")
        return 0  # never stops the factory
    insights.save("feedback.json", data)
    n = sum(len(c.get("videos", [])) for c in data.get("channels", []))
    print(f"feedback: {len(data.get('channels', []))} channels, {n} videos")
    return 0


def sh(*args) -> str:
    return subprocess.run(args, capture_output=True, text=True).stdout


def cmd_heal(a) -> int:
    today = dt.date.today()
    cache: dict[str, set] = {}
    todo = []
    for p in sorted((ROOT / "specs").glob("*/*.json")):
        try:
            day = dt.date.fromisoformat(p.parent.name)
        except ValueError:
            continue
        if day < today - dt.timedelta(days=1):
            continue
        age_min = (time.time() - int(sh("git", "log", "-1", "--format=%ct", "--", str(p)).strip() or time.time())) / 60
        if age_min < 150:  # give a render in progress time to finish
            continue
        tag = p.parent.name
        if tag not in cache:
            r = subprocess.run(["gh", "release", "view", tag, "--json", "assets"], capture_output=True, text=True)
            if r.returncode == 0:
                cache[tag] = {x["name"] for x in json.loads(r.stdout)["assets"]}
            elif "not found" in r.stderr.lower():
                cache[tag] = set()  # no release yet: nothing rendered for that day
            else:
                cache[tag] = None  # GitHub unreachable: assume nothing, start nothing
        if cache[tag] is None:
            continue
        sid = json.loads(p.read_text())["id"]
        if f"{sid}-pack.json" not in cache[tag]:
            todo.append(str(p.relative_to(ROOT)))
    emit("heal", " ".join(todo))
    return 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("plan")
    p.add_argument("--days", type=int, default=3)
    p.add_argument("--only", action="append")
    p.add_argument("--max-calls", type=int, default=int(os.environ.get("AUTOPILOT_MAX_CALLS", "400")))
    p.set_defaults(fn=cmd_plan)
    sub.add_parser("learn").set_defaults(fn=cmd_learn)
    sub.add_parser("heal").set_defaults(fn=cmd_heal)
    args = ap.parse_args()
    sys.exit(args.fn(args))
