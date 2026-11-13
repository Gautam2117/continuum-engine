"""Third wave of channel styles (14 Nov 2026): the remaining channels in the 50-channel network, so every
channel the engine renders has its own palette, type, voice, pacing and backdrop. Colours, type and voices
come from the Studio bible (lib/bible.ts)."""
from .styles import Style

MORE = [
    Style("kiara", "#101412", "#1e2a24", "#f3f7f2", "#a9bdb0", "#9fd3b5", "Caladea:style=Bold", "Inter:style=Light", "af_river", speed=0.94, motif="film", pad="warm"),
    Style("samjho", "#2b1f4a", "#3a2b63", "#fff6e6", "#cdbfe6", "#ffcf4a", "FreeSans:style=Bold", "FreeSans", "hf_alpha", lang="hi", speed=1.0, motif="grain", pad="bright"),
    Style("inkbound", "#0e0d12", "#1d1a24", "#efe9dd", "#b3a98f", "#c9a227", "Caladea:style=Bold", "Inter:style=Regular", "bf_alice", speed=0.92, motif="film", pad="deep"),
    Style("founder", "#0c0d10", "#1a1c22", "#f5f6f8", "#a3a8b5", "#ffb547", "Inter Display:style=Bold", "Inter:style=Regular", "am_echo", speed=1.02, motif="grain", pad="warm"),
    Style("lifespawn", "#0e0f14", "#1c1d26", "#ece6da", "#a9a395", "#c9a227", "Caladea:style=Bold", "Inter:style=Regular", "bm_daniel", speed=0.94, motif="film", pad="deep"),
    Style("nextframe", "#151826", "#232843", "#fdf6ec", "#b9b6c6", "#ffb347", "Inter Display:style=Black", "Inter:style=Medium", "am_puck", speed=1.1, motif="grid", pad="bright"),
    Style("majority", "#0e0f14", "#1b1c26", "#efeae0", "#aaa59a", "#8c2f39", "Caladea:style=Bold", "Inter:style=Regular", "bm_lewis", speed=0.98, motif="film", pad="deep"),
    Style("room404", "#0d1020", "#1a1f38", "#eef0ff", "#9aa2c8", "#ffcf4a", "Inter Display:style=Bold", "Inter:style=Regular", "am_onyx", speed=0.98, motif="scan", pad="deep"),
    Style("epic", "#140e12", "#2a1a1f", "#f7ead8", "#c2aa8e", "#e0a030", "Caladea:style=Bold", "Inter:style=Regular", "bm_george", speed=0.93, motif="paper", pad="warm"),
    Style("nightarchive", "#0b0c0b", "#151815", "#c9c9b8", "#8a8a7c", "#9dff4a", "Inter Display:style=Medium", "Inter:style=Regular", "am_onyx", speed=0.9, motif="scan", pad="deep"),
    Style("oddunits", "#1f2a44", "#2b3a5c", "#fff7e0", "#c6c1a8", "#ffd166", "Inter Display:style=Black", "Inter:style=Medium", "af_aoede", speed=1.06, motif="grain", pad="bright"),
    Style("unrealgoods", "#0e0e10", "#1c1c20", "#f4f1ea", "#b0aca0", "#d4af37", "Inter Display:style=SemiBold", "Inter:style=Regular", "af_heart", speed=0.96, motif="grain", pad="warm"),
    Style("tinyhistories", "#e9e2d0", "#d7cdb5", "#33415c", "#6d7487", "#c96f4a", "Caladea:style=Bold", "Inter:style=Regular", "bm_fable", speed=0.95, motif="paper", pad="warm"),
    Style("sentin", "#0f1016", "#1d1f2a", "#f4f5fb", "#a5a8c0", "#7c5cff", "Inter Display:style=Bold", "Inter:style=Regular", "af_kore", speed=1.04, motif="grid", pad="bright"),
    Style("longgame", "#0c0d10", "#191b21", "#f5f6f8", "#a3a8b5", "#5ee1ff", "Inter Display:style=Bold", "Inter:style=Regular", "am_santa", speed=0.98, motif="grain", pad="warm"),
    Style("onedollar", "#0f0e0c", "#1f1c17", "#f7f2e8", "#b9b19e", "#7bd389", "Inter Display:style=Bold", "Inter:style=Regular", "am_liam", speed=1.04, motif="grain", pad="bright"),
    Style("unsealed", "#0f1a24", "#1a2a38", "#e8d9b0", "#a89f82", "#d1495b", "Caladea:style=Bold", "Inter:style=Regular", "bm_lewis", speed=0.94, motif="paper", pad="deep"),
    Style("heist", "#0b1626", "#13253d", "#e6f0ff", "#92a6c4", "#ff5d5d", "Inter Display:style=Bold", "Inter:style=Regular", "am_adam", speed=1.02, motif="grid", pad="deep"),
    Style("survive", "#0c1214", "#162227", "#eef8f6", "#9ab5b0", "#ff9f1c", "Inter Display:style=Bold", "Inter:style=Medium", "am_michael", speed=1.04, motif="scan", pad="bright"),
    Style("news2099", "#07111f", "#0d1d33", "#e7f6ff", "#8aaed0", "#00e5ff", "Inter Display:style=Bold", "Inter:style=Medium", "af_nova", speed=1.04, motif="scan", pad="deep"),
    Style("money", "#0b0c10", "#16181f", "#f5f5f0", "#a8a8a0", "#ffd166", "Inter Display:style=Bold", "Inter:style=Regular", "am_adam", speed=1.04, motif="grid", pad="bright"),
    Style("indiamachine", "#101418", "#1c242b", "#fff7ec", "#b8aa95", "#ff9933", "Inter Display:style=Bold", "Inter:style=Regular", "bm_daniel", speed=1.0, motif="grid", pad="warm"),
    Style("truth", "#efe6d2", "#e0d4bb", "#2d2a26", "#6e675a", "#c8553d", "Caladea:style=Bold", "Inter:style=Regular", "bm_lewis", speed=0.95, motif="paper", pad="warm"),
    Style("blank", "#0b0f12", "#141c22", "#e3eef2", "#8aa3ab", "#7fb7be", "Inter Display:style=Light", "Inter:style=Light", "bf_lily", speed=0.8, motif="grain", pad="deep"),
    Style("benchwise", "#0e1013", "#1a1d22", "#f3f5f8", "#a4a9b3", "#3ddc97", "Inter Display:style=Bold", "Inter:style=Regular", "am_eric", speed=1.06, motif="grid", pad="bright"),
    Style("briefly", "#0a0c10", "#141820", "#f2f4f8", "#9ca3b3", "#ff6b6b", "Inter Display:style=Bold", "Inter:style=Medium", "af_sarah", speed=1.08, motif="grid", pad="none"),
    Style("ohgummy", "#1a0f1f", "#2c1736", "#fff3fb", "#cfa6c6", "#ff5fa2", "Inter Display:style=Black", "Inter:style=SemiBold", "af_alloy", speed=1.1, motif="grain", pad="bright"),
    Style("pixel", "#1b1530", "#2a2148", "#fff1d6", "#c4b79c", "#ff7b54", "Inter Display:style=Bold", "Inter:style=Medium", "bf_isabella", speed=1.0, motif="grid", pad="bright"),
]

CHANNEL_MORE = {
    "Kiara": "kiara", "Samjho System": "samjho", "Inkbound": "inkbound", "Founder, Actually": "founder",
    "LifeSpawn": "lifespawn", "Next Frame": "nextframe", "Majority Rules": "majority", "Room 404": "room404",
    "Epic Elsewhere": "epic", "The Night Archive": "nightarchive", "The Odd Units": "oddunits",
    "Unreal Goods Co.": "unrealgoods", "Tiny Histories": "tinyhistories", "Sent In": "sentin",
    "The Builders Long Game": "longgame", "One-Dollar Builds": "onedollar", "Unsealed Show": "unsealed",
    "Heist & Con": "heist", "Survive This": "survive", "News From 2099": "news2099",
    "Money Has Mechanics": "money", "The India Machine": "indiamachine", "Truth Over Propaganda": "truth",
    "BLANK HOURS": "blank", "Benchwisedeals": "benchwise", "Brieflylatest": "briefly", "OHGUMMY": "ohgummy",
    "Pixel Fables": "pixel",
}
