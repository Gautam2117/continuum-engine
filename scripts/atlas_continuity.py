"""Read-only rolling Atlas runway audit. A spec is NOT an upload or a review."""
from __future__ import annotations
import argparse
import datetime as dt
import json
import pathlib
import sqlite3
from scripts import network_supervisor as supervisor

ATLAS = "Counterfactual Atlas"
UTC = dt.timezone.utc


def audit(root: pathlib.Path, db_path: pathlib.Path, *, today: dt.date | None = None, days: int = 8) -> dict:
    if not 1 <= days <= 30:
        raise ValueError("Runway horizon must be 1 to 30 days")
    today = today or dt.datetime.now(UTC).date()
    states: dict[str, dict[str, int]] = {}
    if db_path.is_file():
        try:
            with sqlite3.connect(f"file:{db_path.resolve()}?mode=ro", uri=True, timeout=5) as db:
                rows = db.execute("SELECT spec_id,state FROM jobs WHERE channel=?", (ATLAS,)).fetchall()
            for sid, state in rows:
                key = str(sid)[:10]
                bucket = states.setdefault(key, {})
                bucket[state] = bucket.get(state, 0) + 1
        except sqlite3.Error:
            states = {}  # A missing or inaccessible DB never creates fake evidence.
    dates = []
    for delta in range(days):
        day = today + dt.timedelta(days=delta)
        valid, eligible, invalid, held = supervisor.supply(root, day)
        shorts = len(valid.get((ATLAS, "short"), set()))
        longs = len(valid.get((ATLAS, "long"), set()))
        ready = len(eligible.get((ATLAS, "short"), set())) + len(eligible.get((ATLAS, "long"), set()))
        dates.append({"date": day.isoformat(), "required": 3,
                      "validShortSpecs": min(shorts, 2), "validLongSpecs": min(longs, 1),
                      "specSlotsMissing": max(0, 2 - shorts) + max(0, 1 - longs),
                      "editorialEligible": min(ready, 3),
                      "editorialHeld": len([r for r in held if r.get("channel") == ATLAS]),
                      "invalidFiles": len([r for r in invalid if "atlas" in r.get("file", "")]),
                      "privateWorkerStates": states.get(day.isoformat(), {}),
                      "publicYouTubeVideos": None})
    return {"channel": ATLAS, "dailyTarget": {"short": 2, "long": 1},
            "auditedAt": dt.datetime.now(UTC).isoformat(), "plannedEndDate": None,
            "horizonDays": days, "runway": dates,
            "completeSpecDays": sum(x["specSlotsMissing"] == 0 for x in dates),
            "reviewedMediaIsNotPublicUpload": True,
            "publicVerification": "Read Studio YouTube channel videos, not local specs or private worker receipts"}


def main() -> None:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--specs',type=pathlib.Path,default=supervisor.ROOT/'specs')
    p.add_argument('--db',type=pathlib.Path,default=supervisor.ROOT/'var'/'worker.sqlite3')
    p.add_argument('--days',type=int,default=8)
    p.add_argument('--output',type=pathlib.Path)
    args=p.parse_args()
    result=audit(args.specs,args.db,days=args.days)
    payload=json.dumps(result,ensure_ascii=False,indent=2)+'\n'
    if args.output:
        supervisor.write_atomic(args.output,result)
    print(payload,end='')

if __name__ == '__main__':
    main()
