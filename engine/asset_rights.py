"""Commercial-use licensing and provenance for retrieved Wikimedia still images.

Only explicit public-domain, CC0, CC BY and CC BY-SA licence labels are
accepted. Ambiguous, non-commercial and no-derivative licences are rejected.
This is an automated prefilter, not a replacement for human copyright review.
"""
from __future__ import annotations

import re
import urllib.parse
from html import unescape

_ALLOWED_HOSTS = {"upload.wikimedia.org", "commons.wikimedia.org"}


def text_only(value: str) -> str:
    return re.sub(r"\s+", " ", unescape(re.sub(r"<[^>]*>", " ", value or ""))).strip()


def commercial_license(label: str) -> str | None:
    value = text_only(label).lower().replace("_", "-").strip()
    if any(bad in value for bad in ("noncommercial", "non-commercial", "-nc", "-nd", "no derivatives", "unknown", "fair use", "all rights reserved")):
        return None
    if value in {"pd", "public domain", "public-domain", "public domain mark"} or value.startswith("public domain "):
        return "Public domain"
    if re.fullmatch(r"cc[ -]?0(?:[ -]?\d+(?:\.\d+)?)?", value):
        return "CC0"
    if re.fullmatch(r"cc[ -]?by(?:[ -]sa)?(?:[ -]?\d+(?:\.\d+)?)?", value):
        return value.upper()
    return None


def safe_commons_url(value: str) -> bool:
    parsed = urllib.parse.urlparse(value)
    return parsed.scheme == "https" and parsed.hostname in _ALLOWED_HOSTS and not parsed.username and not parsed.password


def commons_file_url(title: str) -> str | None:
    if not isinstance(title, str) or not title.startswith("File:"):
        return None
    return "https://commons.wikimedia.org/wiki/" + urllib.parse.quote(title.replace(" ", "_"), safe=":_()-")


def provenance(page: dict, info: dict) -> dict | None:
    meta = info.get("extmetadata") or {}
    lic = commercial_license((meta.get("LicenseShortName") or {}).get("value", ""))
    title = str(page.get("title") or "")
    source = commons_file_url(title)
    url = info.get("thumburl") or info.get("url")
    if not lic or not source or not isinstance(url, str) or not safe_commons_url(url):
        return None
    author = text_only((meta.get("Artist") or {}).get("value", ""))[:180]
    credit = (f"{title} | {author or 'Creator not listed'} | {lic} | {source}")
    return {"downloadUrl": url, "sourceUrl": source, "title": title,
            "author": author or "Creator not listed", "license": lic, "credit": credit}
