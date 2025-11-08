import os, json, time
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from pymongo import MongoClient
from kafka import KafkaProducer
from kafka.errors import KafkaError

from orchestrator.rules import decide_tier
from orchestrator.mover import ensure_buckets, put_seed_objects, move_object
from orchestrator.consistency import with_retry
from orchestrator.stream_consumer import ensure_topic

KAFKA_BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP", "redpanda:9092")
TOPIC_ACCESS    = os.getenv("TOPIC_ACCESS", "access-events")
MONGO_URL       = os.getenv("MONGO_URL", "mongodb://mongo:27017")

app = FastAPI(title="NetApp Data-in-Motion API")

# --- globals filled at startup ---
mongo: Optional[MongoClient] = None
db = None
coll_files = None
coll_events = None
producer: Optional[KafkaProducer] = None

# --------- models ----------
class AccessEvent(BaseModel):
    file_id: str
    event: str = "read"      # read/write
    ts: float = time.time()

class MoveRequest(BaseModel):
    file_id: str
    target: str  # "s3" | "azure" | "gcs"

# --------- helpers ----------
def seed_from_disk():
    """Load /data/seeds/metadata.json into Mongo and ensure objects are in S3."""
    from pathlib import Path
    import json

    seed_meta = Path("/data/seeds/metadata.json")
    if not seed_meta.exists():
        return {"seeded": 0, "note": "metadata.json not found"}

    # Tolerate UTF-8 BOM (Windows)
    try:
        text = seed_meta.read_text(encoding="utf-8-sig")
    except Exception:
        text = seed_meta.read_text()  # fallback

    meta = json.loads(text)

    with_retry(ensure_buckets, retries=10, backoff=0.5)
    with_retry(lambda: put_seed_objects("/data/seeds"), retries=10, backoff=0.5)

    cnt = 0
    for m in meta:
        coll_files.update_one(
            {"id": m["id"]},
            {"$set": {**m, "current_tier": "unknown", "current_location": "s3"}},
            upsert=True,
        )
        cnt += 1
    return {"seeded": cnt, "ok": True}

# --------- lifecycle ----------
@app.on_event("startup")
def on_startup():
    """
    Robust startup with retries. Keep /health responsive even if deps are warming up.
    """
    global mongo, db, coll_files, coll_events, producer

    # 1) Mongo
    def _mongo():
        global mongo, db, coll_files, coll_events
        mongo = MongoClient(MONGO_URL, serverSelectionTimeoutMS=2000)
        _ = mongo.admin.command("ping")
        db = mongo["netapp"]
        coll_files = db["files"]
        coll_events = db["events"]
    with_retry(_mongo, retries=10, backoff=0.5)

    # 2) Storage emulators (ensure + seed objects)
    with_retry(ensure_buckets, retries=10, backoff=0.5)
    with_retry(lambda: put_seed_objects("/data/seeds"), retries=10, backoff=0.5)

    # 3) Seed metadata idempotently (ignore errors)
    try:
        seed_from_disk()
    except Exception:
        pass

    # 4) Kafka/Redpanda (best-effort)
    def _producer():
        global producer
        producer = KafkaProducer(
            bootstrap_servers=KAFKA_BOOTSTRAP,
            value_serializer=lambda v: json.dumps(v).encode("utf-8"),
            request_timeout_ms=3000,
            api_version_auto_timeout_ms=3000,
        )
    try:
        with_retry(_producer, retries=10, backoff=0.5)
        ensure_topic(KAFKA_BOOTSTRAP, TOPIC_ACCESS)  # best-effort
    except Exception:
        producer = None  # allow API to run even without producer

# --------- endpoints ----------
@app.get("/health")
def health():
    return {"status": "ok", "app": "api"}

@app.get("/files")
def list_files():
    if coll_files is None:
        raise HTTPException(503, "db not ready")
    return list(coll_files.find({}, {"_id": 0}))

@app.get("/policy/{file_id}")
def policy(file_id: str):
    if coll_files is None:
        raise HTTPException(503, "db not ready")
    f = coll_files.find_one({"id": file_id}, {"_id":0})
    if not f:
        raise HTTPException(404, "file not found")
    tier = decide_tier(f.get("access_freq_per_day",0), f.get("latency_sla_ms",9999))
    return {"file_id": file_id, "recommendation": tier}

@app.post("/ingest_event")
def ingest_event(ev: AccessEvent):
    if coll_files is None:
        raise HTTPException(503, "db not ready")
    if producer is None:
        # still allow policy/metadata pathways to work
        coll_events.insert_one({"type": "access", **ev.model_dump(), "note":"no_stream"})
        coll_files.update_one({"id": ev.file_id}, {"$inc": {"access_freq_per_day": 1}}, upsert=True)
        return {"queued": False, "note": "streaming backend not ready"}
    doc = ev.model_dump()
    try:
        producer.send(TOPIC_ACCESS, doc)
        producer.flush(2)
    except KafkaError as e:
        raise HTTPException(503, f"kafka error: {e}")
    coll_events.insert_one({"type": "access", **doc})
    coll_files.update_one({"id": ev.file_id}, {"$inc": {"access_freq_per_day": 1}}, upsert=True)
    return {"queued": True}

@app.post("/move")
def move(req: MoveRequest):
    if coll_files is None:
        raise HTTPException(503, "db not ready")
    f = coll_files.find_one({"id": req.file_id})
    if not f:
        raise HTTPException(404, "file not found")
    with_retry(lambda: move_object(req.file_id, f.get("current_location","s3"), req.target))
    coll_files.update_one({"id": req.file_id}, {"$set": {"current_location": req.target}})
    coll_events.insert_one({"type":"move","file_id":req.file_id,"target":req.target,"ts":time.time()})
    return {"moved": True, "to": req.target}

@app.post("/seed")
def seed():
    if coll_files is None:
        raise HTTPException(503, "db not ready")
    return seed_from_disk()
