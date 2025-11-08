from __future__ import annotations
import os, time
from typing import List, Dict, Any, Deque
from collections import deque, defaultdict
from fastapi import FastAPI, Request
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from ml.model import OnlineAnomaly, policy_tiering


API_PORT = int(os.getenv("API_PORT", "8001"))

app = FastAPI(title="NetApp Stream API", version="1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"],
)

# --- In-memory stores (demo) ---
RECENT_EVENTS: Deque[Dict[str, Any]] = deque(maxlen=5000)
ACTIONS: Deque[Dict[str, Any]] = deque(maxlen=1000)
THROUGHPUT_PER_MIN: Dict[int, int] = defaultdict(int)  # minute_bucket -> count
DEVICE_COUNTS: Dict[str, int] = defaultdict(int)
ANOMALY_COUNT_LAST_60 = deque(maxlen=60)  # store last 60 minutes anomaly counts
CUR_MIN_BUCKET = int(time.time() // 60)
CUR_MIN_COUNT = 0

an = OnlineAnomaly(window=400)

class StreamEvent(BaseModel):
    device_id: str
    temperature: float
    bytes: int
    ts: float
    # Enriched by consumer:
    z_temp: float | None = None
    is_anomaly: bool | None = None
    is_temp_alert: bool | None = None
    minute_bucket: int | None = None

def _rotate_minute_if_needed(min_bucket:int):
    global CUR_MIN_BUCKET, CUR_MIN_COUNT
    if min_bucket != CUR_MIN_BUCKET:
        # finalize previous minute into THROUGHPUT_PER_MIN & anomaly window
        THROUGHPUT_PER_MIN[CUR_MIN_BUCKET] += CUR_MIN_COUNT
        CUR_MIN_BUCKET, CUR_MIN_COUNT = min_bucket, 0

@app.get("/health")
def health():
    return {
        "ok": True,
        "events": len(RECENT_EVENTS),
        "devices": len(DEVICE_COUNTS),
        "cur_minute": CUR_MIN_BUCKET,
        "cur_min_count": CUR_MIN_COUNT,
    }

@app.get("/stream/peek")
def stream_peek(n: int = 25):
    return list(RECENT_EVENTS)[-n:]

@app.get("/metrics")
def metrics():
    # compact view + include current minute
    last_30 = sorted(THROUGHPUT_PER_MIN.items())[-30:]
    # append current, live minute bucket as well
    if last_30 and last_30[-1][0] == CUR_MIN_BUCKET:
        last_30[-1] = (CUR_MIN_BUCKET, last_30[-1][1] + CUR_MIN_COUNT)
    else:
        last_30.append((CUR_MIN_BUCKET, CUR_MIN_COUNT))

    recent = list(RECENT_EVENTS)[-300:]
    anom_rate = sum(1 for e in recent if e.get("is_anomaly")) / max(1, len(recent))

    return {
        "throughput_per_min": last_30[-30:],  # keep 30 with the live one
        "events_total": len(RECENT_EVENTS),
        "devices": len(DEVICE_COUNTS),
        "anomaly_rate_recent": anom_rate,
    }


@app.get("/actions")
def get_actions(n: int = 50):
    return list(ACTIONS)[-n:]

@app.post("/stream/event")
async def stream_event(ev: StreamEvent):
    global CUR_MIN_COUNT
    payload = ev.model_dump()
    minute_bucket = payload.get("minute_bucket") or int(time.time() // 60)
    _rotate_minute_if_needed(minute_bucket)
    CUR_MIN_COUNT += 1
    DEVICE_COUNTS[payload["device_id"]] += 1

    # If consumer didn’t enrich (safety), run minimal scoring here
    if payload.get("z_temp") is None:
        score = an.score_event(payload)
        payload.update(score)

    RECENT_EVENTS.append(payload)

    # Triggers
    if payload.get("is_temp_alert"):
        ACTIONS.append({"ts": time.time(), "type": "raise_alert", "event": payload})
    action = policy_tiering(DEVICE_COUNTS, payload["device_id"])
    if action:
        ACTIONS.append({"ts": time.time(), "type": action, "event": payload})

    return {"ok": True}
