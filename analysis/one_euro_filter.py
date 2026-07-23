"""
=============================================================================
analysis/one_euro_filter.py — Adaptive Signal Smoothing
Online Assessment Monitoring System
Holy Angel University — School of Computing

One-Euro filter. Unlike a fixed-alpha EMA, the cutoff frequency scales
with movement speed: slow movement gets heavy smoothing (removes landmark
jitter), fast movement gets light smoothing (stays responsive to real
head turns). This removes the tradeoff where a single alpha is either
too jittery when still or too laggy when moving.
=============================================================================
"""

import math
import time


class OneEuroFilter:
    """Adaptive low-pass filter for a single scalar signal."""

    def __init__(self, min_cutoff: float = 1.0, beta: float = 0.007,
                 d_cutoff: float = 1.0):
        self.min_cutoff = min_cutoff
        self.beta = beta
        self.d_cutoff = d_cutoff
        self._x_prev = None
        self._dx_prev = 0.0
        self._t_prev = None

    @staticmethod
    def _alpha(cutoff: float, dt: float) -> float:
        tau = 1.0 / (2 * math.pi * cutoff)
        return 1.0 / (1.0 + tau / dt)

    def __call__(self, x: float) -> float:
        now = time.time()
        if self._x_prev is None:
            self._x_prev, self._t_prev = x, now
            return x

        dt = max(1e-6, now - self._t_prev)
        self._t_prev = now

        dx = (x - self._x_prev) / dt
        a_d = self._alpha(self.d_cutoff, dt)
        dx_hat = a_d * dx + (1 - a_d) * self._dx_prev
        self._dx_prev = dx_hat

        cutoff = self.min_cutoff + self.beta * abs(dx_hat)
        a = self._alpha(cutoff, dt)
        x_hat = a * x + (1 - a) * self._x_prev
        self._x_prev = x_hat
        return x_hat

    def reset(self) -> None:
        self._x_prev = None
        self._dx_prev = 0.0
        self._t_prev = None