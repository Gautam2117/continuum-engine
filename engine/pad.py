"""A quiet generated ambient bed (no licensing questions): slow detuned chords with gentle movement."""
import numpy as np

MOODS = {
    "warm": [(110.0, 138.6, 164.8), (98.0, 123.5, 146.8), (116.5, 146.8, 174.6), (103.8, 130.8, 155.6)],
    "deep": [(55.0, 82.4, 110.0), (49.0, 73.4, 98.0), (58.3, 87.3, 116.5), (51.9, 77.8, 103.8)],
    "bright": [(220.0, 277.2, 329.6), (196.0, 246.9, 293.7), (233.1, 293.7, 349.2), (207.7, 261.6, 311.1)],
}


def pad(seconds: float, mood: str, sr: int = 24000, seed: int = 0) -> np.ndarray:
    n = int(seconds * sr)
    if mood == "none" or n <= 0:
        return np.zeros(n, dtype=np.float32)
    rng = np.random.default_rng(seed)
    t = np.arange(n) / sr
    chords = MOODS.get(mood, MOODS["warm"])
    bar = 8.0
    out = np.zeros(n, dtype=np.float64)
    for i, chord in enumerate(chords * int(np.ceil(seconds / (bar * len(chords))) + 1)):
        s0 = int(i * bar * sr)
        if s0 >= n:
            break
        s1 = min(n, int((i + 1.5) * bar * sr))
        seg = t[s0:s1] - t[s0]
        env = np.sin(np.pi * np.clip(seg / (1.5 * bar), 0, 1)) ** 2
        for f in chord:
            for det in (-0.6, 0.6):
                out[s0:s1] += env * np.sin(2 * np.pi * (f + det) * seg + rng.uniform(0, 6.28)) / 12
    # soft low-pass by moving average, then very low level
    k = 64
    out = np.convolve(out, np.ones(k) / k, mode="same")
    return (out / (np.abs(out).max() + 1e-9) * 0.06).astype(np.float32)
