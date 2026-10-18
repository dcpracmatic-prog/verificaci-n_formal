"""Detector de anomalías: tasa de error en ventana deslizante."""
from __future__ import annotations
from collections import deque
from typing import Deque


class ErrorRateDetector:
    def __init__(self, window: int = 20, min_events: int = 10, threshold: float = 0.2):
        self.window, self.min_events, self.threshold = window, min_events, threshold
        self._buf: Deque[bool] = deque(maxlen=window)

    def add(self, ok: bool) -> bool:
        self._buf.append(ok)
        if len(self._buf) < self.min_events:
            return False
        return (self._buf.count(False) / len(self._buf)) >= self.threshold

    def reset(self) -> None:
        self._buf.clear()
