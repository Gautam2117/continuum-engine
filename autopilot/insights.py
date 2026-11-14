"""Turns Studio's real analytics into guidance for the next scripts and the next publish times.

feedback.json comes from Studio (/api/autopilot/feedback); ledger.json is written by the planner and ties every
published video back to the choices that produced it (topic axis, publish slot, format)."""
import datetime as dt
import json
import os
import pathlib
import re
import statistics
import tempfile

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
    payload = json.dumps(data, indent=1, ensure_ascii=False) + "\n"
    with tempfile.NamedTemporaryFile(dir=STATE, delete=False) as output:
        draft = pathlib.Path(output.name)
        try:
            output.write(payload.encode("utf-8"))
            output.close()
            draft.replace(STATE / name)
        finally:
            draft.unlink(missing_ok=True)


def joined(channel: str) -> list[dict]:
    """Use exact Engine spec IDs supplied by Studio's published YouTube lineage.

    Never match performance to a script by title: titles can be edited, reused
    and frequently repeat across Shorts. A missing source link means unlinked,
    not a zero-performing or missing upload.
    """
    feedback = load("feedback.json", {})
    ledger = load("ledger.json", [])
    matched: dict[str, list[dict]] = {}
    for ch in feedback.get("channels", []):
        if _norm(str(ch.get("title") or "")) != _norm(channel):
            continue
        for video in ch.get("videos", []):
            spec_id = video.get("engineSpecId")
            if isinstance(spec_id, str) and spec_id:
                matched.setdefault(spec_id, []).append(video)
    out = []
    for entry in ledger:
        if entry.get("channel") != channel or not isinstance(entry.get("id"), str):
            continue
        candidates = matched.get(entry["id"], [])
        # One video per spec is the accepted learning unit. Reuploads must be
        # investigated instead of silently overwriting the original metrics.
        if len(candidates) != 1 or candidates[0].get("views") is None:
            continue
        v = candidates[0]
        out.append({**entry, **{k: v.get(k) for k in
                                 ("views", "minutes", "avgPct", "subsGained", "publishedAt")},
                    "youtubeVideoId": v.get("id")})
    return out


def mature(row: dict, *, now: dt.datetime | None = None) -> bool:
    """Wait for a minimum 48 hours of distribution and analytics lag."""
    when = row.get("publishedAt")
    if not isinstance(when, str) or not when:
        return False
    try:
        parsed = dt.datetime.fromisoformat(when.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            return False
    except ValueError:
        return False
    now = now or dt.datetime.now(dt.timezone.utc)
    return dt.timedelta(hours=48) <= now - parsed <= dt.timedelta(days=180)


def previous_channel_examples(channel: str, fmt: str) -> str:
    """Existing videos provide observed audience context, not credited Engine wins.

    We deliberately don't infer a script's axis, editing style or causality
    from their titles. Only 48h+ examples can enter this observation note.
    """
    feedback = load("feedback.json", {})
    videos = [v for c in feedback.get("channels", [])
              if _norm(str(c.get("title") or "")) == _norm(channel)
              for v in c.get("videos", [])
              if v.get("format") == fmt and v.get("views") is not None and mature(v)]
    if len(videos) < 4:
        return ""
    ranked = sorted(videos, key=lambda v: max(0, v.get("views") or 0), reverse=True)
    best, low = ranked[:2], ranked[-2:]
    def example(v: dict) -> str:
        return f'- "{str(v.get("title") or "").strip()[:100]}" ({int(v["views"])} views)'
    return ("OBSERVED HISTORICAL VIDEOS FROM THIS SAME CHANNEL (not controlled experiments, no causal conclusions):\n"
            + "Higher-view examples:\n" + "\n".join(map(example, best))
            + "\nLower-view examples:\n" + "\n".join(map(example, low)))


def score(v: dict, med_views: float) -> float:
    """One number per video: views relative to the channel's median, nudged by retention and subscribers."""
    views = max(0, v.get("views") or 0)
    rel = views / max(med_views, 1)
    # Zero avgPct is frequently API lag or missing data, not a 0%-retention video.
    raw_ret = v.get("avgPct")
    ret = min(max(float(raw_ret) / 100, 0), 1.5) if raw_ret and raw_ret > 0 else 0.5
    subs = min(max((v.get("subsGained") or 0) / max(views, 1) * 100, 0), 3) / 3
    return round(0.6 * min(rel, 5) / 5 + 0.25 * ret + 0.15 * subs, 4)


def slot_stats(channel: str, fmt: str) -> dict[str, tuple[int, float]]:
    rows = [r for r in joined(channel) if r.get("format") == fmt and r.get("slot") and mature(r)]
    if not rows:
        return {}
    med = statistics.median([r["views"] or 0 for r in rows]) or 1
    by: dict[str, list[float]] = {}
    for r in rows:
        by.setdefault(r["slot"], []).append(score(r, med))
    return {k: (len(v), sum(v) / len(v)) for k, v in by.items()}


def guidance(channel: str, fmt: str) -> str:
    """A short paragraph for the planner prompt: what has worked and flopped on this channel."""
    rows = [r for r in joined(channel) if r.get("format") == fmt and mature(r)]
    if len(rows) < 4:
        return previous_channel_examples(channel, fmt)
    med = statistics.median([r["views"] or 0 for r in rows]) or 1
    ranked = sorted(rows, key=lambda r: score(r, med), reverse=True)
    best, worst = ranked[:3], ranked[-2:]
    fmt_row = lambda r: f'- "{r["title"]}" ({r.get("axis", "?")}): {r["views"]} views, {round(r.get("avgPct") or 0)}% watched'  # noqa: E731
    return "REAL RESULTS ON THIS CHANNEL (learn from them):\nBest:\n" + "\n".join(map(fmt_row, best)) + "\nWorst:\n" + "\n".join(map(fmt_row, worst))


def axis_weights(channel: str, axes: list[str]) -> list[str]:
    """Axes ordered best-first once there is data; otherwise unchanged."""
    rows = [r for r in joined(channel) if r.get("axis") and mature(r)]
    if len(rows) < 6:
        return axes
    med = statistics.median([r["views"] or 0 for r in rows]) or 1
    by: dict[str, list[float]] = {}
    for r in rows:
        by.setdefault(r["axis"], []).append(score(r, med))
    avg = {a: sum(by[a]) / len(by[a]) if a in by else 0.5 for a in axes}  # unseen axes get a middling score to stay in rotation
    return sorted(axes, key=lambda a: avg[a], reverse=True)
