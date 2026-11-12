"""Make narration speakable: Kokoro reads words better than digits."""
import re

from num2words import num2words


def _year(n: int) -> str:
    return num2words(n, to="year")


def speakable(text: str) -> str:
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
