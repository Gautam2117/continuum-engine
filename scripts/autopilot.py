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
    unknown = sorted(set(a.only or ()) - daily.PLAYBOOKS.keys())
    if unknown:
        print(f"Unknown or creator-led channels: {', '.join(unknown)}", file=sys.stderr)
        return 2
    if not 1 <= a.days <= 30 or not 0 <= a.start_offset <= 30:
        print("Choose 1–30 days and a start offset of 0–30 days.", file=sys.stderr)
        return 2
    now = dt.datetime.now(dt.timezone.utc)
    start = now.date() + dt.timedelta(days=a.start_offset)
    days = [start + dt.timedelta(days=i) for i in range(a.days)]
    llm = LLM()
    beat = {"at": now.isoformat(timespec="seconds"), "days": [d.isoformat() for d in days], "llm": "none" if not llm.available else [p.name for p in llm.providers]}
    if not llm.available:
        print("No LLM key configured: skipping generation. Existing specs still render and publish.")
        beat["note"] = "no LLM key; nothing generated"
        insights.save("heartbeat.json", beat)
        emit("new", "")
        return 0
    for pv in llm.providers:
        print(f"llm provider {pv.name}: best={getattr(pv, 'best', [])} bulk={pv.models}")
    started = time.monotonic()
    result = daily.plan(days, llm, now, only=a.only or None, max_calls=a.max_calls)
    beat.update(written=len(result["written"]), failed=result["failed"][:20], calls=llm.calls, by_model=llm.by_provider,
                attempts_by_model=llm.attempts_by_model, planning_seconds=round(time.monotonic() - started, 2))
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
    cache: dict[str, set[str] | None] = {}
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
        required = {f"{sid}-{suffix}" for suffix in ("video.mp4", "thumb.jpg", "pack.json")}
        if not required.issubset(cache[tag]):
            todo.append(str(p.relative_to(ROOT)))
    emit("heal", " ".join(todo))
    return 0


def cmd_register(a) -> int:
    """Add hand- or Claude-written specs to the ledger so their results feed the learning loop."""
    from autopilot.slots import slot_key
    ledger = insights.load("ledger.json", [])
    known = {e["id"] for e in ledger}
    n = 0
    for f in a.files:
        s = json.loads(pathlib.Path(f).read_text())
        if s["id"] in known:
            continue
        when = dt.datetime.fromisoformat(s["publishAt"].replace("Z", "+00:00")) if s.get("publishAt") else None
        ledger.append({"id": s["id"], "channel": s["channel"], "format": s["format"], "title": s["title"], "axis": (s.get("meta") or {}).get("axis", "claude-written"), "slot": slot_key(when) if when else "", "publishAt": s.get("publishAt")})
        n += 1
    insights.save("ledger.json", ledger[-1500:])
    print(f"registered {n} spec(s)")
    return 0


def cmd_slots(a) -> int:
    """Best publish times for a channel on a date, as ISO UTC lines (used by Claude-written specs too)."""
    from autopilot.playbooks import PLAYBOOKS, cadence_for
    from autopilot.slots import choose
    now = dt.datetime.now(dt.timezone.utc)
    day = dt.date.fromisoformat(a.date)
    n = a.count or cadence_for(a.channel, day)[a.format]
    for when in choose(a.channel, a.format, n, day, insights.slot_stats(a.channel, a.format), now, min_lead_h=a.lead):
        print(when.strftime("%Y-%m-%dT%H:%M:00Z"))
    return 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("plan")
    p.add_argument("--days", type=int, default=3)
    p.add_argument("--start-offset", type=int, default=0)
    p.add_argument("--only", action="append")
    p.add_argument("--max-calls", type=int, default=int(os.environ.get("AUTOPILOT_MAX_CALLS", "400")))
    p.set_defaults(fn=cmd_plan)
    sub.add_parser("learn").set_defaults(fn=cmd_learn)
    sub.add_parser("heal").set_defaults(fn=cmd_heal)
    r = sub.add_parser("register")
    r.add_argument("files", nargs="+")
    r.set_defaults(fn=cmd_register)
    q = sub.add_parser("slots")
    q.add_argument("--channel", required=True)
    q.add_argument("--format", required=True, choices=["long", "short"])
    q.add_argument("--date", required=True)
    q.add_argument("--count", type=int, default=0)
    q.add_argument("--lead", type=float, default=4.5)
    q.set_defaults(fn=cmd_slots)
    args = ap.parse_args()
    sys.exit(args.fn(args))
