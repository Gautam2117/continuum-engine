"""What each channel is, how it sounds and what it must never do. The planner reads these; the performance loop
adds to them (see insights.py). One playbook per channel the engine renders end to end.

The honesty rules matter as much as the style: these channels are sold to viewers as explainers, so nothing is
invented. Facts come from the grounding text the planner fetches, or from long-settled knowledge."""

CTA_DAYWILD = {"label": "Explore real places on your own missions with Daywild", "url": "https://daywild.continuumarc.tech"}
CTA_ARC = {"label": "More from Continuum Arc", "url": "https://continuumarc.tech"}

# Candidate publish times (UTC) the scheduler explores for a global English audience:
# 14:00 and 18:00 catch India evening, Europe afternoon and US morning; 00:30 is US prime time; 03:30 is US late-night / Asia morning.
SLOTS = ["14:00", "18:00", "00:30", "12:00", "16:00", "20:30", "03:30"]

PLAYBOOKS: dict[str, dict] = {
    "Counterfactual Atlas": dict(
        slug="atlas", cadence={"long": 1, "short": 2}, long_words=1250, short_words=105,
        promise="One impossible what-if per video, answered with real physics and numbers on screen.",
        audience="Curious people aged 16 to 34 worldwide who like science but not jargon.",
        voice="Calm, precise, quietly awed. Short declarative sentences. Never hype words like insane or crazy. The number does the shouting.",
        hook="Sentence one poses the what-if as a concrete question. Sentence two gives the single most surprising consequence, with its number.",
        axes=["astronomy and orbits", "the human body at extremes", "weather and climate", "geology and the deep Earth", "oceans and tides", "energy and power", "materials and engineering", "light, sound and speed", "scale: size and distance", "time and duration", "animals and ecosystems", "everyday objects pushed to extremes"],
        titles=["What if the Moon were twice as close?", "What if you fell through the Earth?", "What if the Sun vanished for one second?"],
        avoid=["claiming certainty where physics is speculative; say 'roughly' or 'on the order of'", "gore", "real people", "predictions about real disasters"],
        scene_bias=["number", "bars", "orbit", "fall", "timeline", "say"], grounded=True,
        tags=["what if", "science", "physics", "space", "explained"], links=[CTA_DAYWILD],
    ),
    "10SecScientist": dict(
        slug="10sec", cadence={"long": 1, "short": 1}, long_words=1150, short_words=100,
        promise="Science in ten seconds of insight: one surprising result, one clean explanation, one thing to try or notice.",
        audience="Students and curious adults who scroll fast and want something true.",
        voice="Quick, warm, a little playful. Talks like a friend who studied it. Active verbs. No filler.",
        hook="Open with the surprising result as a claim, not a question. Then 'here is why'.",
        axes=["chemistry in the kitchen", "physics of everyday motion", "biology of the body", "the brain and senses", "space close to home", "materials and states of matter", "electricity and magnets", "plants and soil", "sound and light", "maths that surprises"],
        titles=["Why ice floats (and why that saved life on Earth)", "Your eyes never see what you think they see"],
        avoid=["medical advice", "unsafe at-home experiments (no fire, chemicals, mains electricity)", "pseudo-science"],
        scene_bias=["say", "number", "bars", "list", "timeline"], grounded=True,
        tags=["science", "science facts", "explained", "learn", "physics"], links=[CTA_ARC],
    ),
    "Oddly Proven": dict(
        slug="oddly", cadence={"long": 1, "short": 1}, long_words=1150, short_words=100,
        promise="Weird things science actually proved, with the study named on screen.",
        audience="Trivia lovers and skeptics who want receipts.",
        voice="Dry, amused, precise. Treats the strange claim seriously, then shows the evidence.",
        hook="State the weird claim flatly in sentence one. Sentence two: 'And it has been tested.'",
        axes=["psychology experiments that held up", "physics oddities", "animal behaviour studies", "medicine history surprises", "sleep and memory", "illusions and perception", "food and taste science", "weird records verified by Guinness-style bodies", "maths paradoxes", "accidental discoveries"],
        titles=["Scientists really did this, and it worked", "The strange experiment that changed how we see sleep"],
        avoid=["naming a study you cannot ground; say 'researchers have found' only with a grounded source", "replication-crisis studies presented as settled", "medical advice"],
        scene_bias=["list", "say", "number", "timeline", "bars"], grounded=True,
        tags=["weird science", "studies", "facts", "psychology", "explained"], links=[CTA_ARC],
    ),
    "Crazy Clipz": dict(
        slug="crazy", cadence={"long": 1, "short": 1}, long_words=1100, short_words=95,
        promise="Bizarre-but-true records and stunts, retold from public sources as original renders.",
        audience="Teens and young adults who want fast, surprising, shareable.",
        voice="High energy but exact. Short punchy lines. Always say where the record or claim comes from.",
        hook="Lead with the most extreme number or detail in the first seven words.",
        axes=["verified world records", "engineering stunts", "extreme sports history", "bizarre competitions", "survival stories with public records", "giant and tiny things", "speed and endurance", "failed inventions"],
        titles=["The record nobody thought could be broken", "The stunt that should have failed"],
        avoid=["dangerous stunts presented as something to try", "unsourced records", "real injuries described graphically", "real people's private lives"],
        scene_bias=["number", "bars", "say", "timeline", "list"], grounded=True,
        tags=["records", "crazy facts", "stunts", "unbelievable", "true story"], links=[CTA_ARC],
    ),
    "Wild Creature Files": dict(
        slug="wild", cadence={"long": 1, "short": 1}, long_words=1150, short_words=100,
        promise="Strange animals and the exact tricks they use to survive.",
        audience="Nature lovers and families; calm, wonder-first.",
        voice="Warm field-guide narrator. Concrete verbs. One vivid comparison per video.",
        hook="Open with what the animal does that no other animal can, in plain words.",
        axes=["deep sea animals", "insects and arachnids", "birds with odd skills", "reptiles and amphibians", "mammals with extreme adaptations", "animal partnerships", "defences and camouflage", "animal senses", "migrations", "extinct and nearly-extinct species"],
        titles=["The bird that builds a stage to win a mate", "How a frog survives being frozen solid"],
        avoid=["cruelty or gore", "claims about conservation status without grounding", "anthropomorphising as fact"],
        scene_bias=["image", "say", "number", "list", "bars"], grounded=True,
        tags=["animals", "wildlife", "nature", "animal facts", "survival"], links=[CTA_DAYWILD],
    ),
    "Foundbeam": dict(
        slug="foundbeam", cadence={"long": 1, "short": 1}, long_words=1200, short_words=105,
        promise="How famous products found their first users, told as clear, sourced stories.",
        audience="Builders, founders and curious people who like business stories.",
        voice="Clear, grounded, respectful. Explains the one non-obvious decision that mattered.",
        hook="Start with the odd early moment (the first ten users, the launch that nearly failed).",
        axes=["early distribution tactics", "pivots that worked", "launch stories", "community-led growth", "pricing decisions", "partnerships and platform bets", "product details that created word of mouth"],
        titles=["How a tiny app found its first thousand users", "The launch that almost never happened"],
        avoid=["invented quotes", "private financial details", "claiming insider knowledge", "stock or investment advice"],
        scene_bias=["timeline", "say", "number", "list", "bars"], grounded=True,
        tags=["startups", "product launch", "growth", "business history", "founders"], links=[CTA_ARC],
    ),
    "Workflow Verdict": dict(
        slug="verdict", cadence={"long": 1, "short": 1}, long_words=1100, short_words=95,
        promise="Paper verdicts on AI and productivity tools: what each is built for, who it suits, what it costs, scored on published facts.",
        audience="Professionals and students choosing tools.",
        voice="Even-handed, practical, concise. States what is known and what is not.",
        hook="Name the decision the viewer is facing, then promise one clear score.",
        axes=["note-taking and knowledge tools", "writing and editing tools", "task and project managers", "meeting and transcription tools", "automation platforms", "spreadsheets and data tools", "browser and search tools"],
        titles=["Notion vs Obsidian: which one fits you?", "Is a second brain app worth it?"],
        avoid=["claiming hands-on testing that did not happen: say 'on paper' and base scores on published features and pricing", "prices stated without a date; say 'at the time of writing'", "affiliate claims", "attacking named companies"],
        scene_bias=["verdict", "bars", "list", "say", "number"], grounded=True,
        tags=["productivity", "ai tools", "comparison", "workflow", "software"], links=[CTA_ARC],
        disclose="Scores are editorial judgments from published information, not lab tests. Prices and features change; check the vendor.",
    ),
    "History to Drift To": dict(
        slug="drift", cadence={"long": 1, "short": 0}, long_words=1900, short_words=0,
        promise="Slow, calm history told gently for falling asleep: ordinary days in extraordinary places.",
        audience="Adults who use audio to wind down. Many have it playing in the dark.",
        voice="Hushed, unhurried, kind. Long flowing sentences, concrete sensory detail, no sudden sounds in the writing, no cliffhangers. Never says subscribe in the middle.",
        hook="Open by settling the listener in: where we are, what time of day, that there is nothing to rush.",
        axes=["ancient cities on an ordinary day", "medieval villages through a year", "voyages and ships", "libraries and scholars", "trade routes", "seasons in historical places", "the history of everyday objects"],
        titles=["The Last Ordinary Day in Pompeii | Calm History for Sleep"],
        avoid=["graphic violence", "jump scares in tone", "modern politics", "claims beyond the sources; say 'we think' where historians are unsure"],
        scene_bias=["image", "say", "timeline", "list", "number"], grounded=True,
        tags=["history for sleep", "sleep documentary", "calm history", "bedtime history", "relaxing"], links=[{"label": "Wind down without your phone with HUSH", "url": "https://continuumarc.tech"}],
    ),
}


def playbook(channel: str) -> dict:
    return PLAYBOOKS[channel]
