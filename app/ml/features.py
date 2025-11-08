from __future__ import annotations
from collections import deque
from typing import Deque, Dict, Any
import numpy as np
import time

class RollingStats:
    def __init__(self, window:int=200):
        self.window = window
        self.buf: Deque[float] = deque(maxlen=window)

    def add(self, x: float):
        self.buf.append(float(x))

    def mean_std(self):
        if not self.buf:
            return 0.0, 1.0
        arr = np.fromiter(self.buf, dtype=float)
        return float(arr.mean()), float(arr.std() if arr.std() > 1e-6 else 1.0)

    def zscore(self, x: float) -> float:
        mu, sd = self.mean_std()
        return (x - mu) / sd

class ThroughputMeter:
    """Per-minute throughput meter."""
    def __init__(self):
        self.bucket_start = int(time.time() // 60)
        self.count = 0

    def tick(self) -> Dict[str, Any]:
        now_bucket = int(time.time() // 60)
        rotated = False
        if now_bucket != self.bucket_start:
            rotated = True
            self.bucket_start = now_bucket
            self.count = 0
        self.count += 1
        return {"bucket": self.bucket_start, "count": self.count, "rotated": rotated}
