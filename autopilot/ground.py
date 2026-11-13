"""Fetch real source text so scripts are built from facts instead of a model's memory (Wikipedia, CC BY-SA)."""
import json
import urllib.parse
import urllib.request

UA = "ContinuumEngine/1.0 (https://continuumarc.tech; gautam@continuumarc.tech)"


def _get(params: dict) -> dict | None:
    url = "https://en.wikipedia.org/w/api.php?" + urllib.parse.urlencode({"format": "json", "formatversion": 2, **params})
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers={"user-agent": UA}), timeout=25) as r:
            return json.loads(r.read())
    except Exception:  # noqa: BLE001 - grounding is best effort; the planner copes without it
        return None


def ground(query: str, max_pages: int = 2, max_chars: int = 6500) -> dict:
    """{'text': str, 'sources': [{'title','url'}]} for the best-matching articles; empty when nothing found."""
    found = _get({"action": "query", "list": "search", "srsearch": query, "srlimit": max_pages, "srnamespace": 0})
    titles = [h["title"] for h in (found or {}).get("query", {}).get("search", [])][:max_pages]
    text, sources = [], []
    for t in titles:
        page = _get({"action": "query", "prop": "extracts", "explaintext": 1, "exlimit": 1, "titles": t, "exchars": max_chars // max_pages})
        pages = (page or {}).get("query", {}).get("pages", [])
        body = pages[0].get("extract", "").strip() if pages else ""
        if body:
            text.append(f"## {t}\n{body}")
            sources.append({"title": t, "url": "https://en.wikipedia.org/wiki/" + urllib.parse.quote(t.replace(" ", "_"))})
    return {"text": "\n\n".join(text), "sources": sources}


# ---- news mode (Brieflylatest): the story itself is the grounding -------------------------------------------------
import re
import xml.etree.ElementTree as ET

FEEDS = [
    ("NASA", "https://www.nasa.gov/news-release/feed/"),
    ("BBC News", "https://feeds.bbci.co.uk/news/science_and_environment/rss.xml"),
    ("BBC News", "https://feeds.bbci.co.uk/news/technology/rss.xml"),
]


def _clean(t: str | None) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", t or "")).strip()


def news_items(limit: int = 12) -> list[dict]:
    """Recent headlines with their short summaries from public RSS feeds: [{'outlet','title','summary','url'}]."""
    out: list[dict] = []
    for outlet, url in FEEDS:
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={"user-agent": UA}), timeout=25) as r:
                root = ET.fromstring(r.read())
        except Exception:  # noqa: BLE001 - a feed being down is normal
            continue
        for it in root.iter("item"):
            title, link = _clean(it.findtext("title")), _clean(it.findtext("link"))
            summary = _clean(it.findtext("description"))[:600]
            if title and link:
                out.append({"outlet": outlet, "title": title, "summary": summary, "url": link})
            if sum(1 for o in out if o["outlet"] == outlet) >= limit // 2:
                break
    return out


def ground_news(item: dict) -> dict:
    return {"text": f"## {item['outlet']}: {item['title']}\n{item['summary']}\n(Source: {item['outlet']}, {item['url']})",
            "sources": [{"title": f"{item['outlet']}: {item['title']}", "url": item["url"]}], "label": "Source"}
