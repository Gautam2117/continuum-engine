"""Turns Studio's real analytics into guidance for the next scripts and the next publish times.

feedback.json comes from Studio (/api/autopilot/feedback); ledger.json is written by the planner and ties every
published video back to the choices that produced it (topic axis, publish slot, format)."""
import json
import os
import pathlib
import re
import statistics

STATE = pathlib.Path(os.environ.get("CONTINUUM_STATE_DIR") or (pathlib.Path(__file__).parent / "state")).resolve()


def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", s.lower()).replace(" shorts", "").strip()


def load(name: str, default):
    p = STATE / name
    try:
        return json.loads(p.read_text())
    except (OSError, json.JSONDecodeError):
        return default


def save(name: str, data) -> None:
    STATE.mkdir(parents=True, exist_ok=True)
    (STATE / name).write_text(json.dumps(data, indent=1, ensure_ascii=False) + "\n")


def joined(channel: str) -> list[dict]:
    """Ledger entries for a channel with their measured results (when Studio has them)."""
    feedback = load("feedback.json", {})
    ledger = load("ledger.json", [])
    vids = {}
    for ch in feedback.get("channels", []):
        if _norm(ch.get("title", "")) == _norm(channel):
            for v in ch.get("videos", []):
                vids[_norm(v.get("title", ""))] = v
    out = []
    for e in ledger:
        if e["channel"] != channel:
            continue
        v = vids.get(_norm(e["title"]))
        if v and v.get("views") is not None:
            out.append({**e, **{k: v.get(k) for k in ("views", "minutes", "avgPct", "subsGained", "publishedAt")}})
    return out


def score(v: dict, med_views: float) -> float:
    """One number per video: views relative to the channel's median, nudged by retention and subscribers."""
    rel = (v.get("views") or 0) / max(med_views, 1)
    ret = (v.get("avgPct") or 0) / 100
    subs = min((v.get("subsGained") or 0) / max(v.get("views") or 1, 1) * 100, 3) / 3
    return round(0.6 * min(rel, 5) / 5 + 0.25 * ret + 0.15 * subs, 4)


def slot_stats(channel: str, fmt: str) -> dict[str, tuple[int, float]]:
    rows = [r for r in joined(channel) if r.get("format") == fmt and r.get("slot")]
    if not rows:
        return {}
    med = statistics.median([r["views"] or 0 for r in rows]) or 1
    by: dict[str, list[float]] = {}
    for r in rows:
        by.setdefault(r["slot"], []).append(score(r, med))
    return {k: (len(v), sum(v) / len(v)) for k, v in by.items()}


def guidance(channel: str, fmt: str) -> str:
    """A short paragraph for the planner prompt: what has worked and flopped on this channel."""
    rows = [r for r in joined(channel) if r.get("format") == fmt]
    if len(rows) < 4:
        return ""
    med = statistics.median([r["views"] or 0 for r in rows]) or 1
    ranked = sorted(rows, key=lambda r: score(r, med), reverse=True)
    best, worst = ranked[:3], ranked[-2:]
    fmt_row = lambda r: f'- "{r["title"]}" ({r.get("axis", "?")}): {r["views"]} views, {round(r.get("avgPct") or 0)}% watched'  # noqa: E731
    return "REAL RESULTS ON THIS CHANNEL (learn from them):\nBest:\n" + "\n".join(map(fmt_row, best)) + "\nWorst:\n" + "\n".join(map(fmt_row, worst))


def axis_weights(channel: str, axes: list[str]) -> list[str]:
    """Axes ordered best-first once there is data; otherwise unchanged."""
    rows = [r for r in joined(channel) if r.get("axis")]
    if len(rows) < 6:
        return axes
    med = statistics.median([r["views"] or 0 for r in rows]) or 1
    by: dict[str, list[float]] = {}
    for r in rows:
        by.setdefault(r["axis"], []).append(score(r, med))
    avg = {a: sum(by[a]) / len(by[a]) if a in by else 0.5 for a in axes}  # unseen axes get a middling score to stay in rotation
    return sorted(axes, key=lambda a: avg[a], reverse=True)
