"""Narration with Kokoro (Apache-2.0, runs on CPU). Model files are downloaded once and cached."""
import os
import pathlib
import urllib.request

import numpy as np

MODEL_DIR = pathlib.Path(os.environ.get("KOKORO_DIR", pathlib.Path.home() / ".cache" / "kokoro"))
FILES = {
    "kokoro-v1.0.onnx": "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/kokoro-v1.0.onnx",
    "voices-v1.0.bin": "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/voices-v1.0.bin",
}
SR = 24000
_k = None


def _model():
    global _k
    if _k is None:
        from kokoro_onnx import Kokoro
        MODEL_DIR.mkdir(parents=True, exist_ok=True)
        for name, url in FILES.items():
            p = MODEL_DIR / name
            if not p.exists():
                print(f"downloading {name}…", flush=True)
                urllib.request.urlretrieve(url, p)
        _k = Kokoro(str(MODEL_DIR / "kokoro-v1.0.onnx"), str(MODEL_DIR / "voices-v1.0.bin"))
    return _k


def speak(text: str, voice: str, speed: float = 1.0, lang: str = "en-us") -> np.ndarray:
    """Mono float32 audio at 24 kHz, with a short breath of silence at each end."""
    samples, sr = _model().create(text, voice=voice, speed=speed, lang=lang)
    assert sr == SR
    pad = np.zeros(int(0.18 * SR), dtype=np.float32)
    return np.concatenate([pad, samples.astype(np.float32), pad])
