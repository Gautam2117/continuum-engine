"""Continuum's single-host daily private-production supervisor.

Observes all 48 individual channel targets and the real render queue. Runs
bounded planning only with explicitly approved zero-cost model credentials;
never weakens original-media, editorial, review, OAuth, or publishing gates.
One command invocation is suitable for launchd/systemd and fail-safe restarts.

A deployment on the owner's Mac is temporary. This script cannot turn that Mac
into an independent off-Mac host and never claims an upload occurred.
"""
from __future__ import annotations

import argparse
import contextlib
import datetime as dt
import fcntl
import json
import os
import pathlib
import sqlite3
import shutil
import signal
import subprocess
import sys
import tempfile
import time
from collections import Counter

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from autopilot.playbooks import PLAYBOOKS, cadence_for
from autopilot import daily
from scripts import worker

UTC = dt.timezone.utc
FMT = ("short", "long")
EXPECTED_CHANNELS = 48
ATLAS = "Counterfactual Atlas"
RELEASE_STATE = "PRIVATE_REVIEW_NOT_APPROVED"


def now_utc() -> dt.datetime:
    return dt.datetime.now(UTC)


def write_atomic(path: pathlib.Path, obj: dict) -> None:
    """Safely replace a single JSON heartbeat; never leak credentials."""
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = (json.dumps(obj, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode()
    fd, name = tempfile.mkstemp(prefix=".supervisor-", dir=path.parent)
    try:
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, "wb") as dst:
            dst.write(payload)
            dst.flush()
            os.fsync(dst.fileno())
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


@contextlib.contextmanager
def singleton(state: pathlib.Path):
    """Do not overlap planning cycles, even if the prior render is still active."""
    lock = state / "supervisor.lock"
    state.mkdir(parents=True, exist_ok=True)
    with lock.open("a+") as fd:
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise RuntimeError("Supervisor already running; skipping duplicate tick") from exc
        try:
            yield
        finally:
            fcntl.flock(fd, fcntl.LOCK_UN)


def target(day: dt.date) -> dict[str, dict[str, int]]:
    if len(PLAYBOOKS) != EXPECTED_CHANNELS or ATLAS not in PLAYBOOKS:
        raise RuntimeError("48-channel registry is incomplete; stop rather than silently shrinking target")
    out = {channel: cadence_for(channel, day) for channel in PLAYBOOKS}
    for channel, formats in out.items():
        count = sum(formats.values())
        expected = 3 if channel == ATLAS else 1
        if count != expected or any(formats.get(fmt, 0) < 0 for fmt in FMT):
            raise RuntimeError(f"Daily cadence mismatch for {channel}: {formats}")
    if sum(sum(c.values()) for c in out.values()) != 50:
        raise RuntimeError("Daily network target must remain 50 videos")
    return out


def supply(path: pathlib.Path, day: dt.date) -> tuple[dict[tuple[str, str], set[str]],
                                                        dict[tuple[str, str], set[str]],
                                                        list[dict], list[dict]]:
    """An invalid or misdated JSON spec never counts as delivered supply."""
    found: dict[tuple[str, str], set[str]] = {}
    eligible: dict[tuple[str, str], set[str]] = {}
    errors: list[dict] = []
    held: list[dict] = []
    folder = path / day.isoformat()
    for file in sorted(folder.glob("*.json")):
        try:
            obj = json.loads(file.read_text())
            if not isinstance(obj, dict):
                raise ValueError("expected spec object")
            identity = f"{day.isoformat()}-{file.stem}"
            channel, fmt = obj.get("channel"), obj.get("format")
            if (obj.get("id") != identity or channel not in PLAYBOOKS or fmt not in FMT
                    or not isinstance(obj.get("scenes"), list) or not obj["scenes"]):
                raise ValueError("invalid channel, format, identity, or scenes")
            from engine.spec_check import problems
            issues = problems(obj, day.isoformat(), strict=True)
            if issues:
                raise ValueError("; ".join(issues[:2]))
            found.setdefault((channel, fmt), set()).add(identity)
            # Separate a script that is syntactically valid from a script that
            # has the required model-editor evidence to consume render CPU.
            from scripts.verify_review import editorial_gate
            try:
                editorial_gate(obj)
            except ValueError as hold:
                held.append({"id": identity, "channel": channel,
                             "reason": str(hold)[:240]})
            else:
                eligible.setdefault((channel, fmt), set()).add(identity)
        except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
            errors.append({"file": str(file.relative_to(path)), "reason": str(exc)[:240]})
    return found, eligible, errors, held


def queue_stats(db_path: pathlib.Path) -> dict:
    if not db_path.exists():
        return {"configured": False, "states": {}, "channelsVerified": 0,
                "verifiedEpisodes": 0, "blockedEpisodes": 0}
    try:
        with sqlite3.connect(f"file:{db_path}?mode=ro", uri=True, timeout=3) as conn:
            counts = dict(conn.execute("SELECT state,COUNT(*) FROM jobs GROUP BY state").fetchall())
            verified = conn.execute("SELECT COUNT(DISTINCT spec_id) FROM jobs WHERE state='verified'").fetchone()[0]
            channels = conn.execute("SELECT COUNT(DISTINCT channel) FROM jobs WHERE state='verified'").fetchone()[0]
            blocked = counts.get("blocked", 0)
    except (sqlite3.Error, OSError) as exc:
        return {"configured": True, "databaseError": type(exc).__name__, "states": {}}
    return {"configured": True, "states": counts, "channelsVerified": channels,
            "verifiedEpisodes": verified, "blockedEpisodes": blocked}


def snapshot(specs: pathlib.Path, db: pathlib.Path, *, today: dt.date | None = None,
             days: int = 3) -> dict:
    if not 1 <= days <= 14:
        raise ValueError("Audit horizon must be 1 through 14 days")
    today = today or now_utc().date()
    rows = []
    bad = []
    total = supplied = renderable = 0
    holds: list[dict] = []
    overquota: list[dict] = []
    per_channel = {c: {"target": 0, "validSpecs": 0, "missing": 0} for c in PLAYBOOKS}
    for delta in range(days):
        date = today + dt.timedelta(days=delta)
        desired = target(date)
        actual, eligible, errors, blocked = supply(specs, date)
        bad.extend(errors)
        holds.extend(blocked)
        for channel, formats in desired.items():
            for fmt, want in formats.items():
                if not want:
                    continue
                count = len(actual.get((channel, fmt), set()))
                have = min(want, count)
                can_render = min(want, len(eligible.get((channel, fmt), set())))
                if count > want:
                    overquota.append({"date": date.isoformat(), "channel": channel,
                                      "format": fmt, "extra": count - want})
                miss = want - have
                per_channel[channel]["target"] += want
                per_channel[channel]["validSpecs"] += have
                per_channel[channel]["missing"] += miss
                total += want
                supplied += have
                renderable += can_render
                if miss:
                    rows.append({"date": date.isoformat(), "channel": channel, "format": fmt,
                                 "required": want, "available": have, "missing": miss})
    return {
        "schemaVersion": 1, "observedAt": now_utc().isoformat(), "periodStart": today.isoformat(),
        "days": days, "channels": EXPECTED_CHANNELS, "requiredEpisodes": total,
        "validSpecs": supplied, "missingSpecs": total - supplied,
        "renderEligibleSpecs": renderable, "missingRenderReady": total - renderable,
        "editorialHolds": holds[:200], "editorialHoldCount": len(holds),
        "overquota": overquota[:200], "overquotaCount": len(overquota),
        "missingByChannel": rows, "channelsDetail": per_channel,
        "invalidSpecs": bad[:200], "invalidSpecCount": len(bad),
        "worker": queue_stats(db), "publishing": RELEASE_STATE,
        "offMacHostProvisioned": False,
        "fullyAutonomous": False,
    }


def awake_argv(argv: list[str]) -> list[str]:
    """Prevent idle sleep only while an active Mac work step is executing.

    This cannot prevent shutdown, closed-lid sleep or power loss and is never
    used on Linux/cloud workers. The wrapper inherits the process group so
    the supervisor's timeout can still terminate the entire workload.
    """
    if sys.platform != "darwin":
        return argv
    caffeinate = shutil.which("caffeinate")
    return [caffeinate, "-i", *argv] if caffeinate else argv


def run_command(argv: list[str], *, timeout: int, log: pathlib.Path,
                env: dict[str, str] | None = None) -> dict:
    """Never a shell, never logs environment values or model API credentials."""
    log.parent.mkdir(parents=True, exist_ok=True)
    t0 = time.monotonic()
    try:
        with log.open("a", encoding="utf-8") as output:
            proc = subprocess.Popen(awake_argv(argv), cwd=ROOT, stdin=subprocess.DEVNULL,
                                    stdout=output, stderr=subprocess.STDOUT,
                                    start_new_session=True, env=env)
            try:
                ret = proc.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                # The worker may have started Blender/ffmpeg children. Killing
                # only its parent would leave unbounded orphan CPU processes.
                try:
                    os.killpg(proc.pid, signal.SIGTERM)
                except ProcessLookupError:
                    pass
                try:
                    proc.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    try:
                        os.killpg(proc.pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
                    proc.wait()
                return {"exit": 124, "elapsedSec": round(time.monotonic()-t0, 1),
                        "error": "step timed out; process group terminated"}
        return {"exit": ret, "elapsedSec": round(time.monotonic()-t0, 1)}
    except OSError as exc:
        return {"exit": 127, "error": type(exc).__name__}


def allowed_planner() -> tuple[bool, str]:
    """A provider credential never implies authorization to incur a bill."""
    from autopilot.llm import LLM
    # A localhost-only Ollama model makes no paid network API calls.
    # Other providers still require explicit independent zero-cost confirmation.
    if os.environ.get("CONTINUUM_LLM_LOCAL_ONLY") == "1":
        if not os.environ.get("OLLAMA_MODEL"):
            return False, "local model not configured"
        providers = LLM()
        if not (providers.available and all(p.name == "ollama" for p in providers.providers)):
            return False, "local-only provider guard refused remote models"
        # Check the exact model is installed and the local server is actually
        # reachable. A stale named model must not trigger a 34-minute retry loop.
        import urllib.request
        try:
            req = urllib.request.Request("http://127.0.0.1:11434/api/tags",
                                         headers={"User-Agent": "continuum-preflight"})
            opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
            with opener.open(req, timeout=3) as response:
                available = json.load(response)
            names = {item.get("name") for item in available.get("models", [])}
        except (OSError, ValueError, KeyError) as exc:
            return False, f"local model server unavailable ({type(exc).__name__})"
        if os.environ["OLLAMA_MODEL"] not in names:
            return False, "configured local model is not installed"
        return True, "verified on-device draft model; no remote API or autonomous editorial approval"
    if os.environ.get("CONTINUUM_ZERO_COST_LLM_CONFIRMED") != "1":
        return False, "zero-cost LLM use is not explicitly confirmed on this host"
    providers = LLM()
    if not providers.available:
        return False, "no configured language model provider"
    return True, "configured provider and separate zero-cost authorization present"


def next_queued_job_needs_blender(db_path: pathlib.Path, channel: str | None = None) -> bool:
    """Probe Blender only for the next *eligible* persisted 3D render.

    A new 3D spec discovered during scan still goes through native renderer and
    strict render-evidence verification. Unknown/invalid queue entries fail
    conservatively, but no eligible job means no expensive Blender probe.
    """
    if not db_path.is_file():
        return False
    try:
        with sqlite3.connect(f"file:{db_path.resolve()}?mode=ro", uri=True, timeout=3) as conn:
            query = "SELECT spec_path FROM jobs WHERE state IN ('queued','retry') AND eligible_at<=?"
            params: list[str] = [now_utc().isoformat()]
            if channel:
                query += " AND channel=?"
                params.append(channel)
            row = conn.execute(query + " ORDER BY eligible_at,job_key LIMIT 1", params).fetchone()
        if not row:
            return False
        spec_path = worker.spec_file(pathlib.Path(row[0]))
        spec = json.loads(spec_path.read_text())
        return any((scene.get("show") or {}).get("type") == "b3d"
                   for scene in spec.get("scenes", []) if isinstance(scene, dict))
    except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError, sqlite3.Error):
        return True


def cycle(args) -> dict:
    state = args.state.resolve()
    # The owner may choose one channel without stopping or destroying the
    # other 47 channels' specs, job receipts, or required coverage counters.
    focus_file = state / "focus_channel.txt"
    focus = args.focus_channel or os.environ.get("CONTINUUM_FOCUS_CHANNEL", "").strip()
    if not focus and focus_file.is_file():
        focus = focus_file.read_text(encoding="utf-8").strip()
    if focus and focus not in PLAYBOOKS:
        raise ValueError("Unknown focus channel; refuses unattended planner/render mutation")
    specs = args.specs.resolve()
    spool_env = {**os.environ, "CONTINUUM_SPEC_DIR": str(specs)}
    review_db = args.db.resolve()
    review_dir = args.reviews.resolve()
    started = now_utc()
    steps: dict = {}
    with singleton(state):
        if args.render:
            # A gate before any expensive rendering. Rendering is private only.
            from scripts.worker import preflight
            before = preflight(review_db, review_dir, require_blender=(
                args.require_blender and next_queued_job_needs_blender(review_db,focus or None)))
            if not before["ready"]:
                steps["render"] = {"status": "not-run", "reason": "preflight requirements unavailable",
                                   "preflight": before}
            elif shutil.disk_usage(review_dir).free < args.min_free_gib * (1024 ** 3):
                free_bytes = shutil.disk_usage(review_dir).free
                steps["render"] = {"status": "not-run", "reason": "disk space safety reserve",
                                   "freeGiB": round(free_bytes / 1024**3, 1),
                                   "requiredGiB": args.min_free_gib}
            else:
                steps["render"] = run_command(
                    [sys.executable, str(ROOT / "scripts/worker.py"), "cycle",
                     "--days", str(args.days + 1), "--start-offset", "0",
                     "--db", str(review_db), "--reviews", str(review_dir),
                     "--limit", str(args.render_limit), "--timeout", str(args.render_timeout)]
                    + (["--channel", focus] if focus else []),
                    timeout=args.render_timeout * args.render_limit + 120,
                    log=state/"render.log", env=spool_env)
        if args.plan:
            ok, message = allowed_planner()
            if ok:
                steps["plan"] = run_command(
                    [sys.executable, str(ROOT / "scripts/autopilot.py"), "plan",
                     "--days", str(args.days), "--start-offset", "1",
                     "--max-calls", str(args.max_calls)]
                    + (["--only", focus] if focus else []),
                    timeout=args.plan_timeout, log=state/"planner.log", env=spool_env)
            else:
                steps["plan"] = {"status": "not-run", "reason": message}
        archive_root = os.environ.get("CONTINUUM_ARCHIVE_ROOT", "").strip()
        if archive_root:
            if os.environ.get("CONTINUUM_ARCHIVE_MOUNT_ENCRYPTED") != "1":
                steps["archive"] = {"status": "not-run", "reason": "trusted encrypted mount not confirmed"}
            else:
                steps["archive"] = run_command(
                    [sys.executable, str(ROOT / "scripts/archive_verified_reviews.py"),
                     "--db", str(review_db), "--reviews", str(review_dir),
                     "--destination", archive_root, "--confirm-trusted-mount"],
                    timeout=1800, log=state/"archive.log")
        result = snapshot(specs, review_db, today=started.date(), days=args.days)
        result["steps"] = steps
        result["productionFocus"] = focus or "all-48"
        result["supervisorHost"] = "owner-computer"  # never claim independent VM
        write_atomic(state/"latest.json", result)
    return result


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="48-channel private production supervisor, no public upload")
    p.add_argument("action", choices=["status", "cycle"])
    p.add_argument("--specs", type=pathlib.Path, default=daily.SPECS)
    p.add_argument("--state", type=pathlib.Path, default=ROOT/"var"/"supervisor")
    p.add_argument("--db", type=pathlib.Path, default=ROOT/"var"/"worker.sqlite3")
    p.add_argument("--reviews", type=pathlib.Path, default=ROOT/"var"/"reviews")
    p.add_argument("--days", type=int, default=3)
    p.add_argument("--plan", action="store_true", help="Generate missing future specs only with confirmed zero-cost LLM provider")
    p.add_argument("--focus-channel", type=str, help="Focus actual planning and rendering while continuing to audit all 48")
    p.add_argument("--render", action="store_true", help="Bounded private render-review queue")
    p.add_argument("--require-blender", action="store_true", help="Require actual Blender before rendering")
    p.add_argument("--render-limit", type=int, default=1)
    p.add_argument("--render-timeout", type=int, default=7200)
    p.add_argument("--plan-timeout", type=int, default=2200)
    p.add_argument("--max-calls", type=int, default=100)
    p.add_argument("--min-free-gib", type=int, default=20,
                   help="Do not begin new heavy renders below this free disk reserve")
    return p


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    if (not 1 <= args.days <= 14 or not 1 <= args.render_limit <= 4
            or not 60 <= args.render_timeout <= 21600
            or not 60 <= args.plan_timeout <= 3600 or not 1 <= args.max_calls <= 400
            or not 2 <= args.min_free_gib <= 1024):
        raise SystemExit("Invalid horizon, render cap or time budget")
    if args.focus_channel and args.focus_channel not in PLAYBOOKS:
        raise SystemExit("Unknown --focus-channel")
    if args.action == "status" and (args.plan or args.render):
        raise SystemExit("status is read-only: --plan and --render require cycle")
    report = (snapshot(args.specs.resolve(), args.db.resolve(), days=args.days)
              if args.action == "status" else cycle(args))
    compact = {key:report[key] for key in ("observedAt", "channels", "days", "requiredEpisodes",
                         "validSpecs", "missingSpecs", "renderEligibleSpecs", "missingRenderReady",
                         "editorialHoldCount", "overquotaCount", "invalidSpecCount", "worker",
                         "publishing", "offMacHostProvisioned", "fullyAutonomous")}
    if args.action == "cycle":
        compact["steps"] = report.get("steps")
    print(json.dumps(compact, indent=2))
    return 0 if not report["invalidSpecCount"] and not any(
        isinstance(s,dict) and s.get("exit",0) != 0 for s in report.get("steps",{}).values()) else 2


if __name__ == "__main__":
    raise SystemExit(main())
