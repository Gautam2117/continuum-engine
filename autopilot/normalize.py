"""Make narration speakable: Kokoro reads words better than digits."""
import re

from num2words import num2words


def _year(n: int) -> str:
    return num2words(n, to="year")


def _clock(m: re.Match) -> str:
    h, mi, ap = int(m.group(1)), int(m.group(2) or 0), (m.group(3) or "").replace(".", "").lower()
    words = num2words(h) + ("" if mi == 0 else (" oh " + num2words(mi) if mi < 10 else " " + num2words(mi)))
    return words + (" " + " ".join(ap) if ap else (" o'clock" if mi == 0 else ""))


def speakable(text: str) -> str:
    if re.search(r"[\u0900-\u097F]", text):  # Devanagari: the model writes numbers in Hindi words itself
        return re.sub(r"\s+", " ", re.sub(r"\s*—\s*", ", ", text)).strip()
    text = re.sub(r"\b(\d{1,2})(?::(\d{2}))?\s*([ap]\.?m\.?)\b|\b(\d{1,2}):(\d{2})\b", lambda m: _clock(m) if m.group(1) else _clock(re.match(r"(\d{1,2}):(\d{2})()", m.group(4) + ":" + m.group(5))), text, flags=re.I)
    t = re.sub(r"\s*—\s*", ", ", text).replace("–", " to ").replace("&", " and ")
    t = re.sub(r"(\d),(\d{3})", r"\1\2", t)
    t = re.sub(r"(\d+(?:\.\d+)?)\s*%", lambda m: f"{_num(m.group(1))} percent", t)
    t = re.sub(r"(\d+(?:\.\d+)?)\s*[x×]\b", lambda m: f"{_num(m.group(1))} times", t)
    t = re.sub(r"\$(\d+(?:\.\d+)?)", lambda m: f"{_num(m.group(1))} dollars", t)
    t = re.sub(r"\b(1[1-9]\d\d|20\d\d)\b", lambda m: _year(int(m.group(1))), t)
    t = re.sub(r"\b\d+(?:\.\d+)?\b", lambda m: _num(m.group(0)), t)
    t = re.sub(r"\s+", " ", t).strip()
    return t


def _num(s: str) -> str:
    if "." in s:
        whole, frac = s.split(".")
        return f"{num2words(int(whole))} point {' '.join(num2words(int(c)) for c in frac)}"
    return num2words(int(s)).replace(",", "")
