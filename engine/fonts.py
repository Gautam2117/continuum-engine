"""Font lookup by family/style through fontconfig, so the same code works locally and on CI runners."""
import functools
import subprocess

from PIL import ImageFont


@functools.lru_cache(maxsize=None)
def font_file(pattern: str) -> str:
    out = subprocess.run(["fc-match", "-f", "%{file}", pattern], capture_output=True, text=True, check=True)
    return out.stdout.strip()


@functools.lru_cache(maxsize=None)
def font(pattern: str, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(font_file(pattern), size)
