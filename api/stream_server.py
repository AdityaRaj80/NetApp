from fastapi import FastAPI
from pydantic import BaseModel
from collections import defaultdict, deque
from typing import Dict, Any, List
from datetime import datetime
import requests, os

# NEW: Mongo
from pymongo import MongoClient

app = FastAPI(title='NetApp Stream API', version='1.2')

# In-memory
events: List[Dict[str, Any]] = []
hotness = defaultdict(int)
actions_q = deque(maxlen=200)

# Thresholds
HOT_THRESHOLD = int(os.getenv("HOT_THRESHOLD", "20"))
TEMP_ALERT   = float(os.getenv("TEMP_ALERT", "80.0"))
ORCH_URL     = os.getenv("ORCH_URL")

# Mongo wiring
MONGO_URL    = os.getenv("MONGO_URL", "mongodb://infra-mongo-1:27017/")
MONGO_DB     = os.getenv("MONGO_DB", "netapp_stream")
MONGO_COL    = os.getenv("MONGO_COL", "events")
mongo = MongoClient(MONGO_URL)
col  = mongo[MONGO_DB][MONGO_COL]

class StreamEvent(BaseModel):
    event_id: int
    device_id: int
    temperature: float
    bytes: int
    timestamp: float
    anomaly: bool | None = None  # optional (set by consumer)

def migrate_to_hot_tier(device_id: int):
    payload = {"device_id": device_id, "policy": "tier_to_hot", "source": "stream_api"}
    if ORCH_URL:
        try:
            r = requests.post(ORCH_URL, json=payload, timeout=2.0)
            print("[tier] orchestrator returned", r.status_code)
        except Exception as e:
            print("[tier] orchestrator offline:", e)
    else:
        print(f"[tier] simulated migrate_to_hot_tier(dev={device_id})")

@app.get('/health')
def health():
    return {'ok': True, 'events': len(events)}

@app.get('/stream/peek')
def peek(n: int = 10):
    return events[-n:]

@app.get('/actions')
def actions(n: int = 20):
    return list(actions_q)[-n:]

@app.post('/stream/event')
def stream_event(e: StreamEvent):
    obj = e.model_dump()
    # In-memory
    events.append(obj)
    hotness[e.device_id] += 1
    # Persist (idempotent enough for demo)
    col.insert_one({**obj, "ingested_at": datetime.utcnow()})

    local = []
    if hotness[e.device_id] >= HOT_THRESHOLD:
        local.append({'action': 'tier_to_hot', 'device_id': e.device_id, 'reason': 'high_access_frequency'})
        migrate_to_hot_tier(e.device_id)
    if e.temperature >= TEMP_ALERT:
        local.append({'action': 'raise_alert', 'device_id': e.device_id, 'reason': 'over_temperature'})
    if e.anomaly:
        local.append({'action': 'ml_anomaly', 'device_id': e.device_id, 'reason': 'zscore_outlier'})

    for a in local:
        a['at'] = datetime.utcnow().isoformat() + 'Z'
        actions_q.append(a)

    return {'received_at': datetime.utcnow().isoformat() + 'Z',
            'queued_events': len(events),
            'device_hotness': hotness[e.device_id],
            'actions': local}
