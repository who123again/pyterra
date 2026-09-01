"""Deterministic value-noise used for terrain generation (no external deps)."""
import math

_MASK = 0xFFFFFFFFFFFF


def _hash2(x: int, y: int, seed: int) -> float:
    n = (x * 374761393 + y * 668265263 + seed * 2246822519) & _MASK
    n = ((n ^ (n >> 13)) * 1274126177) & _MASK
    n = n ^ (n >> 16)
    return (n & 0xFFFFFFFF) / 0xFFFFFFFF


def _smooth(t: float) -> float:
    return t * t * (3.0 - 2.0 * t)


def value_noise2(x: float, y: float, seed: int = 0) -> float:
    xi, yi = math.floor(x), math.floor(y)
    xf, yf = x - xi, y - yi
    xi, yi = int(xi), int(yi)
    a = _hash2(xi, yi, seed)
    b = _hash2(xi + 1, yi, seed)
    c = _hash2(xi, yi + 1, seed)
    d = _hash2(xi + 1, yi + 1, seed)
    u, v = _smooth(xf), _smooth(yf)
    return a + (b - a) * u + (c - a) * v + (a - b - c + d) * u * v


def fbm2(x: float, y: float, octaves: int = 3, seed: int = 0) -> float:
    """Fractal Brownian motion, returns ~[0, 1]."""
    total, amp, freq, norm = 0.0, 1.0, 1.0, 0.0
    for i in range(octaves):
        total += value_noise2(x * freq, y * freq, seed + i * 101) * amp
        norm += amp
        amp *= 0.5
        freq *= 2.0
    return total / norm


def fbm1(x: float, octaves: int = 3, seed: int = 0) -> float:
    return fbm2(x, 0.5, octaves, seed)
