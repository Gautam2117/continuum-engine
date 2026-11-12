"""Per-channel look and sound. Every channel gets its own palette, type, voice, pacing and backdrop,
so no two channels in the network share a template."""
from dataclasses import dataclass, field


@dataclass(frozen=True)
class Style:
    slug: str
    bg: str            # base background
    bg2: str           # second background tone (gradient)
    ink: str           # main text
    muted: str         # secondary text
    accent: str        # one accent colour
    display: str       # fontconfig pattern for headlines
    body: str          # fontconfig pattern for body text
    voice: str         # Kokoro voice id
    lang: str = "en-us"
    speed: float = 1.0
    motif: str = "grain"   # grain | stars | grid | paper | film | scan
    pad: str = "warm"      # ambient pad mood: warm | deep | bright | none
    caps_titles: bool = False
    products: list[str] = field(default_factory=list)


STYLES: dict[str, Style] = {s.slug: s for s in [
    Style("drift", "#14110d", "#221a12", "#f1e6d2", "#b8a68a", "#d9a35f", "Caladea:style=Bold", "Caladea", "bm_george", speed=0.88, motif="paper", pad="warm"),
    Style("atlas", "#05070f", "#0c1a33", "#eef4ff", "#8fa3c8", "#5ee1ff", "Inter Display:style=Black", "Inter:style=Medium", "am_michael", speed=1.02, motif="stars", pad="deep"),
    Style("10sec", "#0b0f0c", "#10261a", "#effff4", "#9cc7ab", "#7dff9b", "Inter Display:style=ExtraBold", "Inter:style=Medium", "am_puck", speed=1.12, motif="grid", pad="bright"),
    Style("oddly", "#120c1a", "#24133a", "#f6f0ff", "#b7a5d6", "#ffcf4a", "Inter Display:style=Bold", "Inter:style=Regular", "af_bella", speed=1.03, motif="grain", pad="bright"),
    Style("crazy", "#130707", "#2d0b0b", "#fff2ee", "#d8a59b", "#ff5a3c", "Inter Display:style=Black", "Inter:style=SemiBold", "am_fenrir", speed=1.08, motif="scan", pad="bright", caps_titles=True),
    Style("wild", "#0b130c", "#183018", "#eef7e8", "#a9c29c", "#c8e85a", "DejaVu Serif:style=Bold", "Inter:style=Regular", "bm_fable", speed=0.95, motif="film", pad="warm"),
    Style("foundbeam", "#0e0e10", "#1d1b24", "#f7f5f0", "#aaa6b4", "#ffb547", "Inter Display:style=SemiBold", "Inter:style=Regular", "af_heart", speed=1.0, motif="grain", pad="warm"),
    Style("verdict", "#0a0d12", "#141c2a", "#f2f5fa", "#93a0b8", "#4f8cff", "Inter Display:style=Bold", "Inter:style=Regular", "am_adam", speed=1.05, motif="grid", pad="none"),
    # Footage-led channels: the engine writes scripts, captions and thumbnails; you add the footage.
    Style("strata", "#0a0a12", "#17172b", "#f5f3ff", "#a7a3c8", "#9b7bff", "Inter Display:style=Bold", "Inter:style=Regular", "af_nova", motif="grain", pad="bright"),
    Style("sienna", "#140f0f", "#2a1d1d", "#fff4ef", "#c9aaa0", "#ff9d7a", "Caladea:style=Bold", "Inter:style=Light", "af_sky", motif="film", pad="warm"),
    Style("gotz", "#06080a", "#0f1a12", "#ecfff0", "#94b8a0", "#39ff88", "Inter Display:style=Black", "Inter:style=Bold", "am_echo", motif="scan", pad="bright", caps_titles=True),
    Style("aditi", "#140d10", "#2b1620", "#fff0f6", "#cfa3b8", "#ff7ab6", "Caladea:style=Bold", "Inter:style=Light", "af_jessica", motif="film", pad="warm"),
    Style("felix", "#07060c", "#1a0f22", "#f4eeff", "#a99bc2", "#b46bff", "Inter Display:style=Black", "Inter:style=Bold", "am_liam", motif="scan", pad="deep", caps_titles=True),
    # Second wave of explainer channels: each has its own palette, typefaces, voice and pacing.
    Style("whap10", "#100d08", "#2a1d0a", "#fff6e6", "#c9b48a", "#ffb020", "Inter Display:style=ExtraBold", "Inter:style=Medium", "am_eric", speed=1.06, motif="grid", pad="bright"),
    Style("drives", "#0c0e11", "#1b222b", "#eef2f6", "#9aa7b5", "#ff7a1a", "Inter Display:style=Black", "Inter:style=Medium", "bm_lewis", speed=1.0, motif="scan", pad="deep", caps_titles=True),
    Style("exists", "#0b1012", "#0f2a2e", "#effffd", "#93bfba", "#2ee6c8", "Inter Display:style=Bold", "Inter:style=Regular", "af_sarah", speed=1.04, motif="grid", pad="bright"),
    Style("anomaly", "#060a08", "#0c1f17", "#e9fff4", "#86b8a0", "#9dff4a", "Inter Display:style=Black", "Inter:style=Light", "am_onyx", speed=0.97, motif="scan", pad="deep"),
    Style("gears", "#120f0b", "#2a2116", "#f6efe3", "#b9a98f", "#d9b04a", "DejaVu Serif:style=Bold", "Inter:style=Regular", "bm_daniel", speed=0.98, motif="paper", pad="warm"),
    Style("fool", "#0f0a16", "#231040", "#f7f0ff", "#b6a0dc", "#ff4fa3", "Inter Display:style=Black", "Inter:style=SemiBold", "af_nicole", speed=1.08, motif="grain", pad="bright"),
    Style("drawn", "#f3efe6", "#e4dccb", "#1c1a17", "#6b6558", "#d6452b", "Caladea:style=Bold", "Caladea", "bf_emma", speed=0.96, motif="paper", pad="warm"),
    Style("beyond", "#08080e", "#14122a", "#f1f0ff", "#9d9ac8", "#8aa4ff", "Caladea:style=Bold", "Inter:style=Light", "bf_isabella", speed=0.92, motif="stars", pad="deep"),
    Style("lowbat", "#0d0f14", "#1a1d2a", "#eceff8", "#98a0bb", "#ffb86b", "Inter Display:style=Medium", "Inter:style=Light", "bf_lily", speed=0.86, motif="grain", pad="warm"),
]}

# Channel title → style slug (only channels the engine renders or assists with so far).
CHANNEL_STYLE = {
    "History to Drift To": "drift",
    "Counterfactual Atlas": "atlas",
    "10SecScientist": "10sec",
    "Oddly Proven": "oddly",
    "Crazy Clipz": "crazy",
    "Wild Creature Files": "wild",
    "Foundbeam": "foundbeam",
    "Workflow Verdict": "verdict",
    "Strata": "strata",
    "Sienna Carter": "sienna",
    "GOTZ": "gotz",
    "Aditi Raichand": "aditi",
    "Felix": "felix",
    "What Happens in 10": "whap10",
    "What Drives It": "drives",
    "OH, THIS EXISTS": "exists",
    "What If Anomaly": "anomaly",
    "Gears Unseen": "gears",
    "Brain Fool Lab": "fool",
    "Drawn Out Minds": "drawn",
    "Think Beyond This": "beyond",
    "The Low Battery Show": "lowbat",
}

# Channels whose videos need footage the engine can't make (gameplay, app capture, a persona on camera).
FOOTAGE_LED = {"Strata", "Sienna Carter", "GOTZ", "Aditi Raichand", "Felix"}


def style_for(channel: str) -> Style:
    try:
        return STYLES[CHANNEL_STYLE[channel]]
    except KeyError as e:
        raise SystemExit(f"No style for channel {channel!r}. Add it to engine/styles.py") from e


def rgb(hex_: str, a: int | None = None) -> tuple:
    h = hex_.lstrip("#")
    c = tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))
    return c if a is None else (*c, a)
