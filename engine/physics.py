"""Small, honest physics for the Atlas scenes: every animated motion is computed from these models, not eyeballed.

Models
- uniform: constant density. Gravity falls linearly to zero at the centre, so motion along any chord is simple harmonic.
- layered: a three-shell Earth (mantle, outer core, inner core) whose densities are fixed so the total mass is the real
  5.972e24 kg. Gravity stays near its surface strength for most of the way down, like the seismic model Klotz used.
Only the uniform-model numbers are quoted on screen as maths; the layered model shapes the motion of the "real Earth" ball.
"""
from __future__ import annotations

import math
from functools import lru_cache

import numpy as np

G = 6.674e-11
R = 6.371e6           # m
M = 5.972e24          # kg
G0 = 9.80665
OMEGA = math.sqrt(G0 / R)            # rad/s, the simple-harmonic frequency of the uniform model
HALF_PERIOD = math.pi / OMEGA        # s, one trip through any chord of the uniform Earth (~42.2 min)
SIDEREAL_DAY = 86164.1
EARTH_SPIN = 2 * math.pi / SIDEREAL_DAY


# ---------- layered Earth ----------
R_OUTER_CORE = 3.480e6
R_INNER_CORE = 1.221e6
RHO_MANTLE = 4.45e3
RHO_INNER = 12.9e3


def _shell_mass(r1: float, r2: float, rho: float) -> float:
    return 4 / 3 * math.pi * rho * (r2 ** 3 - r1 ** 3)


# The outer-core density is whatever makes the total mass exact.
RHO_OUTER = (M - _shell_mass(R_OUTER_CORE, R, RHO_MANTLE) - _shell_mass(0, R_INNER_CORE, RHO_INNER)) / (
    4 / 3 * math.pi * (R_OUTER_CORE ** 3 - R_INNER_CORE ** 3))


def mass_inside(r: float) -> float:
    r = max(0.0, min(R, r))
    m = _shell_mass(0, min(r, R_INNER_CORE), RHO_INNER)
    if r > R_INNER_CORE:
        m += _shell_mass(R_INNER_CORE, min(r, R_OUTER_CORE), RHO_OUTER)
    if r > R_OUTER_CORE:
        m += _shell_mass(R_OUTER_CORE, r, RHO_MANTLE)
    return m


def g_layered(r: float) -> float:
    return G * mass_inside(r) / max(r, 1.0) ** 2


def g_uniform(r: float) -> float:
    return G0 * r / R


@lru_cache(maxsize=1)
def layered_fall() -> tuple[np.ndarray, np.ndarray, np.ndarray, float]:
    """Drop from the surface to the centre. Returns (t, r, v, total seconds); r in metres, v in m/s (towards the centre)."""
    dt = 0.5
    r, v, t = R, 0.0, 0.0
    ts, rs, vs = [0.0], [R], [0.0]
    while r > 0:
        a = g_layered(r)
        v += a * dt
        r -= v * dt
        t += dt
        ts.append(t)
        rs.append(max(r, 0.0))
        vs.append(v)
    return np.array(ts), np.array(rs), np.array(vs), t


def layered_half_seconds() -> float:
    """Surface to far side in the layered model (twice the fall to the centre)."""
    return 2 * layered_fall()[3]


def layered_state(frac: float) -> tuple[float, float]:
    """Position along the tunnel in [-1, 1] (-1 near end, +1 far end) and speed in m/s, at a fraction of the whole trip."""
    ts, rs, vs, T = layered_fall()
    f = max(0.0, min(1.0, frac))
    if f <= 0.5:
        t = f * 2 * T
        r = float(np.interp(t, ts, rs))
        v = float(np.interp(t, ts, vs))
        return -r / R, v
    t = (1 - f) * 2 * T
    r = float(np.interp(t, ts, rs))
    v = float(np.interp(t, ts, vs))
    return r / R, v


def uniform_state(frac: float) -> tuple[float, float]:
    """Same, for the uniform model: x = -cos(pi f), v = vmax sin(pi f)."""
    f = max(0.0, min(1.0, frac))
    return -math.cos(math.pi * f), math.sqrt(G0 * R) * math.sin(math.pi * f)


# ---------- hypocycloid vs straight tunnel ----------
def hypocycloid(theta: float, n: int = 400) -> np.ndarray:
    """Fastest frictionless path between two surface points a central angle theta apart (unit Earth radius).
    Returns n points starting at (1, 0)."""
    rho = theta / (2 * math.pi)
    phi = np.linspace(0, theta, n)
    k = (1 - rho) / rho
    x = (1 - rho) * np.cos(phi) + rho * np.cos(k * phi)
    y = (1 - rho) * np.sin(phi) - rho * np.sin(k * phi)
    return np.stack([x, y], axis=1)


def path_times(points: np.ndarray) -> np.ndarray:
    """Cumulative seconds to slide along a path (unit radius) from rest at the surface, uniform-density Earth.
    Speed at radius r (unit) is OMEGA * R * sqrt(1 - r^2)."""
    seg = np.hypot(*np.diff(points, axis=0).T)
    r = np.hypot(points[:, 0], points[:, 1])
    rm = 0.5 * (r[1:] + r[:-1])
    v = OMEGA * np.sqrt(np.maximum(1 - rm ** 2, 1e-9))     # in radii per second
    dt = seg / v
    return np.concatenate([[0.0], np.cumsum(dt)])


def chord(theta: float, n: int = 400) -> np.ndarray:
    a = np.array([1.0, 0.0])
    b = np.array([math.cos(theta), math.sin(theta)])
    s = np.linspace(0, 1, n)[:, None]
    return a * (1 - s) + b * s


# ---------- Earth spin: what happens to a ball dropped in an equatorial tunnel ----------
def spin_drift(t_s: float) -> tuple[float, float, float]:
    """Dropped from the equator in a perfectly vacuum-sealed tunnel, uniform Earth. Inertial frame: the ball keeps the
    surface's sideways speed, so x = R cos(wt), y = (v_e / w) sin(wt) with w = OMEGA. Returns
    (depth fraction r/R, sideways offset from the rotating tunnel wall in km, tunnel angle in radians)."""
    ve = EARTH_SPIN * R
    x = R * math.cos(OMEGA * t_s)
    y = ve / OMEGA * math.sin(OMEGA * t_s)
    ang = EARTH_SPIN * t_s
    # offset of the ball from the tunnel's centreline (a line through the centre at angle ang)
    off = -x * math.sin(ang) + y * math.cos(ang)
    return math.hypot(x, y) / R, off / 1e3, ang


if __name__ == "__main__":
    print("uniform half period (min):", HALF_PERIOD / 60)
    print("rho outer core:", RHO_OUTER)
    print("layered full trip (min):", layered_half_seconds() / 60, "surface g:", g_layered(R))
    print("g at core-mantle boundary:", g_layered(R_OUTER_CORE))
    th = math.radians(120)
    h = hypocycloid(th)
    print("hypocycloid 120deg (min):", path_times(h)[-1] / 60, "chord:", path_times(chord(th))[-1] / 60)
    for m in (1, 5, 10, 20, 42):
        print("spin drift at", m, "min:", spin_drift(m * 60))
