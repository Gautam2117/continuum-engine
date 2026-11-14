# Independent channel competitor research, revision 1

Status: **Implemented and offline tested, NOT running against live YouTube accounts.** This uses YouTube Data API v3 public video metadata only. It does not scrape private analytics, download copyrighted videos, imitate recognizable creator designs, purchase views or bypass API quotas.

## Why this exists

Each of the 48 automated channels gets an independent search term in `autopilot/market.py`. Using one global 'viral video ideas' list would flatten channel identities, even with different prompt words. The weekly fair rotation visits all 48 channels with seven research slots a day. Source title, creator, published date, view count, public subscriber count (if available), likes and URL are saved separately for each channel. Since a channel's *current* subscriber total may differ from its subscribers at video publication, views/current-subscribers is a topical attention proxy, **not** a verified outlier multiple or a retention metric.

## Safe operator commands

```bash
python scripts/market_scan.py --date 2026-11-14 --limit 7
# PRINTS PLAN ONLY. NO NETWORK AND NO KEY REQUIRED.

# Only after a project owner has supplied their approved Data API key
# and verified this project's remaining quota:
YOUTUBE_DATA_API_KEY=... python scripts/market_scan.py --live --limit 7 --upload-reserve 75
```

The CLI defaults to dry-run. Real requests require `--live` **and** an existing project API key. It spends Data API quota (which is not a cash budget authorization). The upload reserve is an intentionally conservative 100 units per potential `videos.insert`; review current official quota docs and actual multi-channel project allocation before adjusting. Search costs 100 units per scan, plus two batched one-unit detail calls if nonempty. With the default conservative 10,000-unit project quota, 75 uploads reserved and 500 other units reserved, only 19 research slots fit per day. **At 97 reserved uploads, no extra research capacity remains.** Never defeat limits by splitting requests across extra projects to evade quota.

If one API request fails, the scan stops, reports a reason without exposing the key, and does not replace other channels' observations. The payload is stored in the existing atomic insights state as `market_signals.json`. Each channel may use only its own nonexpired observations for *original* topic exploration; no creator's title, narration, footage, thumbnail or character is a reusable asset. A video idea still requires independent factual sources and per-channel editorial approval.

## Research quality limits

Search ranking is a platform signal, not evidence that a format 'guarantees' virality. Likes per view omit dislikes, comments and saves; duration alone cannot establish Shorts retention; newly uploaded content has incomplete distribution. The system must never call this 'success prediction'. Analytics from the actual owned channel, once available with source IDs and 48-hour maturity, take priority over competitor proxies.

Official references:

- https://developers.google.com/youtube/v3/determine_quota_cost
- https://developers.google.com/youtube/v3/docs/search/list
- https://developers.google.com/youtube/v3/docs/videos/list
- https://developers.google.com/youtube/v3/docs/channels/list
- https://support.google.com/youtube/answer/1311392
