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
