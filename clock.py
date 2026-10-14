"""
=============================================================================
clock.py — Session Time Source
Online Assessment Monitoring System
Holy Angel University — School of Computing

Every timing rule in the pipeline (calibration length, sliding window,
repetition window, grace period, evidence cooldown, frame buffer) reads the
time through now() instead of calling time.time() directly.

With a live webcam, now() is simply the wall clock. When a recorded video
is replayed (main.py --source), main.py sets the time from the video's own
frame timestamps instead, so a 3-second head turn in the video still counts
as 3 seconds no matter how fast or slow the machine processes the frames.
Without this, replaying faster or slower than real time would stretch or
shrink every duration the risk rules measure.
=============================================================================
"""

import time

_video_time = None


def now() -> float:
    """Current session time in seconds (epoch-based, like time.time())."""
    return time.time() if _video_time is None else _video_time


def set_video_time(seconds: float) -> None:
    """Pin now() to a video frame's timestamp (replay mode only)."""
    global _video_time
    _video_time = seconds
