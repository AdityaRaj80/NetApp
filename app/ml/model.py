from __future__ import annotations
from typing import Dict, Any, Optional
import os
from .features import RollingStats

ANOM_Z = float(os.getenv("ANOMALY_Z_THRESH", "3.0"))
TEMP_ALERT = float(os.getenv("TEMP_ALERT", "80"))
HOT_MSG_THRESHOLD = int(os.getenv("HOT_MSG_THRESHOLD", "20"))

class OnlineAnomaly:
    def __init__(self, window:int=200):
        self.temp_stats = RollingStats(window=window)

    def score_event(self, ev: Dict[str, Any]) -> Dict[str, Any]:
        temp = float(ev.get("temperature", 0))
        z = self.temp_stats.zscore(temp)
        self.temp_stats.add(temp)
        is_alert = temp >= TEMP_ALERT
        is_anom = abs(z) >= ANOM_Z
        return {"z_temp": z, "is_temp_alert": is_alert, "is_anomaly": is_anom}

def policy_tiering(device_counts: Dict[str, int], device_id: str) -> Optional[str]:
    """Return one of {'tier_to_hot','tier_to_warm','tier_to_cold'} or None."""
    n = device_counts.get(device_id, 0)
    if n >= HOT_MSG_THRESHOLD:
        return "tier_to_hot"
    return None
