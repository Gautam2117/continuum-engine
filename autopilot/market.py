"""Bounded, independent research into public YouTube audience demand.

Official Data API only. No scraping, free-tier evasion, copying of competitors'
video media, boosting metrics, proxy farms or purchased subscriptions. Each
channel has a unique query and separate evidence record. No requests without
an already-authorized YOUTUBE_DATA_API_KEY and --live user action.
"""
from __future__ import annotations

import datetime as dt
import json
import math
import os
import pathlib
import re
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass

from . import insights
from .playbooks import PLAYBOOKS

BASE = 'https://www.googleapis.com/youtube/v3/'
WINDOW_DAYS = 60
TTL_DAYS = 21
MAX_RESULTS = 10
SEARCH_QUOTA = 100
DETAIL_QUOTA = 2  # one batched videos.list and one batched channels.list
PUBLIC_VIDEO_RE = re.compile(r'^[A-Za-z0-9_-]{11}$')

# These are 48 independent audiences, not a handful of shared niche buckets.
QUERY = {
    'Counterfactual Atlas': 'what if space science physics animation',
    '10SecScientist': '10 second science explain animation',
    'Oddly Proven': 'counterintuitive scientific studies experiments animation',
    'Crazy Clipz': 'record breaking feats explained animated',
    'Wild Creature Files': 'rare animal wildlife behavior explained',
    'Foundbeam': 'startup user acquisition stories illustrated',
    'Workflow Verdict': 'software workflow product comparison demonstration',
    'History to Drift To': 'calm bedtime ancient daily life history',
    'What Happens in 10': 'seconds timer mechanical process animation',
    'What Drives It': 'how machine works cutaway engineering animation',
    'OH, THIS EXISTS': 'strange real inventions unusual objects',
    'What If Anomaly': 'original alternate reality science fiction animation',
    'Gears Unseen': 'working gears mechanism historical engineering',
    'Brain Fool Lab': 'optical illusions visual perception brain',
    'Drawn Out Minds': 'hand drawn psychological storytelling original',
    'Think Beyond This': 'philosophy paradox thought experiment animation',
    'The Low Battery Show': 'original clay stop motion comedy skit',
    'Strata': 'collaborative photo album app feature use cases',
    'Sienna Carter': 'fictional ai character diary cinematography',
    'Aditi Raichand': 'हिन्दी मौलिक किरदार एनिमेशन कहानी',
    'Kiara': 'cinematic fictional avatar short visual story',
    'Samjho System': 'हिन्दी टेक्नोलॉजी कैसे काम करता है',
    'Inkbound': 'kinetic typography animated original poetry',
    'Founder, Actually': 'startup founder mistakes illustrated comedy',
    'LifeSpawn': 'evolution life cycle biology animation',
    'Next Frame': 'cinematography techniques animated examples',
    'Majority Rules': 'voting systems paradox mathematics explain',
    'Room 404': 'original liminal corridor horror animation',
    'Epic Elsewhere': 'original fantasy world animated short story',
    'The Night Archive': 'history mystery documentary evidence archive',
    'The Odd Units': 'strange units measurement scale comparisons',
    'Unreal Goods Co.': 'fictional absurd product commercial animation',
    'Tiny Histories': 'microhistory overlooked object historical facts',
    'Sent In': 'animated fictional letters micro stories',
    'The Builders Long Game': 'historical infrastructure construction animation',
    'One-Dollar Builds': 'low budget actual diy project build',
    'Unsealed Show': 'public document source investigation explain',
    'Heist & Con': 'fraud psychology historical heist documentary',
    'Survive This': 'survival physics safe science animation',
    'News From 2099': 'original future sci fi news animation',
    'Money Has Mechanics': 'how finance works technical diagram',
    'The India Machine': 'भारत तकनीकी infrastructure कैसे काम करता है',
    'Truth Over Propaganda': 'evidence based source fact checking visual',
    'BLANK HOURS': 'cinematic dark ambient generative visual music',
    'Benchwisedeals': 'product comparison verified technology price',
    'Brieflylatest': 'latest news story explained visual source',
    'OHGUMMY': 'gummy clay stop motion animation original',
    'Pixel Fables': 'pixel art original animated short stories',
}


def verify() -> None:
    if set(QUERY) != set(PLAYBOOKS):
        raise ValueError('Research subjects must cover each automated channel independently')
    if len(set(QUERY.values())) != len(QUERY):
        raise ValueError('Each channel must have a distinct query, not shared niche buckets')


def rotate(day: dt.date, count: int) -> list[str]:
    """Deterministic fair rotation; seven daily slots cover 48 in seven days."""
    verify()
    if not 0 <= count <= len(QUERY):
        raise ValueError('Research count out of bounds')
    keys = list(QUERY)
    offset = (day - dt.date(2026, 11, 14)).days * count % len(keys)
    return [keys[(offset+i) % len(keys)] for i in range(count)]


def quota_allowed(upload_reserve: int, other_reserve: int, max_scans: int,
                  quota_limit: int = 10_000) -> int:
    """Conservative quota reservation. Upload costs are platform-specific."""
    if min(upload_reserve, other_reserve, max_scans, quota_limit) < 0:
        raise ValueError('Negative quotas or reserves are invalid')
    spare = max(0, quota_limit - 100 * upload_reserve - other_reserve)
    return min(max_scans, len(QUERY), spare // (SEARCH_QUOTA + DETAIL_QUOTA))


def _iso_time(value: str) -> dt.datetime | None:
    try:
        parsed = dt.datetime.fromisoformat(value.replace('Z', '+00:00'))
        if parsed.tzinfo is None:
            return None
        return parsed.astimezone(dt.timezone.utc)
    except (AttributeError, ValueError):
        return None


@dataclass
class Client:
    key: str
    requests: int = 0

    def call(self, endpoint: str, data: dict) -> dict:
        if endpoint not in ('search', 'videos', 'channels'):
            raise ValueError('Unsupported YouTube Data API endpoint')
        if not self.key:
            raise ValueError('API key missing')
        params={**data, 'key':self.key}
        url=BASE+endpoint+'?'+urllib.parse.urlencode(params)
        # API key is never written to logs, feedback or exception messages.
        request=urllib.request.Request(url,headers={'accept':'application/json',
                                                      'user-agent':'continuum-independent-market-observer/1.0'})
        try:
            with urllib.request.urlopen(request,timeout=20) as response:
                payload=response.read(2_000_001)
        except urllib.error.HTTPError as exc:
            if exc.code in (400,403,429):
                raise RuntimeError(f'YouTube API rejected a request ({exc.code}); verify quota, key and permissions') from None
            raise RuntimeError(f'YouTube API unavailable ({exc.code})') from None
        except (OSError, TimeoutError) as exc:
            raise RuntimeError(f'YouTube API connection failed ({type(exc).__name__})') from None
        if len(payload)>2_000_000:
            raise ValueError('YouTube API response larger than safe limit')
        self.requests += 1
        result=json.loads(payload)
        if not isinstance(result,dict):
            raise ValueError('Unexpected YouTube API JSON response')
        return result


def scan_channel(channel: str, client: Client, *, now: dt.datetime | None = None) -> dict:
    """Discover observed high-performing videos, not their copyrighted work."""
    verify()
    if channel not in QUERY:
        raise ValueError('Unknown channel')
    now=now or dt.datetime.now(dt.timezone.utc)
    after=(now-dt.timedelta(days=WINDOW_DAYS)).isoformat().replace('+00:00','Z')
    search=client.call('search',{
        'part':'id,snippet','type':'video','q':QUERY[channel],'maxResults':MAX_RESULTS,
        'order':'viewCount','publishedAfter':after,'safeSearch':'moderate'
    })
    ids=[]
    for item in search.get('items') or []:
        if isinstance(item,dict) and isinstance(item.get('id'),dict):
            ident=item['id'].get('videoId')
            if isinstance(ident,str) and PUBLIC_VIDEO_RE.fullmatch(ident) and ident not in ids:
                ids.append(ident)
    if not ids:
        return {'channel':channel,'query':QUERY[channel],'observedAt':now.isoformat(),
                'source':'official_youtube_data_api','videos':[]}
    videos=client.call('videos',{'part':'snippet,statistics,contentDetails','id':','.join(ids)})
    items=[v for v in videos.get('items',[]) if isinstance(v,dict) and v.get('id') in ids]
    channels=sorted({v.get('snippet',{}).get('channelId') for v in items
                     if isinstance(v.get('snippet',{}).get('channelId'),str)})
    subscribers={}
    if channels:
        info=client.call('channels',{'part':'statistics','id':','.join(channels)})
        for c in info.get('items',[]):
            stats=c.get('statistics') or {}
            try:
                subscribers[c['id']]=int(stats['subscriberCount']) if not stats.get('hiddenSubscriberCount') else None
            except (KeyError,ValueError,TypeError):
                subscribers[c.get('id')]=None
    signals=[]
    for v in items:
        meta=v.get('snippet') or {}
        stats=v.get('statistics') or {}
        published=_iso_time(str(meta.get('publishedAt','')))
        if not published or published>now or published<now-dt.timedelta(days=WINDOW_DAYS):
            continue
        try:
            views=int(stats.get('viewCount',0))
            likes=int(stats.get('likeCount',0))
        except (TypeError,ValueError):
            continue
        if views<1000 or likes<0:
            continue
        sub=subscribers.get(meta.get('channelId'))
        days=max(1/24,(now-published).total_seconds()/86400)
        rate=views/max(sub or 1000,1000)
        velocity=views/days
        signals.append({
            'videoId':v['id'],'url':'https://www.youtube.com/watch?v='+v['id'],
            'title':str(meta.get('title','')).strip()[:170],
            'creator':str(meta.get('channelTitle','')).strip()[:100],
            'channelId':meta.get('channelId'),
            'publishedAt':published.isoformat(),'views':views,
            'subscribers':sub,'viewsPerSubscriberProxy':round(rate,2) if sub is not None else None,
            'viewsPerDaySincePublished':int(velocity),
            'engagementRateLikesOnly':round(likes/max(views,1),4),
            'durationIso':(v.get('contentDetails') or {}).get('duration'),
        })
    signals.sort(key=lambda s:((s['viewsPerSubscriberProxy'] or 0),s['viewsPerDaySincePublished']),reverse=True)
    return {'channel':channel,'query':QUERY[channel],
            'observedAt':now.isoformat(),'source':'official_youtube_data_api',
            'metricWarning':'views/subscribers is a topical attention proxy, not a causal growth measure or within-channel outlier score',
            'videos':signals[:6]}


def guidance(channel: str, *, now: dt.datetime | None = None) -> str:
    """Place qualified public signals only into that channel's next topic brief."""
    history=insights.load('market_signals.json',{})
    row=(history.get('channels') or {}).get(channel)
    if not isinstance(row,dict) or row.get('channel') != channel:
        return ''
    now=now or dt.datetime.now(dt.timezone.utc)
    when=_iso_time(row.get('observedAt',''))
    if not when or when>now or now-when>dt.timedelta(days=TTL_DAYS):
        return ''
    samples=[v for v in row.get('videos',[]) if isinstance(v,dict) and
             isinstance(v.get('title'),str) and v.get('views',0)>=1000]
    if not samples:
        return ''
    lines=[]
    for v in samples[:3]:
        ratio=v.get('viewsPerSubscriberProxy')
        ratio_text=f'{ratio} views per subscriber proxy' if ratio is not None else 'subscriber count unavailable'
        lines.append(f'  Observed {v["title"][:120]!r}: {int(v["views"]):,} views; {ratio_text}; public source {v["url"]}')
    return ('PUBLIC COMPETITOR DISCOVERY, channel-specific, not controlled evidence. '
            'These titles/visuals belong to others. Do NOT reproduce their names, scripts, characters, '
            'footage, exact concepts or thumbnail layouts. Use this only to detect audience questions '
            'and find a materially different original angle for THIS channel. '
            'Never use these observations as proof of a factual claim.\n'
            + '\n'.join(lines))


def record(channel: str, snapshot: dict) -> None:
    """Update one channel without wiping distinct histories of the other 47."""
    if channel not in QUERY or snapshot.get('channel')!=channel:
        raise ValueError('Source channel mismatch')
    saved=insights.load('market_signals.json',{})
    rows=saved.setdefault('channels',{})
    rows[channel]=snapshot
    saved['schemaVersion']=1
    insights.save('market_signals.json',saved)
