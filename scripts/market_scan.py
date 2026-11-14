"""Read-only independent competitor discovery with explicit API quota budget.

Default is dry-run, so no network calls or charges occur without --live.
Each scan is channel-specific; never use another Continuum channel as a niche
training example. Data is anonymous public video metadata, not copied media.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from autopilot import market


def build_plan(*, today: dt.date, limit: int, upload_reserve: int,
               other_reserve: int, quota: int) -> dict:
    granted = market.quota_allowed(upload_reserve, other_reserve, limit, quota)
    channels = market.rotate(today, granted)
    return {
        'date':today.isoformat(), 'channels':channels, 'estimatedQuotaUnits':
        len(channels)*(market.SEARCH_QUOTA+market.DETAIL_QUOTA),
        'uploadReserveUnits':upload_reserve*100,
        'otherReserveUnits':other_reserve,
        'quotaLimit':quota,
        'mode':'PLAN_ONLY_NO_NETWORK',
    }


def main(argv: list[str] | None = None) -> int:
    p=argparse.ArgumentParser(description='Independent YouTube audience research, never copy a competitor video')
    p.add_argument('--live', action='store_true', help='Perform actual official YouTube Data API queries')
    p.add_argument('--limit',type=int,default=7,help='Channels examined per run (0..48)')
    p.add_argument('--upload-reserve',type=int,default=75,help='Reserve quota for uploads by other services')
    p.add_argument('--other-reserve',type=int,default=500,help='Reserve quota for existing project operations')
    p.add_argument('--quota',type=int,default=10000,help='Conservative project daily available quota')
    p.add_argument('--date',type=dt.date.fromisoformat,default=dt.datetime.now(dt.timezone.utc).date())
    args=p.parse_args(argv)
    if not 0 <= args.limit <= 48 or min(args.upload_reserve,args.other_reserve,args.quota)<0:
        p.error('limits and quotas must be nonnegative and daily channel limit at most 48')
    plan=build_plan(today=args.date,limit=args.limit,upload_reserve=args.upload_reserve,
                    other_reserve=args.other_reserve,quota=args.quota)
    if not args.live:
        print(json.dumps(plan,indent=2))
        return 0
    key=os.environ.get('YOUTUBE_DATA_API_KEY')
    if not key:
        p.error('--live requires YOUTUBE_DATA_API_KEY; no API credentials were created')
    client=market.Client(key)
    succeeded=[]
    failed=[]
    # A failure may represent quota exhaustion. Do not consume the remaining
    # day's quota aggressively; stop and report for human inspection.
    for channel in plan['channels']:
        try:
            snapshot=market.scan_channel(channel,client)
            market.record(channel,snapshot)
            succeeded.append({'channel':channel,'count':len(snapshot['videos'])})
        except (RuntimeError,ValueError,OSError) as exc:
            failed.append({'channel':channel,'error':str(exc)[:180]})
            break
    print(json.dumps({'mode':'READ_ONLY_MARKET_OBSERVATION','scanned':succeeded,
                      'failures':failed,'requestCount':client.requests,
                      'remainingNotAttempted':plan['channels'][len(succeeded)+len(failed):]},indent=2))
    return 1 if failed else 0


if __name__=='__main__':
    raise SystemExit(main())
