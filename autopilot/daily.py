"""The daily planner: writes tomorrow's (and the next two days') specs for every channel that is short of videos.

Order of truth: a spec already in specs/<date>/ (Claude wrote it, or an earlier run did) always wins. This only
fills gaps, so the factory keeps running with or without Claude, a laptop or a human."""
from __future__ import annotations

import datetime as dt
import json
import os
import time
import tempfile
import pathlib
import re

from engine.spec_check import problems

from . import insights, prompts, market
from .directors import director_for
from .ground import ground, ground_news, news_items
from .llm import LLM, LLMError
from .normalize import speakable
from . import schemas
from .playbooks import PLAYBOOKS, cadence_for
from .slots import choose, atlas_daily_slots, slot_key

ROOT = pathlib.Path(__file__).resolve().parent.parent
SPECS = pathlib.Path(os.environ.get("CONTINUUM_SPEC_DIR") or (ROOT / "specs")).resolve()
DISCLOSURE = "Narration is a synthetic voice. Script and visuals are produced with AI tools and checked by automated quality gates."  # shown on every video


def _tokens(s: str) -> set[str]:
    return {w for w in re.findall(r"[a-z0-9]+", s.lower()) if len(w) > 2}


def as_obj(data, list_key: str) -> dict:
    """Models sometimes answer with a bare list. Treat it as the value of list_key; reject anything else."""
    if isinstance(data, dict):
        return data
    if isinstance(data, list):
        if len(data) == 1 and isinstance(data[0], dict) and list_key in data[0]:
            return data[0]
        return {list_key: data}
    raise LLMError("reply was not a JSON object")


def too_similar(title: str, others: list[str], limit: float = 0.6) -> bool:
    a = _tokens(title)
    return any(a and (len(a & _tokens(o)) / len(a | _tokens(o))) >= limit for o in others)


def network_topics(exclude: str, days: int = 21) -> list[str]:
    """Topics and titles every OTHER channel made lately, so two channels never publish the same idea in the same weeks."""
    out: list[str] = []
    cutoff = (dt.date.today() - dt.timedelta(days=days)).isoformat()
    for p in SPECS.glob("*/*.json"):
        if p.parent.name < cutoff:
            continue
        try:
            s = json.loads(p.read_text())
        except json.JSONDecodeError:
            continue
        if s.get("channel") != exclude:
            out += [s.get("title", ""), (s.get("meta") or {}).get("topic", "")]
    return [x for x in out if x]


def recent_titles(channel: str) -> list[str]:
    titles = [e["title"] for e in insights.load("ledger.json", []) if e["channel"] == channel]
    for p in SPECS.glob("*/*.json"):
        try:
            s = json.loads(p.read_text())
        except json.JSONDecodeError:
            continue
        if s.get("channel") == channel:
            titles.append(s.get("title", ""))
    return titles


def exemplar(channel: str, fmt: str) -> str:
    """A compact real spec to copy the shape from (same channel if there is one, otherwise any)."""
    # Never seed one channel with a different channel's animation grammar.
    # This previous fallback homogenized brand-new channels across the network.
    best = None
    for p in sorted(SPECS.glob("*/*.json"), reverse=True):
        try:
            s = json.loads(p.read_text())
        except (json.JSONDecodeError, OSError):
            continue
        if s.get("format") == fmt and s.get("channel") == channel:
            best = s
            break
    if not best:
        return ""
    keep = {"title": best["title"], "thumb": best.get("thumb"), "scenes": best["scenes"][: 6 if fmt == "short" else 5]}
    return "EXAMPLE OF THE SHAPE (different topic; do not copy content):\n" + json.dumps(keep, ensure_ascii=False)[:2800]


class EpisodeCallLimit(LLMError):
    pass


class Planner:
    def __init__(self, llm: LLM, *, max_calls: int = 400, log=print):
        self.llm, self.max_calls, self.log = llm, max_calls, log
        self.deadline = time.monotonic() + float(os.environ.get("AUTOPILOT_MAX_MINUTES", "34")) * 60
        self.episode_call_limit: int | None = None
        self.topics: dict[tuple, list[dict]] = {}
        self.long_outlines: dict[tuple[str, str], dict] = {}

    def _call(self, system: str, user: str, **kw):
        limit = self.max_calls
        if self.episode_call_limit is not None:
            limit = min(limit, self.episode_call_limit)
        try:
            return self.llm.complete(system, user, max_calls=limit, deadline=self.deadline, **kw)
        except LLMError as error:
            if limit < self.max_calls and self.llm.calls >= limit and str(error) == "call budget for this run is used up":
                raise EpisodeCallLimit("provider attempt limit reached for this episode") from error
            raise

    # ---- topics ---------------------------------------------------------------------------------
    def pick_topic(self, channel: str, fmt: str) -> dict:
        pb = PLAYBOOKS[channel]
        pool = self.topics.get((channel, fmt))
        if not pool and pb.get("grounding") == "news":
            seen = {e.get("topic", "") for e in insights.load("ledger.json", []) if e["channel"] == channel}
            used = {m for p in SPECS.glob("*/*.json") for m in [json.loads(p.read_text()).get("meta", {}).get("news_url", "")] if m} if SPECS.exists() else set()
            items = [i for i in news_items() if i["url"] not in used and i["title"] not in seen]
            if not items:
                raise LLMError("no fresh news items")
            self.topics[(channel, fmt)] = [{"topic": i["title"], "axis": "news", "news": i} for i in items]
            pool = self.topics[(channel, fmt)]
        if not pool:
            axes = insights.axis_weights(channel, pb["axes"])
            recent = recent_titles(channel)[-40:]
            user = (
                f"Channel: {channel}\nPromise: {pb['promise']}\nAudience: {pb['audience']}\nFormat: {fmt}\n"
                f"Subject areas (prefer earlier ones, but rotate): {json.dumps(axes)}\n"
                f"Already made (do NOT repeat or paraphrase): {json.dumps(recent)}\n"
                f"OWN-CHANNEL VERIFIED ANALYTICS:\n{insights.guidance(channel, fmt)}\n"
                f"INDEPENDENT PUBLIC DEMAND SIGNALS (noncausal):\n{market.guidance(channel)}\n"
                f"Production constraints: {pb.get('topic_constraints', 'Follow the channel promise and subject areas.')}\n\n"
                'Brainstorm 8 video topics most likely to hold attention. Return JSON: {"topics":[{"topic":"...","axis":"one subject area","wiki_query":"2-4 words to find a Wikipedia article with the facts","why":"one line"}]} ranked best first.'
            )
            data = as_obj(self._call("You are a sharp YouTube strategist. Reply with JSON only.", user,
                                     temperature=0.9, schema=schemas.TOPICS), "topics")
            others = network_topics(channel)
            pool = [t for t in data.get("topics", []) if isinstance(t, dict) and t.get("topic") and not too_similar(t["topic"], recent) and not too_similar(t["topic"], others, 0.5)]
            if not pool:
                raise LLMError("no fresh topics")
            self.topics[(channel, fmt)] = pool
        return pool.pop(0)

    # ---- drafting --------------------------------------------------------------------------------
    def _system(self, channel: str) -> str:
        pb = PLAYBOOKS[channel]
        parts = [
            prompts.craft_for(pb),
            f"CHANNEL: {channel}\nPromise: {pb['promise']}\nAudience: {pb['audience']}\nVoice: {pb['voice']}\nHook: {pb['hook']}\n"
            f"Never: {'; '.join(pb['avoid'])}\nPreferred visuals: {', '.join(pb['scene_bias'])}",
            director_for(channel).prompt(),
        ]
        if pb.get("fiction"):
            parts.append(prompts.FICTION)
        if pb.get("host"):
            h = pb["host"]
            parts.append(prompts.HOST.format(name=h["name"], cast=json.dumps({**h["cast"], "name": h["name"], "action": "talk"})))
        if pb.get("persona"):
            parts.append(prompts.PERSONA.format(who=channel))
        if pb.get("lang") == "hi":
            parts.append("LANGUAGE: Hindi. Write every spoken line (say) in Devanagari script, simple and conversational; keep common English words in Latin script where people say them that way.")
        if pb.get("rule"):
            parts.append("CHANNEL RULE: " + pb["rule"])
        return "\n\n".join(parts)

    def draft_short(self, channel: str, topic: dict, g: dict, fixes: list[str] | None = None) -> dict:
        pb = PLAYBOOKS[channel]
        brief = prompts.SHORT_SPEC.replace("{words}", str(pb["short_words"]))
        if pb["slug"] == "10sec":
            brief = ("Return JSON with title, thumb, description, tags, scenes. "
                     "Make an actual 9-to-14-second scientific Short, NOT a 40-second video: "
                     "18-26 spoken words TOTAL in exactly 4 scenes. "
                     "HARD CONSTRAINT: each scene.say must be 4 to 6 words; "
                     "count the words before responding; never exceed 26 across all four scenes. "
                     "Scene 1 is a 4-6-word title hook; "
                     "scene 2 is a 4-6-word quantified or observed fact; "
                     "scene 3 is a 4-6-word visual cause; "
                     "scene 4 is a 4-6-word end-card payoff, never a generic CTA. "
                     "Use distinct visuals. Never add padding to reach a longer runtime. "
                     "Ground every specific claim. No experiment that requires risky materials.")
        user = (
            f"TOPIC: {topic['topic']}\n\nGROUNDING (the only source of specific facts):\n{g['text'] or '(none found: use only settled textbook knowledge and say roughly)'}\n\n"
            + brief + "\n\n" + exemplar(channel, "short")
        )
        # Small models sometimes return the visual-only shape
        # {"type":"title","text":"..."} as a scene. That format has no
        # spoken narration, and must not be silently treated as a valid script.
        shape = (
            "\n\nSTRICT OUTPUT SCHEMA (CHECK EVERY SCENE BEFORE RETURNING): "
            "Each element of scenes MUST be exactly a scene object with a NONEMPTY "
            "spoken sentence string in `say`, and its display instructions in `show`. "
            "Example: {\"say\":\"Here is what the number really measures.\", "
            "\"show\":{\"type\":\"number\",\"value\":12,\"unit\":\"km\",\"label\":\"Distance\"}}. "
            "DO NOT put type, text, from, value, or scene props directly in a scene. "
            f"Write about {pb['short_words']} spoken words across all scenes, "
            "except the ten-second channel uses exactly 4 scenes with 4-6 words per say. "
            "No invented facts, claims, quotes or tests; use the supplied grounding."
        )
        user += shape
        if fixes:
            user += "\n\nYOUR PREVIOUS ATTEMPT WAS REJECTED. Fix all of these:\n- " + "\n- ".join(fixes)
        system = self._system(channel)
        raw = as_obj(self._call(system, user, temperature=0.65, tier="best",
                                schema=schemas.short_script(channel)), "scenes")
        scenes = raw.get("scenes")
        if (isinstance(scenes, list) and scenes and any(
            isinstance(scene, dict) and not str(scene.get("say", "")).strip()
            for scene in scenes
        )):
            # A single bounded repair call may re-author voiceover from the
            # original grounding and visual plan. Never turn on-screen text into
            # unverified narration or skip the normal editorial quality gates.
            repair = (
                f"TOPIC: {topic['topic']}\nSOURCE GROUNDING: {g['text']}\n"
                + brief + shape + "\n\n"
                "REWRITE THIS MALFORMED JSON. It has visual fields at the scene level "
                "and lacks say. Give every scene a distinct, factual spoken sentence "
                "in say. Nest its original visuals under show, preserving visual "
                "variety and the topic. Do not fill with repetition or unsupported "
                "claims. Return the complete corrected JSON object only.\n"
                + json.dumps(raw, ensure_ascii=False)
            )
            return as_obj(self._call(system, repair, temperature=0.35, tier="best",
                                     schema=schemas.short_script(channel)), "scenes")
        return raw

    def draft_long(self, channel: str, topic: dict, g: dict, fixes: list[str] | None = None) -> dict:
        pb = PLAYBOOKS[channel]
        words = pb["long_words"]
        n_ch = 6 if words < 1500 else 8
        per = words // n_ch
        system = self._system(channel)
        base = f"TOPIC: {topic['topic']}\n\nGROUNDING (the only source of specific facts):\n{g['text'] or '(none found: use only settled knowledge)'}\n\n"
        key = (channel, topic["topic"])
        outline = self.long_outlines.get(key)
        if outline is None:
            prompt = prompts.LONG_OUTLINE.replace("{minutes}", str(round(words / 150))).replace("{chapters}", str(n_ch))
            outline = as_obj(self._call(system, base + prompt, temperature=0.8, tier="best",
                                        schema=schemas.long_outline(n_ch)), "chapters")
        chapters = [c for c in outline.get("chapters", []) if isinstance(c, dict)][:n_ch]
        if len(chapters) < 4:
            raise LLMError("outline too short")
        self.long_outlines[key] = outline
        scenes: list[dict] = []
        for i, ch in enumerate(chapters, 1):
            first = "This chapter opens the video: first scene type \"title\", then deliver the promise inside 20 seconds. " if i == 1 else ""
            last = "This is the last chapter: answer the title, then finish with an \"end\" scene. " if i == len(chapters) else ""
            fields = {}
            for placeholder, field in (("name", "name"), ("beats", "beats"), ("loop", "open_loop")):
                value = ch.get(field)
                fields[placeholder] = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False) if value is not None else ""
            prompt = (prompts.CHAPTER.replace("{i}", str(i)).replace("{n}", str(len(chapters)))
                      .replace("{words}", str(per)).replace("{scenes}", str(max(3, per // 55)))
                      .replace("{first}", first).replace("{last}", last))
            prompt = re.sub(r"\{(name|beats|loop)\}", lambda match: fields[match[1]], prompt)
            if scenes:
                prompt += f"\nPrevious chapter ended with: {scenes[-1].get('say', '')}"
            if fixes:
                prompt += "\nEditor notes to apply: " + "; ".join(fixes[:4])
            part = as_obj(self._call(system, base + prompt, temperature=0.8, tier="best",
                                     schema=schemas.chapter(channel)), "scenes")
            scenes += [x for x in part.get("scenes", []) if isinstance(x, dict)]
        return {**{k: outline.get(k) for k in ("title", "thumb", "description", "tags")}, "scenes": scenes}

    @staticmethod
    def _lock_identity(pb: dict, item: dict) -> None:
        """Keep a channel's recurring face the same in every video: a persona's name, or the host's clay look."""
        show = item.get("show") or {}
        from engine.b3d import SCENE_NAMES
        if show.get("type") in SCENE_NAMES:  # the model wrote the 3D scene name as the type: wrap it properly
            name = show.pop("type")
            params = show.pop("params", None) or {k: show.pop(k) for k in list(show) if k not in ("title", "hud", "clock", "fallback")}
            show.update({"type": "b3d", "scene": name, "params": params})
        if show.get("type") == "b3d" and not show.get("fallback"):
            show["fallback"] = {"type": "say", "text": (item.get("say") or "")[:60]}
        if pb.get("persona") and show.get("type") == "persona":
            show["who"] = pb["persona"]
            if show.get("look") not in ("portrait", "place"):
                show["look"] = "portrait"
        host = pb.get("host")
        if host and show.get("type") == "b3d" and show.get("scene") == "clay":
            params = show.setdefault("params", {})
            cast = [c for c in params.get("cast", []) if isinstance(c, dict)] or [{}]
            cast[0] = {**cast[0], **host["cast"], "name": host["name"], "action": cast[0].get("action", "talk")}
            params["cast"] = cast[:5]

    # ---- finishing and gates ---------------------------------------------------------------------
    def finish(self, channel: str, fmt: str, raw: dict, topic: dict, g: dict, spec_id: str, when: dt.datetime) -> dict:
        pb = PLAYBOOKS[channel]
        scenes = []
        for sc in raw.get("scenes", []):
            if not isinstance(sc, dict):
                continue
            say = speakable(str(sc.get("say", "")).strip())
            show = sc.get("show") if isinstance(sc.get("show"), dict) else None
            item: dict = {"say": say}
            if show and show.get("type") and (show["type"] != "say" or show.get("hero") or show.get("text")):
                item["show"] = show
            if sc.get("emoji"):
                item["emoji"] = sc["emoji"]
            if say:
                self._lock_identity(pb, item)
                scenes.append(item)
        if scenes and (scenes[0].get("show") or {}).get("type") != "title":
            scenes[0]["show"] = {"type": "title", "text": raw.get("thumb") or raw.get("title", "")[:48], "kicker": channel}
        if scenes and (scenes[-1].get("show") or {}).get("type") != "end":
            scenes.append({"say": "That is the whole story. Come back tomorrow for another one.", "show": {"type": "end", "text": "New video every day"}})
        if pb["slug"] == "lowbat":
            from engine.pip import fill_phone_states
            fill_phone_states(scenes)
        title = str(raw.get("title", "")).strip().strip('"')[:100]
        if fmt == "short" and "#shorts" not in title.lower() and len(title) <= 90:
            title += " #shorts"
        desc = str(raw.get("description", "")).strip()
        srcs = "\n".join(f"- {s['title']}: {s['url']}" for s in g["sources"])
        label = g.get("label") or "Sources (Wikipedia, CC BY-SA)"
        notes = []
        if pb.get("fiction"):
            notes.append("This is a work of fiction.")
        if pb.get("host"):
            notes.append(f"The host, {pb['host']['name']}, is an animated AI character, not a real person.")
        if pb.get("persona"):
            notes.append(f"{channel} is an AI-generated persona, not a real person.")
        if pb["slug"] == "benchwise":
            notes.append("Some links may be affiliate links; if you buy through them the channel may earn a commission at no extra cost to you. Information is from published specifications; the channel has not tested these products.")
        if pb["slug"] == "money":
            notes.append("This is education, not financial advice.")
        if pb["slug"] == "survive":
            notes.append("General information only. In an emergency call your local emergency number.")
        if pb["slug"] == "onedollar":
            notes.append("These are plans, not tested builds. Take care with tools and heat.")
        desc = (desc + (f"\n\n{label}:\n" + srcs if srcs else "") + (f"\n\n{pb['disclose']}" if pb.get("disclose") else "")
                + ("\n\n" + " ".join(notes) if notes else "") + f"\n\n{DISCLOSURE}").strip()
        tags = [str(t) for t in (raw.get("tags") or [])][:12]
        tags = list(dict.fromkeys(tags + pb["tags"]))[:15]
        return {
            "id": spec_id, "channel": channel, "format": fmt, "title": title, "thumb": str(raw.get("thumb") or "")[:60] or title[:40],
            "description": desc, "tags": tags, "links": pb["links"], "publishAt": when.strftime("%Y-%m-%dT%H:%M:00Z"),
            "meta": {"generator": "autopilot", "creativeDirector": {
                         "id": channel, "fingerprint": director_for(channel).fingerprint(), "version": 1,
                         "camera": director_for(channel).camera, "captions": director_for(channel).captions},
                     "topic": topic["topic"], "axis": topic.get("axis", ""), "slot": slot_key(when),
                     **({"news_url": topic["news"]["url"]} if topic.get("news") else {})},
            "scenes": scenes,
        }

    def critic(self, channel: str, spec: dict, g: dict) -> dict:
        script = "\n".join(
            f"{scene['say']} | On screen: {json.dumps(scene.get('show', {}), ensure_ascii=False)}"
            for scene in spec["scenes"]
        )
        pb = PLAYBOOKS[channel]
        facts = f"{pb['promise']} {pb.get('rule', '')}\n{director_for(channel).prompt()}".strip()
        fic = "This is a FICTION channel: invented characters and events are allowed and are not 'unsupported claims'. Only real-world facts need support.\n" if pb.get("fiction") else ""
        user = (f"CHANNEL BRIEF AND PRODUCTION CONSTRAINTS (violations require revision): {facts}\n{fic}GROUNDING:\n{g['text'][:6000]}\n\n"
                f"TITLE: {spec['title']}\nDESCRIPTION: {spec['description']}\nSCRIPT:\n{script}")
        review = as_obj(self._call(prompts.CRITIC, user, temperature=0.2, max_tokens=1200,
                                    tier="best", schema=schemas.EDITOR), "fixes")
        if type(review.get("pass")) is not bool:
            raise LLMError("editor response is missing a valid pass decision")
        for key in ("fixes", "unsupported_claims"):
            values = review.get(key)
            if not isinstance(values, list) or any(not isinstance(value, str) or not value.strip() for value in values):
                raise LLMError(f"editor response has an invalid {key} list")
        minimums = {"hook": 6, "originality": 6, "accuracy": 7}
        for key, minimum in minimums.items():
            score = review.get(key)
            if type(score) is not int or not 1 <= score <= 10:
                raise LLMError(f"editor response has an invalid {key} score")
            if score < minimum:
                review["pass"] = False
                review["fixes"].append(f"Improve {key}: scored {score}, needs {minimum}")
        return review

    def make(self, channel: str, fmt: str, spec_id: str, when: dt.datetime) -> dict | None:
        pb = PLAYBOOKS[channel]
        topic = self.pick_topic(channel, fmt)
        if topic.get("news"):
            g = ground_news(topic["news"])
        else:
            g = ground(topic.get("wiki_query") or topic["topic"]) if pb.get("grounded") else {"text": "", "sources": []}
        draft = self.draft_short if fmt == "short" else self.draft_long
        fixes: list[str] = []
        titles = recent_titles(channel)
        for attempt in range(3):
            raw = draft(channel, topic, g, fixes or None)
            spec = self.finish(channel, fmt, raw, topic, g, spec_id, when)
            bad = problems(spec, spec_id[:10], strict=True)
            if too_similar(spec["title"], titles, 0.7):
                bad.append("title is too close to an earlier video; choose a different angle")
            if pb.get("lang") == "hi":
                letters = [ch for sc in spec["scenes"] for ch in sc["say"] if ch.isalpha()]
                dev = sum("\u0900" <= ch <= "\u097f" for ch in letters)
                if letters and dev / len(letters) < 0.6:
                    bad.append("write every spoken line in Devanagari Hindi script, not Roman letters (Hinglish in Latin script is not allowed)")
            if pb.get("persona"):
                n_persona = sum((sc.get("show") or {}).get("type") == "persona" for sc in spec["scenes"])
                need = 4 if fmt == "short" else 8
                if n_persona < need:
                    bad.append(f"use the persona scene on at least {need} scenes (only {n_persona}); the persona's face must carry the video")
            if pb["slug"] == "lowbat":
                actions = [(scene.get("show") or {}).get("action") for scene in spec["scenes"]
                           if (scene.get("show") or {}).get("type") == "pip"]
                if not all(action in actions for action in ("notice", "reach", "slip", "reset")):
                    bad.append("stage all four Pip actions: notice, reach, slip and reset")
            if too_similar(spec["title"], network_topics(channel), 0.55):
                bad.append("another channel in the network covered this idea recently; choose a different angle")
            if not bad:
                review = self.critic(channel, spec, g)
                if review["pass"] and not review.get("unsupported_claims") and not review.get("fixes"):
                    spec["meta"]["review"] = {
                        "pass": True,
                        "hook": review["hook"], "originality": review["originality"],
                        "accuracy": review["accuracy"],
                        "unsupported_claims": [], "fixes": [],
                    }
                    spec["meta"]["model"] = self.llm.last_model
                    if (self.llm.last_model or "").startswith("ollama:"):
                        # One small local model evaluating itself is not an
                        # independent fact-check or creative approval.
                        # Preserve its draft and scores, but deny render/publish
                        # eligibility until a separate editor checks the work.
                        spec["meta"]["review"]["pass"] = False
                        spec["meta"]["reviewStatus"] = "LOCAL_DRAFT_INDEPENDENT_REVIEW_REQUIRED"
                    return spec
                bad = [f"editor: {f}" for f in (review.get("fixes") or ["raise hook and accuracy"])][:5] + [f"unsupported: {c}" for c in (review.get("unsupported_claims") or [])][:3]
            self.log(f"  {spec_id}: attempt {attempt + 1} rejected ({len(bad)} issues): {bad[0][:100]}")
            fixes = bad
        return None


def plan(days: list[dt.date], llm: LLM, now: dt.datetime | None = None, *, only: list[str] | None = None, max_calls: int = 400, log=print) -> dict:
    """Fill every channel's quota on each date. Returns {'written': [paths], 'skipped': [...], 'failed': [...]}."""
    now = now or dt.datetime.now(dt.timezone.utc)
    planner = Planner(llm, max_calls=max_calls, log=log)
    out = {"written": [], "skipped": [], "failed": []}
    ledger = insights.load("ledger.json", [])
    channels = [channel for channel in PLAYBOOKS if not only or channel in only]
    if channels:
        # A time-limited network run must not always start with the same channels.
        window = int(now.timestamp() // (15 * 60))
        start = window % len(channels)
        channels = channels[start:] + channels[:start]
    strikes = 0
    for day in sorted(days):
        folder = SPECS / day.isoformat()
        by_channel: dict[str, list[dict]] = {}
        for path in folder.glob("*.json"):
            try:
                saved = json.loads(path.read_text())
            except json.JSONDecodeError:
                continue
            by_channel.setdefault(saved.get("channel", ""), []).append(saved)
        for channel in channels:
            pb = PLAYBOOKS[channel]
            existing = by_channel.get(channel, [])
            occupied = []
            for saved in existing:
                when = saved.get("publishAt")
                if isinstance(when, str):
                    try:
                        parsed = dt.datetime.fromisoformat(when.replace("Z", "+00:00"))
                    except ValueError:
                        continue
                    if parsed.tzinfo is not None:
                        occupied.append(parsed)
            atlas_slots = None
            if channel == "Counterfactual Atlas":
                goals = cadence_for(channel, day)
                missing_short = max(0, goals.get("short", 0) - sum(item.get("format") == "short" for item in existing))
                missing_long = max(0, goals.get("long", 0) - sum(item.get("format") == "long" for item in existing))
                atlas_slots = atlas_daily_slots(
                    day, now, insights.slot_stats(channel, "short"), insights.slot_stats(channel, "long"),
                    existing=tuple(occupied), need_short=missing_short, need_long=missing_long,
                )
            for fmt in ("short", "long"):
                want = cadence_for(channel, day).get(fmt, 0)
                have = sum(saved.get("format") == fmt for saved in existing)
                missing = want - have
                if missing <= 0:
                    continue
                slots = (atlas_slots[fmt] if atlas_slots is not None else
                         choose(channel, fmt, missing, day, insights.slot_stats(channel, fmt), now,
                                occupied=tuple(occupied)))
                prefix = f"{pb['slug']}-{fmt[0]}"
                serial = 0
                for when in slots:
                    while True:
                        serial += 1
                        path = folder / f"{prefix}{serial}.json"
                        if not path.exists():
                            break
                    sid = f"{day.isoformat()}-{path.stem}"
                    planner.episode_call_limit = llm.calls + (18 if fmt == "short" else 36)
                    try:
                        spec = planner.make(channel, fmt, sid, when)
                    except (LLMError, AttributeError, TypeError, KeyError, ValueError) as e:
                        out["failed"].append(f"{sid}: {type(e).__name__}: {e}")
                        log(f"  {sid}: stopped ({str(e)[:140]})")
                        if "budget" in str(e):
                            return out
                        if isinstance(e, EpisodeCallLimit):
                            continue
                        strikes += 1
                        if strikes >= 4:  # four spec failures in a row: the models are down, stop and let the next run retry
                            return out
                        continue
                    if not spec:
                        out["failed"].append(f"{sid}: rejected by quality gates")
                        continue
                    strikes = 0
                    occupied.append(when)
                    folder.mkdir(parents=True, exist_ok=True)
                    with tempfile.NamedTemporaryFile(mode="w", dir=folder, encoding="utf-8", delete=False) as output:
                        draft_path = pathlib.Path(output.name)
                    try:
                        draft_path.write_text(json.dumps(spec, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
                        draft_path.replace(path)
                    finally:
                        draft_path.unlink(missing_ok=True)
                    ledger.append({"id": sid, "channel": channel, "format": fmt, "title": spec["title"], "axis": spec["meta"]["axis"], "slot": spec["meta"]["slot"], "publishAt": spec["publishAt"]})
                    insights.save("ledger.json", ledger[-1500:])
                    rel = str(path.relative_to(ROOT)) if path.is_relative_to(ROOT) else str(path)
                    out["written"].append(rel)
                    log(f"  wrote {rel}: {spec['title']}")
    return out


def inventory(days: list[dt.date], only: list[str] | None = None) -> list[dict]:
    """Report spec coverage independently of the planner's stop condition."""
    channels = [channel for channel in PLAYBOOKS if not only or channel in only]
    rows = []
    for day in sorted(set(days)):
        counts: dict[tuple[str, str], set[str]] = {}
        for path in (SPECS / day.isoformat()).glob("*.json"):
            try:
                spec = json.loads(path.read_text())
                if not isinstance(spec, dict) or spec.get("id") != f"{day}-{path.stem}":
                    continue
                channel, fmt = spec.get("channel"), spec.get("format")
                if channel in channels and fmt in ("short", "long"):
                    counts.setdefault((channel, fmt), set()).add(spec["id"])
            except (OSError, ValueError):
                continue
        for channel in channels:
            for fmt, target in cadence_for(channel, day).items():
                if target:
                    present = len(counts.get((channel, fmt), ()))
                    rows.append({"date": day.isoformat(), "channel": channel, "format": fmt,
                                 "target": target, "specs": present, "missing": max(0, target - present)})
    return rows
