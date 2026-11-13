"""Produce a truthful, repeatable hosted health report from review-workflow evidence.

Only measures scheduled planning and technical review inventory. Never implies that
review packages were editorially accepted, ingested, or publicly uploaded.
"""
from __future__ import annotations

import argparse
import json
import os
import re
from pathlib import Path

ARTIFACT_PATTERN = re.compile(r"^review-(\d{4}-\d{2}-\d{2})-([a-z0-9-]+)-[0-9a-f]{64}$")


def report(heartbeat: dict | None, artifact_names: list[str], run_id: str) -> tuple[str, bool]:
    url = f"https://github.com/Gautam2117/continuum-engine/actions/runs/{run_id}" if run_id else "Not available"
    intro = ["# Continuum Network Health", "", "Scope: 48 automated channels. Felix and GOTZ remain creator-led.",
             "This report measures scheduled specifications and **technical review artifacts only**. It does not confirm YouTube uploads, creative acceptance or monetization.", "", f"Autopilot run: {url}", ""]
    if not heartbeat or not isinstance(heartbeat.get("spec_inventory"), list):
        return "\n".join(intro + ["**Needs attention:** No usable scheduled inventory heartbeat exists. Check the Autopilot schedule and its preview artifact.", ""]), True
    rows = heartbeat["spec_inventory"]
    days = sorted({str(row.get("date")) for row in rows if isinstance(row, dict) and row.get("date")})
    if not days:
        return "\n".join(intro + ["**Needs attention:** The heartbeat contains no channel/date inventory rows.", ""]), True
    target_day = days[0]
    today_rows = [r for r in rows if isinstance(r, dict) and r.get("date") == target_day]
    expected = sum(max(0, int(r.get("target") or 0)) for r in today_rows)
    ready = sum(min(max(0, int(r.get("specs") or 0)), max(0, int(r.get("target") or 0))) for r in today_rows)
    holes = [r for r in today_rows if max(0, int(r.get("missing") or 0)) > 0]
    technical = {f"{day}-{identifier}" for name in artifact_names
                 for match in [ARTIFACT_PATTERN.fullmatch(name)] if match
                 for day, identifier in [match.groups()] if day == target_day}
    attempted = sum(int(n) for n in (heartbeat.get("attempts_by_model") or {}).values() if isinstance(n, int))
    failures = heartbeat.get("failed") if isinstance(heartbeat.get("failed"), list) else []
    lines = intro + [f"Planned date (UTC): **{target_day}**", "",
                     f"- Required channel slots: **{expected}**", f"- Slots with validated planned specs: **{ready}**",
                     f"- Distinct available technical-review artifacts dated that day: **{len(technical)}**",
                     f"- Provider attempts in latest run: **{attempted}**",
                     f"- Planning failures recorded: **{len(failures)}**", ""]
    alert = expected < 50 or ready < expected or len(technical) < expected or bool(failures)
    if alert:
        lines += ["## Needs attention", "", "The automated 50-video/day minimum is **not verified as filled and technically rendered**. The next scheduled Autopilot run should retry missing slots; do not publish unreviewed content.", ""]
        if holes:
            lines += ["First missing channel slots:", ""]
            for r in sorted(holes, key=lambda x: (-int(x.get("missing") or 0), str(x.get("channel") or "")))[:16]:
                lines.append(f"- {r.get('channel')}: {r.get('format')} {r.get('specs', 0)}/{r.get('target', 0)}")
            lines.append("")
    else:
        lines += ["All required specs and technical artifacts were found for this date. Editorial acceptance and public publishing remain separate gates.", ""]
    return "\n".join(lines), alert


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--heartbeat", type=Path, required=True)
    parser.add_argument("--artifacts", type=Path, required=True)
    parser.add_argument("--run-id", default="")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        heartbeat = json.loads(args.heartbeat.read_text())
    except (OSError, ValueError):
        heartbeat = None
    artifacts = args.artifacts.read_text().splitlines() if args.artifacts.is_file() else []
    body, alert = report(heartbeat, artifacts, args.run_id)
    args.output.write_text(body + "\n")
    print(f"Network health: {'attention required' if alert else 'technical inventory filled'}")
    if p := os.environ.get("GITHUB_OUTPUT"):
        with open(p, "a") as out:
            out.write(f"alert={str(alert).lower()}\n")


if __name__ == "__main__":
    main()
