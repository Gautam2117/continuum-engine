"""Emoji stickers from Noto Color Emoji (OFL/Apache licensed, free for commercial use)."""
from __future__ import annotations

import functools
import os

from PIL import Image, ImageDraw, ImageFont

EMOJI_FONT = os.environ.get("EMOJI_FONT", "/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf")

# Narration keyword -> emoji. First matches win, so order from specific to general.
KEYWORDS = [
    ("moon", "🌕"), ("eclipse", "🌑"), ("tide", "🌊"), ("ocean", "🌊"), ("wave", "🌊"), ("sea", "🌊"), ("water", "💧"),
    ("earth", "🌍"), ("planet", "🪐"), ("saturn", "🪐"), ("mars", "🔴"), ("sun", "☀️"), ("star", "⭐"), ("galaxy", "🌌"),
    ("space", "🚀"), ("rocket", "🚀"), ("orbit", "🛰️"), ("light", "💡"), ("sky", "🌤️"), ("blue", "🔵"), ("cloud", "☁️"),
    ("rain", "🌧️"), ("storm", "⛈️"), ("lightning", "⚡"), ("electric", "⚡"), ("energy", "⚡"), ("fire", "🔥"),
    ("hot", "🔥"), ("heat", "🔥"), ("ice", "🧊"), ("cold", "🥶"), ("snow", "❄️"), ("volcano", "🌋"), ("mountain", "⛰️"),
    ("ash", "🌋"), ("bread", "🍞"), ("bakery", "🥖"), ("bakers", "🥖"), ("wine", "🍷"), ("food", "🍽️"), ("fish", "🐟"),
    ("sleep", "😴"), ("dream", "💤"), ("night", "🌙"), ("quiet", "🤫"), ("brain", "🧠"), ("mind", "🧠"), ("think", "🤔"),
    ("heart", "❤️"), ("blood", "🩸"), ("body", "🧍"), ("bone", "🦴"), ("eye", "👁️"), ("see", "👀"), ("hand", "✋"),
    ("money", "💰"), ("cash", "💵"), ("gold", "🪙"), ("price", "🏷️"), ("cost", "💸"), ("sell", "🛒"), ("business", "💼"),
    ("time", "⏳"), ("clock", "⏰"), ("history", "🏛️"), ("roman", "🏛️"), ("rome", "🏛️"), ("ancient", "🏺"),
    ("war", "⚔️"), ("king", "👑"), ("empire", "👑"), ("ship", "🚢"), ("boat", "⛵"), ("train", "🚆"), ("car", "🚗"),
    ("plane", "✈️"), ("map", "🗺️"), ("city", "🏙️"), ("town", "🏘️"), ("house", "🏠"), ("home", "🏠"), ("school", "🏫"),
    ("book", "📖"), ("letter", "✉️"), ("write", "✍️"), ("computer", "💻"), ("phone", "📱"), ("code", "👨‍💻"), ("robot", "🤖"),
    ("ai", "🤖"), ("data", "📊"), ("chart", "📈"), ("score", "🏆"), ("win", "🏆"), ("test", "🧪"), ("science", "🔬"),
    ("atom", "⚛️"), ("gravity", "🍎"), ("magnet", "🧲"), ("sound", "🔊"), ("music", "🎵"), ("voice", "🗣️"),
    ("dog", "🐕"), ("cat", "🐈"), ("bird", "🐦"), ("shark", "🦈"), ("whale", "🐋"), ("snake", "🐍"), ("insect", "🐜"),
    ("tree", "🌳"), ("plant", "🌱"), ("flower", "🌸"), ("forest", "🌲"), ("animal", "🦁"), ("danger", "⚠️"),
    ("warning", "⚠️"), ("secret", "🤫"), ("question", "❓"), ("why", "❓"), ("how", "❓"), ("idea", "💡"), ("world", "🌐"),
    ("big", "📏"), ("fast", "💨"), ("speed", "💨"), ("wind", "💨"), ("heavy", "🏋️"), ("small", "🔍"), ("tiny", "🔍"),
]


GENERIC = {"how", "why", "big", "small", "tiny", "see", "world", "test", "fast", "heavy", "data", "score", "win", "light", "blue", "hand", "time", "ai"}


def pick(text: str, limit: int = 2) -> list[str]:
    """Emoji for the narration: topic words first, vague words only if nothing better turns up."""
    words = [w.strip(".,!?;:'\"").lower() for w in text.split()]
    out: list[str] = []
    for allow_generic in (False, True):
        for w in words:
            for key, e in KEYWORDS:
                if (key in GENERIC) != allow_generic or e in out:
                    continue
                if w == key or w == key + "s" or (len(key) > 3 and w.startswith(key)):
                    out.append(e)
                    break
            if len(out) >= limit:
                return out
    return out


@functools.lru_cache(maxsize=None)
def _native(ch: str) -> Image.Image | None:
    try:
        f = ImageFont.truetype(EMOJI_FONT, 109)
    except OSError:
        return None
    im = Image.new("RGBA", (160, 140), (0, 0, 0, 0))
    ImageDraw.Draw(im).text((4, 2), ch, font=f, embedded_color=True)
    bb = im.getbbox()
    return im.crop(bb) if bb else None


@functools.lru_cache(maxsize=512)
def sprite(ch: str, size: int) -> Image.Image | None:
    """RGBA sticker `size` px on its long side, or None when the emoji font is not installed."""
    n = _native(ch)
    if n is None:
        return None
    sc = size / max(n.size)
    return n.resize((max(1, int(n.width * sc)), max(1, int(n.height * sc))), Image.LANCZOS)
