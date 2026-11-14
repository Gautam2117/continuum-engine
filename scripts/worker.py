"""Durable local render-review worker for an owned machine or compliant VM.

No public uploads, paid API calls or GitHub Actions dispatches occur here.
All jobs are one at a time on one host; SQLite persists state across crashes.
"""
from __future__ import annotations

import argparse
import datetime as dt
import fcntl
import hashlib
import json
import os
import pathlib
import re
import signal
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import time
from contextlib import closing, contextmanager
from importlib.util import find_spec

ROOT = pathlib.Path(__file__).resolve().parents[1]
SPEC_ROOT = pathlib.Path(os.environ.get("CONTINUUM_SPEC_DIR") or (ROOT / "specs")).resolve()
sys.path.insert(0, str(ROOT))
SCHEMA = """
CREATE TABLE IF NOT EXISTS jobs (
  job_key TEXT PRIMARY KEY,
  spec_id TEXT NOT NULL,
  spec_path TEXT NOT NULL,
  spec_sha256 TEXT NOT NULL,
  channel TEXT NOT NULL,
  format TEXT NOT NULL,
  state TEXT NOT NULL CHECK(state IN ('queued','running','retry','verified','blocked','superseded')),
  attempt INTEGER NOT NULL DEFAULT 0 CHECK(attempt >= 0),
  eligible_at TEXT NOT NULL,
  started_at TEXT,
  updated_at TEXT NOT NULL,
  duration_sec REAL,
  mp4_sha256 TEXT,
  review_path TEXT,
  last_error TEXT
);
CREATE INDEX IF NOT EXISTS jobs_by_state ON jobs(state, eligible_at);
"""
VALID_SPEC = re.compile(r"\d{4}-\d{2}-\d{2}/[a-z0-9-]+\.json\Z")


def utcnow() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


def iso(when: dt.datetime) -> str:
    return when.astimezone(dt.timezone.utc).isoformat(timespec="seconds")


def digest(path: pathlib.Path) -> str:
    with path.open("rb") as source:
        return hashlib.file_digest(source, "sha256").hexdigest()


@contextmanager
def single_worker(db_path: pathlib.Path):
    """Prevent concurrent memory/CPU-heavy renders on one host.

    SQLite claim protects each row; POSIX flock additionally protects the
    machine from two different jobs rendering concurrently.
    """
    lockfile = db_path.with_name(db_path.name + ".render.lock")
    lockfile.parent.mkdir(parents=True, exist_ok=True)
    with lockfile.open("a+") as handle:
        try:
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as error:
            raise RuntimeError("Another worker owns the render lock; no parallel job started") from error
        try:
            yield
        finally:
            fcntl.flock(handle, fcntl.LOCK_UN)


def future_specs(*, today: dt.date | None = None, days: int = 7, start_offset: int = 0) -> list[pathlib.Path]:
    """Never accidentally render historical content from a repo-wide scan."""
    if not 1 <= days <= 30 or not 0 <= start_offset <= 30:
        raise ValueError("days must be 1-30 and start offset 0-30")
    today = today or utcnow().date()
    start, end = today + dt.timedelta(days=start_offset), today + dt.timedelta(days=start_offset + days - 1)
    paths = []
    for path in sorted(SPEC_ROOT.glob("*/*.json")):
        try:
            day = dt.date.fromisoformat(path.parent.name)
        except ValueError:
            continue
        if start <= day <= end:
            paths.append(path)
    return paths


def connection(db_path: pathlib.Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(db_path, timeout=20)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA journal_mode=WAL")
    db.execute("PRAGMA busy_timeout=20000")
    db.executescript(SCHEMA)
    return db


def spec_file(path: pathlib.Path) -> pathlib.Path:
    path = path.resolve(strict=True)
    if not path.is_file() or not path.is_relative_to(SPEC_ROOT.resolve()):
        raise ValueError("Spec is outside the configured specs directory")
    relative = path.relative_to(SPEC_ROOT.resolve()).as_posix()
    if not VALID_SPEC.fullmatch(relative):
        raise ValueError("Spec must have a specs/YYYY-MM-DD/<slug>.json path")
    data = json.loads(path.read_text())
    if not isinstance(data, dict) or data.get("id") != f"{path.parent.name}-{path.stem}":
        raise ValueError("Spec ID and path mismatch")
    if data.get("format") not in {"short", "long"} or not isinstance(data.get("channel"), str):
        raise ValueError("Missing valid channel or format")
    return path


def enqueue(db: sqlite3.Connection, files: list[pathlib.Path], *, now: dt.datetime | None = None) -> dict:
    now = now or utcnow()
    imported = invalid = already = 0
    for candidate in files:
        try:
            path = spec_file(candidate)
            spec = json.loads(path.read_text())
            sha = digest(path)
        except (ValueError, OSError, json.JSONDecodeError):
            invalid += 1
            continue
        job_key = f"{spec['id']}:{sha}"
        # Do not let stale queued revisions compete with the currently edited
        # spec. Preserve verified and running receipts for audit.
        db.execute("UPDATE jobs SET state='superseded',updated_at=? "
                   "WHERE spec_id=? AND spec_sha256<>? AND state IN ('queued','retry')",
                   (iso(now), spec["id"], sha))
        result = db.execute(
            "INSERT OR IGNORE INTO jobs (job_key,spec_id,spec_path,spec_sha256,channel,format,state,eligible_at,updated_at) "
            "VALUES (?,?,?,?,?,?,?,?,?)",
            (job_key, spec["id"], str(path), sha, spec["channel"], spec["format"], "queued", iso(now), iso(now)),
        )
        if not result.rowcount:
            # A checkout can restore earlier bytes after a revision was queued.
            # Only reactivate superseded work. Verified and blocked rows retain their receipts.
            result = db.execute(
                "UPDATE jobs SET state='queued',attempt=0,eligible_at=?,started_at=NULL,updated_at=?,last_error=NULL "
                "WHERE job_key=? AND state='superseded'", (iso(now), iso(now), job_key),
            )
        if result.rowcount:
            imported += 1
        else:
            already += 1
    db.commit()
    return {"imported": imported, "existing": already, "invalid": invalid}


def recover_stale(db: sqlite3.Connection, now: dt.datetime, *, max_age_hours: float = 4) -> int:
    cutoff = iso(now - dt.timedelta(hours=max_age_hours))
    updated = db.execute(
        "UPDATE jobs SET state='retry',eligible_at=?,updated_at=?,last_error='Recovered stale worker lease' "
        "WHERE state='running' AND started_at < ?", (iso(now), iso(now), cutoff),
    )
    db.commit()
    return updated.rowcount


def claim(db: sqlite3.Connection, now: dt.datetime | None = None, *,
          window: tuple[dt.date, dt.date] | None = None, job_key: str | None = None) -> dict | None:
    now = now or utcnow()
    db.execute("BEGIN IMMEDIATE")
    sql = "SELECT * FROM jobs WHERE state IN ('queued','retry') AND eligible_at <= ?"
    params = [iso(now)]
    if job_key is not None:
        sql += " AND job_key = ?"
        params.append(job_key)
    if window is not None:
        start, end = window
        sql += " AND spec_id >= ? AND spec_id < ?"
        params.extend([start.isoformat(), (end + dt.timedelta(days=1)).isoformat()])
    row = db.execute(sql + " ORDER BY eligible_at,job_key LIMIT 1", params).fetchone()
    if row is None:
        db.commit()
        return None
    db.execute("UPDATE jobs SET state='running', attempt=attempt+1,started_at=?,updated_at=? WHERE job_key=?",
               (iso(now), iso(now), row["job_key"]))
    db.commit()
    return {**dict(row), "attempt": row["attempt"] + 1}


def finish(db: sqlite3.Connection, job_key: str, state: str, *, error: str = "", media: dict | None = None,
           now: dt.datetime | None = None, attempt: int = 1, max_attempts: int = 3) -> str:
    now = now or utcnow()
    if state == "retry":
        state = "blocked" if attempt >= max_attempts else "retry"
    backoff = min(24 * 60, 15 * (2 ** max(0, attempt - 1)))
    next_at = now + dt.timedelta(minutes=backoff) if state == "retry" else now
    media = media or {}
    db.execute("UPDATE jobs SET state=?,eligible_at=?,updated_at=?,duration_sec=?,mp4_sha256=?,review_path=?,last_error=? "
               "WHERE job_key=? AND state='running'",
               (state, iso(next_at), iso(now), media.get("durationSec"), media.get("mp4Sha256"),
                media.get("reviewPath"), error[:800], job_key))
    db.commit()
    return state


def execute(command: list[str], *, cwd: pathlib.Path, timeout: int, logfile: pathlib.Path, env: dict[str, str] | None = None) -> None:
    """Abort an entire render process group on timeout, never a shell string."""
    logfile.parent.mkdir(parents=True, exist_ok=True)
    with logfile.open("a") as out:
        out.write("COMMAND " + repr(command) + "\n")
        out.flush()
        child = subprocess.Popen(command, cwd=cwd, env=env, stdout=out, stderr=subprocess.STDOUT,
                                 start_new_session=True, stdin=subprocess.DEVNULL)
        try:
            ret = child.wait(timeout=timeout)
        except subprocess.TimeoutExpired as error:
            try:
                os.killpg(child.pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
            try:
                child.wait(timeout=10)
            except subprocess.TimeoutExpired:
                try:
                    os.killpg(child.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                child.wait()
            raise RuntimeError(f"Command exceeded {timeout}s: {command[0]}") from error
        if ret:
            raise RuntimeError(f"Command failed with exit code {ret}; inspect {logfile}")


def archive_partial(path: pathlib.Path) -> None:
    """Preserve but quarantine incomplete render bytes across process crashes."""
    if not path.exists():
        return
    root = path.parent
    target = root / f".failed-{path.name.lstrip('.')}-{int(time.time())}"
    suffix = 0
    while target.exists():
        suffix += 1
        target = root / f".failed-{path.name.lstrip('.')}-{int(time.time())}-{suffix}"
    path.rename(target)


def adopt_verified_review(output: pathlib.Path, job: dict, spec_path: pathlib.Path) -> dict:
    """Resume a crash after files completed but before the DB receipt committed."""
    from scripts.verify_review import verify, verify_audio
    if not output.is_dir():
        raise ValueError("Review output is not a directory")
    video_dir = output / job["spec_id"]
    manifest = json.loads((video_dir / "manifest.json").read_text())
    if (manifest.get("publicationStatus") != "NOT_APPROVED_FOR_PUBLICATION"
            or manifest.get("id") != job["spec_id"]
            or manifest.get("specSha256") != job["spec_sha256"]):
        raise ValueError("Existing review manifest has wrong source identity")
    if (video_dir / "spec.json").read_bytes() != spec_path.read_bytes():
        raise ValueError("Existing review spec differs from current source")
    files = manifest.get("files")
    required = {"video.mp4", "thumb.jpg", "pack.json", "spec.json", "probe.json"}
    if not isinstance(files, dict) or set(files) != required:
        raise ValueError("Existing review file manifest incomplete")
    for filename, sha in files.items():
        if digest(video_dir / filename) != sha:
            raise ValueError(f"Existing review file changed: {filename}")
    if manifest.get("mp4Sha256") != digest(video_dir / "video.mp4"):
        raise ValueError("Existing video digest invalid")
    if manifest.get("thumbnailSha256") != digest(video_dir / "thumb.jpg"):
        raise ValueError("Existing thumbnail digest invalid")
    probe = json.loads((video_dir / "probe.json").read_text())
    recorded_duration = float(manifest["durationSec"])
    actual_duration = float(probe["format"]["duration"])
    if not 0 < recorded_duration < 36000 or abs(actual_duration - recorded_duration) > .25:
        raise ValueError("Review manifest duration does not match measured media")
    verify(json.loads(spec_path.read_text()), json.loads((video_dir / "pack.json").read_text()),
           probe, video_dir / "thumb.jpg")
    verify_audio(video_dir / "video.mp4")
    return {"reviewPath": str(video_dir), "mp4Sha256": manifest["mp4Sha256"],
            "durationSec": recorded_duration}


def render_one(job: dict, *, review_root: pathlib.Path, time_budget: int = 7200,
               log_root: pathlib.Path | None = None) -> dict:
    """Validate and produce a checked local review package. NEVER publish it."""
    source = spec_file(pathlib.Path(job["spec_path"]))
    if digest(source) != job["spec_sha256"]:
        raise FileExistsError("Source was modified after enqueue; superseded revision")
    from engine.spec_check import problems
    spec = json.loads(source.read_text())
    failures = problems(spec, source.parent.name, strict=True)
    if failures:
        raise ValueError("Strict spec rejected: " + "; ".join(failures[:4]))
    key = job["job_key"]
    output = review_root / f"{spec['id']}-{job['spec_sha256'][:12]}"
    if output.exists():
        return adopt_verified_review(output, job, source)
    tmp = review_root / f".staging-{spec['id']}-{job['spec_sha256'][:12]}"
    # After a crash, preserve the stale staging evidence and start clean.
    if tmp.is_dir() and not tmp.is_symlink():
        for scratch in tmp.glob(".blender-*"):
            if scratch.is_dir() and not scratch.is_symlink():
                shutil.rmtree(scratch)
    archive_partial(tmp)
    review_root.mkdir(parents=True, exist_ok=True)
    if shutil.disk_usage(review_root).free < 2 * 1024**3:
        raise RuntimeError("Less than 2 GiB free; stop before disk exhaustion")
    logs = log_root or review_root / "logs"
    log = logs / f"{spec['id']}-{job['spec_sha256'][:12]}.log"
    started = time.monotonic()
    try:
        # Keep full-size Blender frame sequences only for this render. Final
        # review files and diagnostic logs live outside the scratch directory.
        # Put scratch inside staging so a crash can be recovered next cycle.
        tmp.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix=".blender-", dir=tmp) as scratch:
            env = {**os.environ, "B3D_CACHE": scratch}
            execute([sys.executable, "-m", "engine.render", str(source), "--out", str(tmp)],
                    cwd=ROOT, timeout=time_budget, logfile=log, env=env)
        video_dir = tmp / spec["id"]
        video = video_dir / "video.mp4"
        execute(["ffmpeg", "-v", "error", "-xerror", "-i", str(video), "-f", "null", "-"],
                cwd=ROOT, timeout=180, logfile=log)
        probe = video_dir / "probe.json"
        with probe.open("w") as fd:
            subprocess.run(["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", str(video)],
                           stdout=fd, timeout=30, check=True)
        execute([sys.executable, "-m", "scripts.verify_review", str(source), str(video_dir)],
                cwd=ROOT, timeout=180, logfile=log)
        manifest = {"id": spec["id"], "specSha256": job["spec_sha256"],
                    "createdAt": iso(utcnow()), "durationSec": float(json.loads(probe.read_text())["format"]["duration"]),
                    "mp4Sha256": digest(video), "thumbnailSha256": digest(video_dir / "thumb.jpg"),
                    "elapsedSeconds": round(time.monotonic() - started, 1),
                    "publicationStatus": "NOT_APPROVED_FOR_PUBLICATION"}
        for filename in ("video.mp4", "thumb.jpg", "pack.json", "spec.json", "probe.json"):
            manifest.setdefault("files", {})[filename] = digest(video_dir / filename)
        (video_dir / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
        (video_dir / "checksums.txt").write_text("".join(
            f"{sha}  {filename}\n" for filename, sha in manifest["files"].items()))
        if digest(source) != job["spec_sha256"]:
            raise FileExistsError("Source changed during render; superseded revision")
        tmp.rename(output)
        return {"reviewPath": str(output / spec["id"]), "mp4Sha256": manifest["mp4Sha256"],
                "durationSec": manifest["durationSec"]}
    except Exception:
        # Preserve failed media separately but permit a clean retry. Never
        # overwrite previous evidence or mistake partial work for success.
        archive_partial(tmp)
        raise


def process_next(db: sqlite3.Connection, *, review_root: pathlib.Path, now: dt.datetime | None = None,
                 render_fn=render_one, time_budget: int = 7200, max_attempts: int = 3,
                 window: tuple[dt.date, dt.date] | None = None, job_key: str | None = None) -> dict:
    job = claim(db, now, window=window, job_key=job_key)
    if job is None:
        return {"status": "idle"}
    try:
        details = render_fn(job, review_root=review_root, time_budget=time_budget)
    except FileExistsError as error:
        state = finish(db, job["job_key"], "superseded", error=str(error), now=now or utcnow())
    except ValueError as error:
        state = finish(db, job["job_key"], "blocked", error=str(error), now=now or utcnow())
    except (OSError, RuntimeError, subprocess.SubprocessError) as error:
        state = finish(db, job["job_key"], "retry", error=str(error), attempt=job["attempt"], now=now or utcnow(),
                       max_attempts=max_attempts)
    except Exception as error:
        # A programming error or malformed external dependency must be visible
        # as a blocked job, rather than crashing the whole service and silently
        # leaving an indefinite in-progress lease.
        state = finish(db, job["job_key"], "blocked",
                       error=f"Unexpected {type(error).__name__}: {error}", now=now or utcnow())
    else:
        state = finish(db, job["job_key"], "verified", media=details, now=now or utcnow())
    return {"id": job["spec_id"], "state": state, "attempt": job["attempt"]}


def preflight(db_path: pathlib.Path, reviews: pathlib.Path, *, require_blender: bool = False) -> dict:
    """Check deployment dependencies before the host starts claiming jobs."""
    tools = {name: shutil.which(name) is not None for name in ("ffmpeg", "ffprobe", "fc-match")}
    modules = {name: find_spec(name) is not None for name in ("PIL", "numpy", "num2words", "kokoro_onnx", "soundfile")}
    storage = {}
    for label, path in (("database", db_path.parent), ("reviews", reviews)):
        try:
            path.mkdir(parents=True, exist_ok=True)
            free = shutil.disk_usage(path).free
            storage[label] = {"writable": os.access(path, os.W_OK | os.X_OK), "freeBytes": free}
        except OSError:
            storage[label] = {"writable": False, "freeBytes": 0}
    blender = None
    if require_blender:
        from engine.b3d import available
        blender = available() if modules["PIL"] else False
    ready = (all(tools.values()) and all(modules.values())
             and all(item["writable"] and item["freeBytes"] >= 2 * 1024**3 for item in storage.values())
             and blender is not False)
    return {"ready": ready, "tools": tools, "modules": modules, "storage": storage, "blender": blender}


def main():
    p = argparse.ArgumentParser(description="Durable private review queue (NO PUBLISHING)")
    p.add_argument("action", choices=["scan", "once", "cycle", "status", "preflight"])
    p.add_argument("--db", type=pathlib.Path, default=ROOT / "var" / "worker.sqlite3")
    p.add_argument("--reviews", type=pathlib.Path, default=ROOT / "var" / "reviews")
    p.add_argument("--spec", type=pathlib.Path, help="One specific spec from the configured directory for scan or cycle")
    p.add_argument("--days", type=int, default=7, help="Future-day horizon for scan (1-30)")
    p.add_argument("--start-offset", type=int, default=0, help="Start scan this many days from today")
    p.add_argument("--limit", type=int, default=1, help="Max jobs for one invocation (1-10)")
    p.add_argument("--timeout", type=int, default=7200, help="Per-job render timeout (seconds)")
    p.add_argument("--require-blender", action="store_true", help="Verify Blender Python during preflight")
    args = p.parse_args()
    if not 1 <= args.limit <= 10 or not 60 <= args.timeout <= 21600:
        p.error("limit must be 1-10 and timeout 60-21600 seconds")
    if not 1 <= args.days <= 30 or not 0 <= args.start_offset <= 30:
        p.error("days must be 1-30 and start offset 0-30")

    if args.spec and args.action not in ("scan", "cycle"):
        p.error("--spec is only supported by scan or cycle")

    os.umask(0o077)  # protect the lock, SQLite queue, manifests and logs

    if args.action == "preflight":
        result = preflight(args.db, args.reviews, require_blender=args.require_blender)
        print(json.dumps(result, indent=2))
        if not result["ready"]:
            raise SystemExit(2)
        return

    def run() -> dict:
        window = None
        job_key = None
        with closing(connection(args.db)) as db:
            if args.action in ("scan", "cycle"):
                today = utcnow().date()
                start = today + dt.timedelta(days=args.start_offset)
                if args.action == "cycle" and not args.spec:
                    window = (start, start + dt.timedelta(days=args.days - 1))
                if args.action == "cycle" and args.spec:
                    try:
                        selected = spec_file(args.spec)
                        job_key = f"{selected.parent.name}-{selected.stem}:{digest(selected)}"
                    except (OSError, ValueError) as error:
                        p.error(f"Invalid cycle spec: {error}")
                files = [args.spec] if args.spec else future_specs(today=today, days=args.days, start_offset=args.start_offset)
                imported = enqueue(db, files)
                if args.action == "scan":
                    return imported
            if args.action in ("once", "cycle"):
                # Safe to recover immediately: an exclusive render lock proves
                # no other same-host process owns any still-running jobs.
                recovered = recover_stale(db, utcnow(), max_age_hours=0)
                jobs = [process_next(db, review_root=args.reviews, time_budget=args.timeout, window=window, job_key=job_key)
                        for _ in range(args.limit)]
                return {"scan": imported if args.action == "cycle" else None,
                        "recovered": recovered, "jobs": jobs}
            return {row["state"]: row["count"] for row in
                    db.execute("SELECT state, count(*) AS count FROM jobs GROUP BY state")}

    try:
        if args.action in ("once", "cycle"):
            with single_worker(args.db):
                outcome = run()
        else:
            outcome = run()
    except RuntimeError as error:
        p.exit(2, f"Worker busy or unavailable: {error}\n")
    print(json.dumps(outcome, indent=2))


if __name__ == "__main__":
    main()
