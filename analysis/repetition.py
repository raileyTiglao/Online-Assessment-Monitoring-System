"""
=============================================================================
analysis/repetition.py — Repeated-Glance Detection
Online Assessment Monitoring System
Holy Angel University — School of Computing

Counts how many separate times an examinee has looked away within a recent
span, as opposed to how LONG they looked away for.

TemporalAnalyzer answers "is this being sustained?", which is the right
question for a prolonged downward stare but blind to the opposite pattern:
a series of short, repeated glances. Five one-second looks at a phone
spread over fifteen seconds may never push any ratio past its threshold —
each glance ends too soon — yet the repetition is itself the behaviour of
interest. Normal movement drifts and settles; furtive checking returns to
the same place again and again.

An EPISODE is one excursion away from normal and back. Episodes are
counted over a window long enough to contain several of them
(RepetitionConfig.WINDOW_SECONDS), and risk escalates on the count.

Two guards keep the count honest, both necessary because the underlying
suspicion flag sits close to its threshold during ordinary movement:

  MIN_EPISODE_SECONDS — suspicion must hold this long before it counts as
      an episode at all, so single-frame flickers are ignored.
  MIN_GAP_SECONDS     — normal posture must be recovered for this long
      before a new episode can begin, so one wavering glance that dips in
      and out of threshold is counted once rather than five times.

Without both, landmark jitter around the threshold would manufacture
dozens of episodes a second and the count would be meaningless.
=============================================================================
"""

import time
from collections import deque

from config import RepetitionConfig


class RepetitionAnalyzer:
    """
    Tracks discrete look-away episodes over a rolling window.

    Usage:
        rep = RepetitionAnalyzer()
        rep.update(suspicious=True)      # call every frame
        print(rep.episode_count)
    """

    def __init__(self, window_seconds: float = None):
        self.window_seconds = window_seconds or RepetitionConfig.WINDOW_SECONDS
        # Timestamps at which each counted episode BEGAN, oldest first.
        self._episodes = deque()
        # Confirmed state: True while inside a counted episode.
        self._in_episode = False
        # The raw per-frame flag's current run: what it is, and when that
        # run started. An episode is only opened or closed once the raw
        # flag has held its value long enough (see the two guards above).
        self._raw_state = False
        self._raw_since = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def update(self, suspicious: bool) -> None:
        """
        Feed one frame's suspicion flag and advance the episode state
        machine. Safe to call every frame; cost is O(1) amortised.
        """
        now = time.time()

        if self._raw_since is None:
            self._raw_state = suspicious
            self._raw_since = now

        # Any change in the raw flag restarts the dwell timer, so only a
        # value that HOLDS can open or close an episode.
        if suspicious != self._raw_state:
            self._raw_state = suspicious
            self._raw_since = now

        held_for = now - self._raw_since

        if (not self._in_episode and self._raw_state
                and held_for >= RepetitionConfig.MIN_EPISODE_SECONDS):
            # Timestamp the episode at its true start, not at the moment it
            # was confirmed, so evidence lookup lands on the actual glance.
            self._episodes.append(self._raw_since)
            self._in_episode = True

        elif (self._in_episode and not self._raw_state
                and held_for >= RepetitionConfig.MIN_GAP_SECONDS):
            self._in_episode = False

        self._prune(now)

    @property
    def episode_count(self) -> int:
        """Number of episodes that began within the current window."""
        self._prune(time.time())
        return len(self._episodes)

    def get_onset_timestamp(self) -> float | None:
        """
        When the MOST RECENT episode began — the glance that completed the
        pattern and pushed the count over its threshold.

        The earliest episode would arguably better represent "when this
        started", but it can be up to WINDOW_SECONDS old (20s), while the
        FrameBuffer only retains a few seconds. Asking for a frame that far
        back doesn't fail cleanly: FrameBuffer.get_frame_near() returns the
        CLOSEST frame it holds, so a stale timestamp would silently yield an
        unrelated frame and present it as evidence. The newest episode is
        both representative and actually still in the buffer.
        """
        self._prune(time.time())
        return self._episodes[-1] if self._episodes else None

    def reset(self) -> None:
        """Clear all state (e.g. on recalibration or a new session)."""
        self._episodes.clear()
        self._in_episode = False
        self._raw_state = False
        self._raw_since = None

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _prune(self, now: float) -> None:
        """Drop episodes that began before the window."""
        cutoff = now - self.window_seconds
        while self._episodes and self._episodes[0] < cutoff:
            self._episodes.popleft()
