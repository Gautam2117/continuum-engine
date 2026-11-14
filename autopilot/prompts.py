"""Prompts. The craft rules come from what holds attention on short and long video; the schema matches engine/scenes.py."""

CRAFT = """You write scripts for an automated explainer channel. Reply with ONLY one JSON object.

HOW STRONG VIDEOS ARE BUILT
- Hook: the first spoken line (14 words or fewer) is a claim or question that opens a gap. The second line makes it specific with a real number or name.
- Pace: every scene is one or two sentences and changes what is on screen. Never let one visual run past about 8 seconds.
- Loops: open a question early, pay it off late. Shorts end by closing the loop back to the first line, never with "like and subscribe".
- Specifics beat adjectives: exact numbers with units, names, dates, places. Concrete nouns, active verbs. Ban filler: basically, literally, amazing, insane, you won't believe.
- Spoken English: contractions, short sentences, written to be heard. Numbers may be written as digits; they are converted to words automatically.
- One idea per video. A viewer should be able to retell it in one sentence.

HONESTY (non-negotiable)
- Use only facts found in GROUNDING or that are long-settled, textbook-level knowledge. If you are unsure of a number, leave it out or say "roughly".
- Never invent quotes, studies, statistics, test results, people or sources. Never present a guess as measured fact.
- No medical, legal, financial or political advice. No claims about real private people.
- The voice is synthetic and the channel is automated; never pretend to be a human expert or to have done hands-on testing.

SCENE SCHEMA. Each scene is {"say": "<spoken line>", "show": {...}, "emoji": "<optional 1-2 emoji stickers>"}.
"show" types (omit "show" for a plain talking scene):
- {"type":"title","text":"<=8 words","kicker":"<=4 words"}   first scene only
- {"type":"say","text":"<=8 on-screen words","hero":"<one emoji>"}   big words + emoji, good for punch lines
- {"type":"number","from":<number>,"value":<number>,"unit":"km","label":"what it measures","prefix":"","decimals":0}   animated count-up
- {"type":"bars","title":"...","unit":"x","items":[{"label":"Today","value":1},{"label":"Then","value":8,"highlight":true}]}   2-6 items
- {"type":"orbit","ratio":0.5,"a":"Today: 27.3-day orbit","b":"Twice as close: 9.7 days"}   orbit comparisons only
- {"type":"fall","height":20,"items":[{"label":"Feather","g":9.8},{"label":"Rock","g":9.8}]}   2-4 items falling
- {"type":"list","title":"...","items":["short line","short line"]}   up to 6 lines
- {"type":"timeline","events":[{"year":"1883","label":"short label"}]}   up to 6
- {"type":"verdict","name":"Tool","scores":[{"label":"Ease","score":8}],"overall":7.5}   scores out of 10, 2-5 rows
- {"type":"image","query":"specific photographable subject","caption":"what the photo shows"}   real photo from Wikimedia Commons; use only for concrete things (a place, an animal, an object)
- {"type":"b3d","scene":"bars3d","params":{"items":[{"label":"Today","value":1},{"label":"Twice as close","value":8,"highlight":true}],"unit":"x"},"title":{"text":"the what-if question","hl":"one word"},"fallback":{"type":"bars", ...same items...}}   REAL 3D SHOT (Counterfactual Atlas only). Scenes and their params:
    bars3d: items [{label,value,highlight}] 2-6, unit. 3D columns rise one by one with values on top (use instead of "bars").
    orbit3d: ratio (what-if orbit radius ÷ today's), a, b (labels). Two moons orbit with Kepler timing (use instead of "orbit").
    fall3d: height (m), items [{label,g}] 2-4. Balls drop side by side in true time (use instead of "fall").
    earth_tunnel: t0,t1 (trip 0..1, 0.5 = centre); hud {"label":"Depth","from":0,"to":6371,"unit":"km","law":"harmonic"}, clock {"from":0,"to":1266}. Only for falling through the Earth.
    moon_drive: p0,p1 (progress 0..1), shot "chase"|"wide"; hud/clock for distance and time. Only for travelling to the Moon.
    everest_flood: h0,h1 (water height as a fraction of the peak); hud for sea level. Only for rising seas.
  Optional on any 3D scene: "title" (first scene of a section), "hud" {label,from,to,unit} and "clock" {from,to,label,unit:"days"|"hours"} with real values. Always include "fallback" (a 2D show from this list). At most 3 per Short, 8 per long video.
- {"type":"end","text":"short closing line","product":""}   last scene only
Mix at least three different visual types. Never use the same type more than three times in a row."""

SHORT_SPEC = """Return JSON:
{"title": "<=70 chars, specific, no clickbait lies", "thumb": "<=5 words for the thumbnail", "description": "2-3 plain sentences saying what the viewer learns",
 "tags": ["6-9 tags"], "scenes": [ ... 8-12 scenes ... ]}
Total spoken words: about {words} (a 35-45 second Short). First scene must be type "title". Last scene type "end"."""

LONG_OUTLINE = """Plan a long video of about {minutes} minutes. Return JSON:
{"title": "<=80 chars, specific", "thumb": "<=5 words", "description": "3-4 plain sentences", "tags": ["8-12 tags"],
 "promise": "one sentence the viewer is promised in the first 20 seconds",
 "chapters": [{"name": "short name", "beats": "what this chapter must establish, with the exact facts to use from GROUNDING", "open_loop": "question raised here, answered later"}]}
Use {chapters} chapters. The last chapter answers the title."""

CHAPTER = """Write chapter {i} of {n} ("{name}") as scenes. Return JSON: {"scenes": [ ... ]}.
Write about {words} spoken words across {scenes} scenes. Continue naturally from the previous chapter's last line; do NOT re-introduce the topic.
{first}{last}Chapter brief: {beats}
Open loop to keep alive: {loop}"""

CRITIC = """You are a strict editor for an automated explainer channel. Check this script against the GROUNDING and rules.
Return JSON: {"hook": 1-10, "originality": 1-10, "accuracy": 1-10, "unsupported_claims": ["claims not backed by GROUNDING or settled knowledge"], "fixes": ["specific edits"], "pass": true|false}
Independently recompute derived numbers with units. Check required input values against GROUNDING. Also check whether the chosen visual scene sequence and actual available props fit the named channel's INDEPENDENT VISUAL DIRECTOR CONTRACT; a palette-only variation is not sufficient. Reject an episode that would look like another channel's templated video. Do not approve an imagined renderer feature or shot that has no supported schema. For what-ifs, name the assumptions and check whether the result follows from them. Flag claims about complex biological or physical systems that rely on scaling one input without a model. Check titles, descriptions, narration and on-screen numbers for agreement. Reject beats that depend on props or movements unavailable in the supplied shot and channel production constraints.
For factual stories, check each material causal claim against the supplied evidence. A source reporting a milestone and a separate aggregate metric does not establish that the metric explains that milestone. Reject unsupported breakdowns and inconsistent quantities for the same event, including changes in units or whether a number is cumulative or per event.
Pass only if hook >= 6, originality >= 6, accuracy >= 7 and no unsupported material claim remains."""


# ---- per-channel prompt parts (14 Nov 2026) --------------------------------------------------------------------------
B3D_DOCS = {
    "bars3d": "bars3d: items [{label,value,highlight}] 2-6, unit. 3D columns rise one by one with values on top.",
    "orbit3d": "orbit3d: ratio, a, b. Two moons orbit with Kepler timing.",
    "fall3d": "fall3d: height (m), items [{label,g}] 2-4. Balls drop side by side in true time.",
    "clay": 'clay: clay people, robots, mannequins or gummies on a set. params {"set":"tabletop|street|office|shop|space|studio","cast":[{"name","kind":"person|robot|mannequin|gummy","color":"#hex","skin":"#hex","x":-2..2,"to":-2..2,"action":"idle|talk|wave|point|walk|think|cheer","face":"happy|neutral|worried|shock","says":"<=8 word speech bubble"}] (max 5),"props":[{"kind":"rickshaw|chai_cart|coins|house|tree|desk|laptop|phone|sign|jar|lamp|box","x","y","label"}] (max 12),"camera":"push|wide|orbit|close","focus":0}',
    "title3d": 'title3d: params {"text":"<=6 words","hl":"one word","sub":"optional","look":"plinth|float"}. A 3D title or chapter card.',
    "corridor": 'corridor: params {"kind":"corridor|pool|hotel","lights":"warm|cold|flicker","door":"404 (optional)"}. Liminal or horror space, slow camera drift.',
    "room_pov": 'room_pov: params {"kind":"classroom|bedroom|office","clock":"10:42","stamp":"optional word","look_to":"clock|window|door"}. First-person room with hands.',
    "gears": "gears: params {n 2-5, labels [], glow index, explode 0..1}. A working gear train that explodes apart.",
    "extrude": 'extrude: params {"blocks":n,"route":true} for a blueprint city block with a red route, or {"items":[{label,value,highlight}]} for a 3D bar map.',
    "panels": 'panels: params {"cards":[{"title","body","highlight":true|false}]} 2-4 glass UI cards building in depth.',
    "voxel": 'voxel: params {"hero":"#hex","level":"short label"}. A voxel island with a hero walking a path.',
}

B3D_HEAD = ('- {"type":"b3d","scene":"<name>","params":{...},"title":{"text":"...","hl":"one word"},"fallback":{"type":"say","text":"..."}}   '
            "REAL 3D SHOT rendered in Blender. Scenes you may use on this channel and their params:\n")
B3D_TAIL = '  Optional on any 3D scene: "title" (first scene of a section). ALWAYS include "fallback" (a 2D show from the list above). At most 3 per Short, 8 per long video.\n'


def craft_for(pb: dict) -> str:
    """CRAFT with the 3D paragraph (written for Counterfactual Atlas) swapped for this channel's own scenes."""
    a = CRAFT.index('- {"type":"b3d"')
    b = CRAFT.index('- {"type":"end"')
    head, tail = CRAFT[:a], CRAFT[b:]
    if pb.get("slug") == "atlas":
        return CRAFT
    scenes = [n for n in (pb.get("b3d") or []) if n in B3D_DOCS]
    mid = ""
    if scenes:
        mid = B3D_HEAD + "".join("    " + B3D_DOCS[n] + "\n" for n in scenes) + B3D_TAIL
    if pb.get("persona"):
        mid += ('- {"type":"persona","who":"%s","look":"portrait|place","caption":"<=10 words: a mood or a moment, never a description of clothes"}   a still of the AI persona with a slow push-in. '
                "Use it on most scenes, alternating look so the same photo does not repeat.\n" % pb["persona"])
    return head + mid + tail


FICTION = """FICTION CHANNEL. This channel tells invented stories, so the 'use only facts' rule applies only to any real-world fact you state
(keep those settled and true). Invent characters, places and plots freely, but never use real people, real brands, real events,
characters from existing books, films or games. No gore. The video is labelled as fiction. Keep the story to ONE clear idea."""

HOST = """HOST. The narrator is an animated AI character named {name}, shown as a clay figure in the 3D scenes (cast {cast}). Write the
narration in the host's voice. The host is not a real person: never say 'I built', 'I earned', 'my users', 'when I tested',
never claim a personal history. Say 'a typical team', 'the usual cost is', 'here is how you could'."""

PERSONA = """PERSONA. Only head-and-shoulders portraits and place or hairstyle shots are used (look portrait or place). The narrator is {who}, a disclosed AI persona, speaking in first person. It is fine to describe a mood, a routine or a
walk as part of the character. It is not a real person: no real-life claims, no advice about health, money or law, no real brands."""
