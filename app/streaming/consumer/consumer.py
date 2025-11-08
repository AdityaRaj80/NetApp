from __future__ import annotations
import os, json, time
from kafka import KafkaConsumer
import requests
from ml.features import ThroughputMeter
from ml.model import OnlineAnomaly

BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP", "localhost:9092")
TOPIC     = os.getenv("KAFKA_TOPIC", "sensor_stream")
GROUP     = os.getenv("KAFKA_GROUP", "netapp-consumer")
API       = os.getenv("STREAM_API", "http://localhost:8001")

tm = ThroughputMeter()
an = OnlineAnomaly(window=400)

def main():
    consumer = KafkaConsumer(
        TOPIC,
        bootstrap_servers=BOOTSTRAP,
        group_id=GROUP,
        value_deserializer=lambda x: json.loads(x.decode("utf-8")),
        enable_auto_commit=True,
        auto_offset_reset="earliest",
    )
    print(f"[consumer] connected to {BOOTSTRAP}, topic={TOPIC}, group={GROUP}")
    for msg in consumer:
        ev = msg.value
        # expected base fields: device_id, temperature, bytes, ts
        bucket_info = tm.tick()
        minute_bucket = bucket_info["bucket"]

        # enrich with ML scoring
        score = an.score_event(ev)
        ev_enriched = {
            **ev,
            **score,
            "minute_bucket": minute_bucket
        }
        try:
            r = requests.post(f"{API}/stream/event", json=ev_enriched, timeout=2.5)
            if r.ok:
                print(f"[consumer] fwd -> API ok | dev={ev['device_id']} temp={ev['temperature']} z={score['z_temp']:.2f} anom={score['is_anomaly']}")
            else:
                print("[consumer] API error:", r.status_code, r.text[:200])
        except Exception as e:
            print("[consumer] API post failed:", e)

if __name__ == "__main__":
    main()
