from __future__ import annotations
import os, json, random, time
from kafka import KafkaProducer

BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP", "localhost:9092")
TOPIC     = os.getenv("KAFKA_TOPIC", "sensor_stream")

def main():
    p = KafkaProducer(bootstrap_servers=BOOTSTRAP,
                      value_serializer=lambda x: json.dumps(x).encode("utf-8"))
    devices = [f"dev-{i:03d}" for i in range(1, 26)]
    print(f"[producer] sending to {BOOTSTRAP} topic={TOPIC}")
    while True:
        ev = {
            "device_id": random.choice(devices),
            "temperature": round(random.gauss(65, 8), 2),  # mean 65C, sd 8
            "bytes": random.randint(500, 50_000),
            "ts": time.time(),
        }
        p.send(TOPIC, ev)
        print("[producer] sent:", ev)
        time.sleep(0.35)  # ~170 ev/min
if __name__ == "__main__":
    main()
