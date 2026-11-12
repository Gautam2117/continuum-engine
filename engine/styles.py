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
