"""Free-tier LLM access that keeps working when any one provider is rate-limited or retired.

Providers are tried in order. A key that isn't set is skipped. Every call is plain HTTPS with the standard
library, so nothing here depends on Claude, a laptop or a paid account.

  GEMINI_API_KEY      Google AI Studio free tier (OpenAI-compatible endpoint). Model list is discovered live.
  GROQ_API_KEY        Groq free tier.
  OPENROUTER_API_KEY  OpenRouter free (:free) models.
  CEREBRAS_API_KEY    Cerebras free tier. Model list is discovered live.
  MISTRAL_API_KEY     Mistral "Experiment" free tier.
  GITHUB_MODELS_TOKEN GitHub Models free tier (a PAT with models:read).
Model lists for Groq and Cerebras are discovered live, because retired ids 404 and would silently starve the run.
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
    models: list[str]                                 # bulk tier: most requests per day
    best: list[str] = field(default_factory=list)     # quality tier: strongest models first
    json_mode: bool = True
    dead: set = field(default_factory=set)  # models that hit a hard limit this run
    busy_hits: int = 0                       # consecutive busy/rate-limit failures
    cool_until: float = 0.0                  # monotonic time before which this provider is skipped (when another is available)

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


def discover_gemini(key: str) -> tuple[list[str], list[str]]:
    """Returns (best, bulk). Best = strongest first (Pro, then newest Flash); bulk = Flash-Lite and Gemma, which
    have the most free requests per day. Writing and editing use best and fall back down as quotas run out."""
    forced = os.environ.get("LLM_GEMINI_MODELS")
    if forced:
        m = [x.strip() for x in forced.split(",") if x.strip()]
        return m, m
    try:
        data = _http(f"https://generativelanguage.googleapis.com/v1beta/models?key={key}&pageSize=200", None, {})
    except LLMError:
        return ["gemini-2.5-pro", "gemini-3.5-flash", "gemini-2.5-flash"], ["gemini-3.5-flash-lite", "gemini-3.1-flash-lite", "gemini-2.5-flash-lite"]
    names = [m["name"].split("/")[-1] for m in data.get("models", []) if "generateContent" in m.get("supportedGenerationMethods", [])]
    names = [n for n in names if not re.search(r"image|tts|embedding|live|audio|vision|robotics|computer|thinking-exp|preview-\d|exp", n)]
    pick = lambda pat: sorted([n for n in names if re.search(pat, n)], key=_version, reverse=True)  # noqa: E731
    lite = pick(r"flash-lite")
    gemma = pick(r"^gemma")
    pro = pick(r"-pro")
    flash = [n for n in pick(r"flash") if n not in lite]
    bulk = (lite[:2] + gemma[:1] + flash[:1]) or ["gemini-2.5-flash-lite"]
    best = (pro[:2] + flash[:2] + gemma[:1]) or bulk
    return best, bulk


_NOT_CHAT = r"whisper|guard|tts|embed|moderation|vision-preview|orpheus|playai|distil-whisper|safeguard|prompt-guard|ocr|image|audio|transcri"


def discover_openai_compat(base: str, key: str, fallback: list[str], prefer: list[str] | None = None) -> list[str]:
    """Live model list for an OpenAI-compatible endpoint, strongest first (preferred ids, then by parameter count).
    Falls back to a static list when the listing call itself fails."""
    forced = os.environ.get(f"LLM_{re.sub(r'[^A-Z]', '', base.upper())[:12]}_MODELS")
    if forced:
        return [x.strip() for x in forced.split(",") if x.strip()]
    try:
        data = _http(f"{base}/models", None, {"authorization": f"Bearer {key}"}, timeout=30)
    except LLMError:
        return fallback
    ids = [m.get("id", "") for m in data.get("data", []) if m.get("id") and not re.search(_NOT_CHAT, m["id"], re.I)]
    if not ids:
        return fallback

    def size(n: str) -> float:
        m = re.search(r"(\d+(?:\.\d+)?)b", n.lower())
        return float(m.group(1)) if m else 0.0

    prefer = prefer or []
    ranked = [p for p in prefer if p in ids] + sorted([n for n in ids if n not in prefer], key=lambda n: (-size(n), n))
    return ranked[:6]


def providers_from_env() -> list[Provider]:
    out: list[Provider] = []
    if k := os.environ.get("GEMINI_API_KEY"):
        best, bulk = discover_gemini(k)
        out.append(Provider("gemini", "https://generativelanguage.googleapis.com/v1beta/openai", k, bulk, best=best))
    if k := os.environ.get("GROQ_API_KEY"):
        gm = discover_openai_compat("https://api.groq.com/openai/v1", k, ["openai/gpt-oss-120b", "llama-3.3-70b-versatile", "openai/gpt-oss-20b"],
                                    prefer=["openai/gpt-oss-120b", "llama-3.3-70b-versatile", "qwen/qwen3-32b", "openai/gpt-oss-20b"])
        out.append(Provider("groq", "https://api.groq.com/openai/v1", k, gm, best=gm[:2]))
    if k := os.environ.get("CEREBRAS_API_KEY"):
        cm = discover_openai_compat("https://api.cerebras.ai/v1", k, ["gpt-oss-120b", "llama-3.3-70b", "qwen-3-32b"], prefer=["gpt-oss-120b", "llama-3.3-70b", "qwen-3-235b-a22b-instruct-2507"])
        out.append(Provider("cerebras", "https://api.cerebras.ai/v1", k, cm, best=cm[:2]))
    if k := os.environ.get("NVIDIA_API_KEY"):  # build.nvidia.com: free, no card, about 40 requests/min
        nm = discover_openai_compat("https://integrate.api.nvidia.com/v1", k, ["openai/gpt-oss-120b", "meta/llama-3.3-70b-instruct", "qwen/qwen3-next-80b-a3b-instruct"],
                                    prefer=["openai/gpt-oss-120b", "meta/llama-3.3-70b-instruct", "qwen/qwen3-next-80b-a3b-instruct", "mistralai/mistral-large-3-675b-instruct-2512"])
        out.append(Provider("nvidia", "https://integrate.api.nvidia.com/v1", k, nm, best=nm[:2]))
    if k := os.environ.get("INCEPTION_API_KEY"):  # one-time 100M free tokens, no card
        im = discover_openai_compat("https://api.inceptionlabs.ai/v1", k, ["mercury-2", "mercury"])
        out.append(Provider("inception", "https://api.inceptionlabs.ai/v1", k, im, best=im[:1]))
    if k := os.environ.get("SAMBANOVA_API_KEY"):
        sm = discover_openai_compat("https://api.sambanova.ai/v1", k, ["Meta-Llama-3.3-70B-Instruct", "gpt-oss-120b"], prefer=["gpt-oss-120b", "Meta-Llama-3.3-70B-Instruct"])
        out.append(Provider("sambanova", "https://api.sambanova.ai/v1", k, sm, best=sm[:2]))
    if k := os.environ.get("MISTRAL_API_KEY"):
        out.append(Provider("mistral", "https://api.mistral.ai/v1", k, ["mistral-small-latest", "open-mistral-nemo"], best=["mistral-large-latest", "mistral-small-latest"]))
    if k := os.environ.get("GITHUB_MODELS_TOKEN"):
        out.append(Provider("github", "https://models.github.ai/inference", k, ["openai/gpt-4.1-mini", "openai/gpt-4o-mini"], best=["openai/gpt-4.1"]))
    if k := os.environ.get("OPENROUTER_API_KEY"):
        out.append(Provider("openrouter", "https://openrouter.ai/api/v1", k, [os.environ.get("OPENROUTER_MODEL", "meta-llama/llama-3.3-70b-instruct:free")]))
    return out


class LLM:
    def __init__(self, providers: list | None = None, log=print):
        self.providers = providers if providers is not None else providers_from_env()
        self.calls = 0
        self.log = log
        self.by_provider: dict[str, int] = {}
        self.last_model = ""
        self.sleep = time.sleep

    @property
    def available(self) -> bool:
        return bool(self.providers)

    def complete(self, system: str, user: str, *, want_json: bool = True, temperature: float = 0.8, max_tokens: int = 6000, tier: str = "bulk"):
        """Returns parsed JSON when want_json, else text. Fails over across providers and models.
        tier="best" tries the strongest models first (scripts, editor); "bulk" tries the highest-quota ones (topic ideas).
        Busy-server errors (503 and friends) are retried with backoff and never mark a model dead; only a spent
        quota or a retired model does."""
        if not self.providers:
            raise LLMError("no LLM key configured (set GEMINI_API_KEY, GROQ_API_KEY or OPENROUTER_API_KEY)")
        last = ""
        for sweep in range(3):  # after a full sweep where everything was merely busy, wait and sweep again
            busy = False
            for prov in self.providers:
                if getattr(prov, "cool_until", 0) > time.monotonic() and any(getattr(p, "cool_until", 0) <= time.monotonic() for p in self.providers if p is not prov):
                    continue  # this provider was busy a moment ago and another one is free: do not wait on it
                best = getattr(prov, "best", [])
                order = (best + [m for m in prov.models if m not in best]) if tier == "best" and best else prov.models
                for model in order:
                    if model in prov.dead:
                        continue
                    if getattr(prov, "cool_until", 0) > time.monotonic() and len(self.providers) > 1:
                        break
                    tries = 0
                    while tries < 3:
                        tries += 1
                        try:
                            self.calls += 1
                            text = prov.chat(model, system, user, temperature, max_tokens, want_json)
                            result = extract_json(text) if want_json else text
                            prov.busy_hits = 0  # noqa
                            self.last_model = f"{prov.name}:{model}"
                            self.by_provider[self.last_model] = self.by_provider.get(self.last_model, 0) + 1
                            return result
                        except LLMError as e:
                            last = f"{prov.name}/{model}: {e}"
                            msg = str(e)
                            low = msg.lower()
                            if msg.startswith(("500", "502", "503", "504", "network")) or "high demand" in low or "unavailable" in low:
                                busy = True
                                prov.busy_hits = getattr(prov, "busy_hits", 0) + 1
                                if getattr(prov, "busy_hits", 0) >= 2 and len(self.providers) > 1:
                                    prov.cool_until = time.monotonic() + 600  # skip this provider for 10 minutes
                                    break
                                self.sleep(min(60, 8 * 2 ** (tries - 1)))  # 8s, 16s, 32s
                                continue
                            if msg.startswith("429"):
                                if "perminute" in low or "per minute" in low or "rpm" in low:
                                    prov.busy_hits = getattr(prov, "busy_hits", 0) + 1
                                    if getattr(prov, "busy_hits", 0) >= 2 and len(self.providers) > 1:
                                        prov.cool_until = time.monotonic() + 300
                                        break
                                    self.sleep(25)  # a per-minute limit: wait it out, then try again
                                    busy = True
                                    continue
                                prov.dead.add(model)  # daily quota gone, or this model is not on the free tier
                                prov.busy_hits = getattr(prov, "busy_hits", 0) + 1
                                if getattr(prov, "busy_hits", 0) >= 4 and len(self.providers) > 1:
                                    prov.cool_until = time.monotonic() + 900
                                break
                            if msg.startswith(("403", "404", "401")):
                                prov.dead.add(model)  # not allowed, or retired
                                break
                            if "not valid JSON" in msg:
                                continue  # one more try with the same model
                            self.sleep(3 * tries)
                    self.log(f"  llm: {last[:160]}")
            if not busy:
                break
            self.log(f"  llm: every model is busy; waiting before sweep {sweep + 2}")
            self.sleep(60)
        raise LLMError(f"all providers failed; last: {last}")
