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
        slug="atlas", fixed=True, cadence={"long": 1, "short": 2}, long_words=1250, short_words=105,
        promise="One impossible what-if per video, answered with real physics and numbers on screen.",
        audience="Curious people aged 16 to 34 worldwide who like science but not jargon.",
        voice="Calm, precise, quietly awed. Short declarative sentences. Never hype words like insane or crazy. The number does the shouting.",
        hook="Sentence one poses the what-if as a concrete question. Sentence two gives the single most surprising consequence, with its number.",
        axes=["astronomy and orbits", "the human body at extremes", "weather and climate", "geology and the deep Earth", "oceans and tides", "energy and power", "materials and engineering", "light, sound and speed", "scale: size and distance", "time and duration", "animals and ecosystems", "everyday objects pushed to extremes"],
        titles=["What if the Moon were twice as close?", "What if you fell through the Earth?", "What if the Sun vanished for one second?"],
        avoid=["claiming certainty where physics is speculative; say 'roughly' or 'on the order of'", "gore", "real people", "predictions about real disasters"],
        scene_bias=["b3d (when the topic fits a 3D scene)", "number", "bars", "orbit", "fall", "timeline", "say"], grounded=True,
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
    "What Happens in 10": dict(
        slug="whap10", cadence={'long': 1, 'short': 1}, long_words=1150, short_words=100,
        promise='What really happens in the next 10 seconds, 10 minutes, 10 hours or 10 years of one ordinary thing, step by step with real numbers.',
        audience='Curious people who like a countdown and a clear payoff.',
        voice='Brisk, concrete, a little wry. Counts the clock out loud. Every beat has a timestamp and a number.',
        hook='Sentence one names the thing and the time window. Sentence two gives the first surprising number at second zero.',
        axes=['the human body over time', 'the Earth and sky over time', 'food and chemistry over time', 'machines and materials over time', 'space and light over time', 'cities and infrastructure over time'],
        titles=['What happens in the first 10 seconds after you swallow a coin?', 'What happens to a phone left on the Moon for 10 years?'],
        avoid=['medical advice or diagnosis', "claiming exact personal outcomes; say 'typically' or 'on average'", 'gore', 'predictions about real disasters'],
        scene_bias=['timeline', 'number', 'bars', 'say', 'list'], grounded=True,
        tags=['what happens', 'timeline', 'explained', 'science', 'step by step'], links=[CTA_ARC],
    ),
    "What Drives It": dict(
        slug="drives", cadence={'long': 1, 'short': 1}, long_words=1150, short_words=100,
        promise='How a machine, engine or vehicle actually works, from the part that moves first to the part that moves you.',
        audience='People who like to know how things work, aged 14 to 45.',
        voice="Plain, confident, workshop-calm. Names every part once, then uses it. Prefers 'this pushes that' to jargon.",
        hook='Sentence one states what the machine does in plain words. Sentence two gives the number that makes it impressive.',
        axes=['engines and fuel', 'gears and transmissions', 'aircraft and flight', 'ships and submarines', 'trains and railways', 'electric motors and batteries', 'everyday machines (pumps, locks, elevators)'],
        titles=['How a jet engine turns fire into thrust', 'How an elevator stays up when the cable breaks'],
        avoid=['repair or modification instructions that could cause injury', 'claiming a part works a way you are unsure of', 'brand ranking claims'],
        scene_bias=['number', 'bars', 'list', 'timeline', 'image', 'say'], grounded=True,
        tags=['how it works', 'engines', 'machines', 'engineering', 'explained'], links=[CTA_ARC],
    ),
    "OH, THIS EXISTS": dict(
        slug="exists", cadence={'long': 1, 'short': 1}, long_words=1100, short_words=100,
        promise='Real, documented products and inventions most people have never heard of, what they do and why they exist.',
        audience='Curious people who enjoy discovering odd, useful things.',
        voice='Delighted but honest. Says what it is, who made it, what it costs when known, and what it does not do.',
        hook="Sentence one is 'There is a real [thing] that [does something surprising].' Sentence two says who made it and when.",
        axes=['odd tools and gadgets', 'useful inventions from other countries', 'everyday objects with a hidden story', 'weirdly specific professional equipment', 'tiny inventions that changed habits', 'accessibility and design inventions'],
        titles=['There is a real fork that tells you how fast you eat', 'The tiny tool every sailor carries and nobody names'],
        avoid=['claiming to have tested or owned the product', 'prices or availability unless the grounding states them', 'affiliate claims', 'brand ranking claims', 'recommending a purchase'],
        scene_bias=['image', 'say', 'list', 'number', 'timeline'], grounded=True,
        tags=['inventions', 'gadgets', 'products', 'did you know', 'discovery'], links=[CTA_ARC],
    ),
    "What If Anomaly": dict(
        slug="anomaly", cadence={'long': 1, 'short': 1}, long_words=1200, short_words=105,
        promise='One strange rule of the world changes. A tight, labelled work of fiction follows the consequences, one step at a time.',
        audience='Fans of science fiction and thought experiments aged 15 to 35.',
        voice='Dry, deadpan, quietly unsettling. Short sentences. States the anomaly as plain fact, then lets consequences pile up.',
        hook='Sentence one states the anomaly as a flat fact. Sentence two shows the first small consequence, with a specific detail.',
        axes=['gravity or time behaving differently', 'a new law of biology', 'a rule of physics reversed for one day', 'a city where one law of nature is off', 'a machine that behaves unexpectedly', 'a shared world event with a rule'],
        titles=['The day the clocks ran backwards for one hour', 'Every shadow pointed the wrong way for a week'],
        avoid=['presenting fiction as fact; the first scene must say it is fiction', 'real people or real disasters', 'gore', 'political or religious targets'],
        scene_bias=['say', 'number', 'timeline', 'list', 'bars'], grounded=False,
        tags=['sci-fi', 'what if', 'short story', 'fiction', 'thought experiment'], links=[CTA_ARC],
    ),
    "Gears Unseen": dict(
        slug="gears", cadence={'long': 1, 'short': 1}, long_words=1150, short_words=100,
        promise='The hidden engineering inside everyday and ancient objects: how a lock, a clock, a zip or an aqueduct really works.',
        audience='Curious tinkerers and history lovers aged 16 to 50.',
        voice='Warm, patient, craftsman-like. Describes motion in order: first this turns, then that lifts. Respects the inventor.',
        hook='Sentence one names the object everyone has used. Sentence two says what most people do not know it does.',
        axes=['locks and keys', 'clocks and timekeeping', 'fasteners and joints', 'water and plumbing', 'ancient machines', 'textile and printing machines', 'tiny mechanisms (zips, pens, switches)'],
        titles=['How a zip fastener actually locks', 'The Roman aqueduct maths that kept water flowing downhill'],
        avoid=['instructions to defeat security locks or safety devices', 'claiming a date or inventor the grounding does not give', 'brand ranking claims'],
        scene_bias=['image', 'number', 'list', 'timeline', 'say'], grounded=True,
        tags=['engineering', 'how it works', 'mechanisms', 'history of technology', 'explained'], links=[CTA_ARC],
    ),
    "Brain Fool Lab": dict(
        slug="fool", cadence={'long': 1, 'short': 1}, long_words=1100, short_words=100,
        promise='Illusions and tricks you can test on yourself in seconds, then the real brain science behind each one.',
        audience='Curious people and students who like to be surprised by their own senses.',
        voice='Playful challenger. Gives one instruction, makes the viewer try it, then explains plainly. Never mocks the viewer.',
        hook='Sentence one is an instruction the viewer can follow right now. Sentence two promises their brain will get it wrong.',
        axes=['optical illusions', 'sound and hearing tricks', 'memory tricks', 'attention and change blindness', 'touch and body-sense illusions', 'decision shortcuts'],
        titles=['Stare at the dot for ten seconds and watch the colour vanish', 'Why you cannot tickle yourself'],
        avoid=['medical or mental-health claims', 'tests that could cause eye strain beyond a few seconds', "claiming a trick works on everyone; say 'most people'", 'flashing patterns'],
        scene_bias=['say', 'list', 'number', 'bars', 'image'], grounded=True,
        tags=['illusions', 'brain', 'psychology', 'experiments', 'perception'], links=[CTA_ARC],
    ),
    "Drawn Out Minds": dict(
        slug="drawn", cadence={'long': 1, 'short': 1}, long_words=1150, short_words=100,
        promise='One big idea about how people think and decide, explained slowly with a named study or thinker each time.',
        audience='Thoughtful adults who like psychology, economics and ideas.',
        voice='Reflective, clear, kind. Explains one idea per video and ends with a question to carry away. No self-help tone.',
        hook='Sentence one states a puzzling human behaviour. Sentence two names the researcher or study that first measured it.',
        axes=['decision-making and bias', 'memory and learning', 'habits and motivation', 'groups and social influence', 'money and choice', 'language and thought', 'attention and focus'],
        titles=['Why we keep going to a bad meeting we already paid for', 'The experiment that showed how fast we copy a crowd'],
        avoid=['therapy, diagnosis or self-help advice', 'claiming a study result the grounding does not give', "presenting contested findings as settled; say 'in this study' or 'some replications fail'"],
        scene_bias=['say', 'list', 'timeline', 'bars', 'number'], grounded=True,
        tags=['psychology', 'behavioural science', 'decision making', 'ideas', 'explained'], links=[CTA_ARC],
    ),
    "Think Beyond This": dict(
        slug="beyond", cadence={'long': 1, 'short': 1}, long_words=1200, short_words=105,
        promise='A famous thought experiment, laid out in plain steps with the strongest reply to it, so the viewer can decide for themselves.',
        audience='Curious adults aged 18 to 45 who like philosophy, physics and big questions.',
        voice='Slow, spacious, fair. Presents every side as its holder would. Never tells the viewer what to believe.',
        hook='Sentence one poses the dilemma as a concrete scene. Sentence two asks the question the whole video turns on.',
        axes=['mind and identity', 'time and the universe', 'ethics dilemmas', 'knowledge and reality', 'fairness and society', 'infinity and mathematics'],
        titles=['The ship that has every plank replaced', 'If you copied yourself, which one is you?'],
        avoid=['taking a side on current politics or religion', 'presenting one answer as the only one', 'claiming a thinker said something the grounding does not give'],
        scene_bias=['say', 'list', 'timeline', 'number', 'bars'], grounded=True,
        tags=['thought experiment', 'philosophy', 'big questions', 'mind', 'explained'], links=[CTA_ARC],
    ),
    "The Low Battery Show": dict(
        slug="lowbat", cadence={"long": 0, "short": 1}, long_words=0, short_words=85,
        promise="Original stick-character comedy about the last tiny obstacle at the end of a long day.",
        audience="People who are tired enough to bargain with a phone charger.",
        voice="Dry, understated and specific. The action carries the joke.",
        hook="Open on the character interacting with one ordinary object that refuses to cooperate.",
        axes=["one last notification", "the temptation to check the screen", "the phone sliding away", "refusing to get up", "the relief when the screen goes dark"],
        topic_constraints="Pitch a silent-readable couch gag starring Pip with only a phone, couch, lamp and table. The only prop motion is the phone sliding out of reach. The screen can go dark. Avoid charging, cables, falls and any action outside the couch setup.",
        titles=["Close Enough to Regret It", "The Phone Has the Last Word"],
        avoid=["ambient compilations", "life advice", "borrowed characters", "explaining the punchline"],
        scene_bias=["title", "pip", "end"], grounded=False, fiction=True,
        rule='Use recurring Pip. The set contains a couch, lamp, table and phone. Build the joke through a reach, a slide and a reversal. Keep all narrated and implied actions within those props and poses. No cables, chargers, sockets, falls or spare objects. Use only title, pip and end visuals. Use at least four {"type":"pip","action":"notice|reach|slip|reset"} scenes. Omit field "phone" to keep the previous shot state. The phone starts near; slip begins near and automatically ends far. After slip, use "phone":"dead" once if the screen goes black. The phone stays dead afterward. Choose exactly one action per scene and match the narration to the staged action.',
        tags=["stickman", "original animation", "comedy", "shorts"], links=[CTA_ARC],
    ),
}


def playbook(channel: str) -> dict:
    return PLAYBOOKS[channel]


def cadence_for(channel: str, day) -> dict:
    """What a channel makes on a given date. Decided by SG on 14 Nov 2026: Counterfactual Atlas makes 3 a day
    (1 long + 2 Shorts); every other channel makes exactly 1 video a day: a Short on most days and a long video
    on two days a week, staggered per channel so the network's long renders spread across the week.
    Channels that only have one format (sleep and ambient channels, long only) make that format daily."""
    pb = PLAYBOOKS[channel]
    if pb.get("fixed"):
        return dict(pb["cadence"])
    c = pb["cadence"]
    if not c.get("short"):
        return {"long": 1, "short": 0}
    if not c.get("long"):
        return {"long": 0, "short": 1}
    a = list(PLAYBOOKS).index(channel) % 7
    return {"long": 1, "short": 0} if day.weekday() in {a, (a + 3) % 7} else {"long": 0, "short": 1}


# Third wave (14 Nov 2026): the rest of the network, so every channel SG runs except Felix and GOTZ (his own
# gaming channels) has a playbook.
from .playbooks_more import MORE  # noqa: E402

PLAYBOOKS.update(MORE)
