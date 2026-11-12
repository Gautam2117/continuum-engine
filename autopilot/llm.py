"""Free-tier LLM access that keeps working when any one provider is rate-limited or retired.

Providers are tried in order. A key that isn't set is skipped. Every call is plain HTTPS with the standard
library, so nothing here depends on Claude, a laptop or a paid account.

  GEMINI_API_KEY      Google AI Studio free tier (OpenAI-compatible endpoint). Model list is discovered live.
  GROQ_API_KEY        Groq free tier.
  OPENROUTER_API_KEY  OpenRouter free (:free) models.
"""
from __future__ import annotations

import json
import os
import re
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field


class LLMError(RuntimeError):
    pass


def _http(url: str, body: dict | None, headers: dict, timeout: int = 120) -> dict:
    req = urllib.request.Request(url, data=json.dumps(body).encode() if body is not None else None, headers={"content-type": "application/json", "user-agent": "continuum-engine", **headers})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        raise LLMError(f"{e.code} {e.read().decode(errors='replace')[:300]}") from e
    except (urllib.error.URLError, TimeoutError) as e:
        raise LLMError(f"network: {e}") from e


def extract_json(text: str):
    """Parse the first JSON value in a model reply, tolerating code fences and chatter around it."""
    t = text.strip()
    t = re.sub(r"^```(?:json)?\s*|\s*```$", "", t, flags=re.I)
    try:
        return json.loads(t)
    except json.JSONDecodeError:
        pass
    for open_, close in (("{", "}"), ("[", "]")):
        a, b = t.find(open_), t.rfind(close)
        if a != -1 and b > a:
            try:
                return json.loads(t[a:b + 1])
            except json.JSONDecodeError:
                continue
    raise LLMError("reply was not valid JSON")


@dataclass
class Provider:
    name: str
    base: str
    key: str
    models: list[str]
    json_mode: bool = True
    dead: set = field(default_factory=set)  # models that hit a hard limit this run

    def chat(self, model: str, system: str, user: str, temperature: float, max_tokens: int, want_json: bool) -> str:
        body = {"model": model, "temperature": temperature, "max_tokens": max_tokens,
                "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}]}
        if want_json and self.json_mode:
            body["response_format"] = {"type": "json_object"}
        data = _http(f"{self.base}/chat/completions", body, {"authorization": f"Bearer {self.key}"})
        try:
            return data["choices"][0]["message"]["content"] or ""
        except (KeyError, IndexError, TypeError) as e:
            raise LLMError(f"unexpected reply shape: {str(data)[:200]}") from e


def _version(name: str) -> float:
    m = re.search(r"(\d+(?:\.\d+)?)", name)
    return float(m.group(1)) if m else 0.0


def discover_gemini(key: str) -> list[str]:
    """Newest first. Flash-Lite has the most free requests per day, then Gemma, then Flash."""
    forced = os.environ.get("LLM_GEMINI_MODELS")
    if forced:
        return [m.strip() for m in forced.split(",") if m.strip()]
    try:
        data = _http(f"https://generativelanguage.googleapis.com/v1beta/models?key={key}&pageSize=200", None, {})
    except LLMError:
        return ["gemini-3.5-flash-lite", "gemini-3.1-flash-lite", "gemini-2.5-flash-lite"]
    names = [m["name"].split("/")[-1] for m in data.get("models", []) if "generateContent" in m.get("supportedGenerationMethods", [])]
    names = [n for n in names if not re.search(r"image|tts|embedding|live|audio|vision|robotics|computer|thinking-exp", n)]
    pick = lambda pat: sorted([n for n in names if re.search(pat, n)], key=_version, reverse=True)  # noqa: E731
    lite = pick(r"flash-lite")
    gemma = pick(r"^gemma")
    flash = [n for n in pick(r"flash") if n not in lite]
    return (lite[:2] + gemma[:1] + flash[:1]) or ["gemini-2.5-flash-lite"]


def providers_from_env() -> list[Provider]:
    out: list[Provider] = []
    if k := os.environ.get("GEMINI_API_KEY"):
        out.append(Provider("gemini", "https://generativelanguage.googleapis.com/v1beta/openai", k, discover_gemini(k)))
    if k := os.environ.get("GROQ_API_KEY"):
        out.append(Provider("groq", "https://api.groq.com/openai/v1", k, ["llama-3.3-70b-versatile", "llama-3.1-8b-instant"]))
    if k := os.environ.get("OPENROUTER_API_KEY"):
        out.append(Provider("openrouter", "https://openrouter.ai/api/v1", k, [os.environ.get("OPENROUTER_MODEL", "meta-llama/llama-3.3-70b-instruct:free")]))
    return out


class LLM:
    def __init__(self, providers: list | None = None, log=print):
        self.providers = providers if providers is not None else providers_from_env()
        self.calls = 0
        self.log = log
        self.by_provider: dict[str, int] = {}

    @property
    def available(self) -> bool:
        return bool(self.providers)

    def complete(self, system: str, user: str, *, want_json: bool = True, temperature: float = 0.8, max_tokens: int = 6000):
        """Returns parsed JSON when want_json, else text. Fails over across providers and models."""
        if not self.providers:
            raise LLMError("no LLM key configured (set GEMINI_API_KEY, GROQ_API_KEY or OPENROUTER_API_KEY)")
        last = ""
        for prov in self.providers:
            for model in prov.models:
                if model in prov.dead:
                    continue
                for attempt in range(2):
                    try:
                        self.calls += 1
                        text = prov.chat(model, system, user, temperature, max_tokens, want_json)
                        result = extract_json(text) if want_json else text
                        self.by_provider[f"{prov.name}:{model}"] = self.by_provider.get(f"{prov.name}:{model}", 0) + 1
                        return result
                    except LLMError as e:
                        last = f"{prov.name}/{model}: {e}"
                        msg = str(e)
                        if msg.startswith(("429", "403", "404", "401")):
                            if "per minute" in msg.lower() or "rpm" in msg.lower():
                                time.sleep(20)
                                continue
                            prov.dead.add(model)  # daily quota or model retired: move on for this run
                            break
                        if "not valid JSON" in msg:
                            continue  # one more try with the same model
                        time.sleep(3 + attempt * 4)
                self.log(f"  llm: {last[:160]}")
        raise LLMError(f"all providers failed; last: {last}")
