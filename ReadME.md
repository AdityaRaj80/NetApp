Perfect — here’s your **complete `README.md`** for the GitHub repository.
It’s clean, structured, and ready to paste directly into your project root (`netapp-data-in-motion/README.md`).
It includes architecture overview, setup guide, commands, and verification checklist.

---

```markdown
# 📡 NetApp Data-in-Motion

A fully containerized **real-time data streaming pipeline** built with **Kafka**, **FastAPI**, and **Streamlit** — designed to simulate continuous IoT-style data, perform live anomaly detection, and trigger automated actions such as alerts and auto-tiering.

---

## 🚀 Overview

This system continuously streams random IoT-like sensor data through Kafka into a FastAPI backend, where events are analyzed in real-time.  
The backend triggers actions when thresholds are met (e.g., high temperature, frequent access, or ML anomaly).  
A live Streamlit dashboard visualizes incoming data, alerts, and system health.

---

## 🧠 Architecture

| Component | Role | Implementation | Container |
|------------|------|----------------|------------|
| **Kafka Broker** | Real-time message backbone | Confluent KRaft (no ZooKeeper) | `netapp-kafka` |
| **Producer** | Generates simulated IoT events (temperature, device ID, etc.) | `producer.py` | `stream-producer` |
| **Consumer** | Subscribes to Kafka, applies z-score anomaly detection, forwards events | `consumer.py` | `stream-consumer` |
| **Stream API** | Receives, processes, and stores events; triggers alerts & auto-tiering | `stream_server.py` (FastAPI) | `stream-api` |
| **Dashboard** | Visualizes live events, health, and actions | `stream_dashboard.py` (Streamlit) | `stream-ui` |

---

## ⚙️ Data Flow

```

[ Producer ] ─┐
│
│  (Kafka topic: sensor_stream)
▼
[ Kafka Broker (netapp-kafka) ]
│
▼
[ Consumer ] ─► [ FastAPI Stream API ] ─► [ Streamlit Dashboard ]

```

### Event Flow Summary

1. **Producer → Kafka**  
   `producer.py` creates JSON events (device ID, temperature, bytes, timestamp) and streams them into Kafka.

2. **Kafka Broker**  
   Acts as the real-time buffer for all events (topic: `sensor_stream`).

3. **Consumer → FastAPI**  
   `consumer.py` subscribes to Kafka, computes rolling z-scores, flags anomalies, and forwards enriched data to the FastAPI endpoint `/stream/event`.

4. **FastAPI Stream API**  
   Stores events in memory, maintains hotness counters, and triggers:
   - 🔥 `raise_alert` → if `temperature > 80°C`
   - 🚀 `tier_to_hot` → if a device sends > 20 messages
   - 🧠 `ml_anomaly` → if detected as outlier by ML logic  
   Provides endpoints:
   - `/health` → System stats  
   - `/stream/peek` → Latest events  
   - `/actions` → Triggered actions log  

5. **Streamlit Dashboard**  
   Pulls data every second from the API to render:
   - Live line chart of temperature vs time  
   - Table of recent events  
   - Health stats and triggered actions  

---

## 🐳 Docker Setup

All components are containerized and connected on the same network (`kafka_default`).

```

netapp-data-in-motion/
│
├── api/
│   └── stream_server.py
│
├── app/
│   └── streaming/
│       ├── producer/producer.py
│       └── consumer/consumer.py
│
├── ui/
│   └── stream_dashboard.py
│
└── infra/
├── kafka/docker-compose.kafka.yml
├── stream-compose.yml
└── (other infra like MinIO, Mongo, etc.)

````

---

## 💻 Running the Project (From Scratch)

### 1️⃣ Start Kafka
```bash
cd infra
docker compose -f kafka/docker-compose.kafka.yml up -d
````

### 2️⃣ Start Stream Stack

```bash
docker compose -f stream-compose.yml up -d
```

### 3️⃣ Open the Dashboard

* **Dashboard (UI):** [http://localhost:8601](http://localhost:8601)
* **Stream API (Health):** [http://localhost:8001/health](http://localhost:8001/health)

### 4️⃣ Verify Logs

```bash
docker logs -f stream-producer     # Should print "sent: {...}"
docker logs -f stream-consumer     # Should print "recv: {...}"
docker logs -f stream-api          # Should show POST /stream/event
```

---

## 🧠 Verification Checklist

| Check                | Command                                                                                  | Expected Output                      |
| -------------------- | ---------------------------------------------------------------------------------------- | ------------------------------------ |
| Kafka Broker running | `docker ps --filter name=netapp-kafka`                                                   | Shows `netapp-kafka` with port 19092 |
| Topic exists         | `docker exec -it netapp-kafka kafka-topics --list --bootstrap-server netapp-kafka:29092` | `sensor_stream`                      |
| API running          | `curl http://localhost:8001/health`                                                      | `{ "ok": true, "events": ... }`      |
| Dashboard            | Open [http://localhost:8601](http://localhost:8601)                                      | Live graph & data table              |
| Producer             | `docker logs stream-producer`                                                            | `[producer] sent: {...}`             |
| Consumer             | `docker logs stream-consumer`                                                            | `[consumer] recv: {...}`             |

---

## 🧩 Stopping and Cleaning Up

To stop all services:

```bash
docker compose -f stream-compose.yml down
docker compose -f kafka/docker-compose.kafka.yml down
```

Optional cleanup:

```bash
docker network prune -f
docker volume prune -f
```

---

## 🔁 Re-Running the Project

To restart after shutdown:

```bash
cd infra
docker compose -f kafka/docker-compose.kafka.yml up -d
docker compose -f stream-compose.yml up -d
```

Then revisit:

* API → [http://localhost:8001/health](http://localhost:8001/health)
* Dashboard → [http://localhost:8601](http://localhost:8601)

Everything will reconnect automatically (producer/consumer will resume streaming).

---

## ✨ Key Features

* **Event-driven architecture** with Kafka (no ZooKeeper)
* **Real-time anomaly detection** using rolling z-score
* **Automated tiering triggers** and temperature alerts
* **Live visualization** via Streamlit
* **Full Docker orchestration** with reproducible setup
* **Extensible** — you can plug in MinIO, Mongo, or ML models easily

---

## 📚 Endpoints Summary

| Endpoint        | Method | Description                                 |
| --------------- | ------ | ------------------------------------------- |
| `/health`       | GET    | Returns number of events and active devices |
| `/stream/event` | POST   | Receives and processes incoming event       |
| `/stream/peek`  | GET    | Shows recent events (default: last 10)      |
| `/actions`      | GET    | Returns recent triggered actions            |

---

## 🧠 Technical Notes

* **Kafka Ports:**

  * `19092` → external (for local testing)
  * `29092` → internal (for containers)

* **Environment Variables:**

  * `KAFKA_BOOTSTRAP`: Kafka bootstrap server
  * `STREAM_API`: API endpoint for consumer
  * `HOT_THRESHOLD`: Number of messages before tiering trigger
  * `TEMP_ALERT`: Temperature alert threshold

---

## 🤝 Contributors

**Aditya Raj**
BITS Pilani, Mechanical Engineering
Project: *NetApp Data-in-Motion*
Hackathon Submission for **NetApp Hackathon 2025**

---

## 🧾 License

This project is licensed under the MIT License.
Feel free to modify and extend.

---

> 🧩 *“Turning data-in-motion into insights-in-real-time.”*

```

---

Would you like me to include an **ASCII architecture diagram** or a **Mermaid diagram block** (which renders visually on GitHub) at the top of the README?  
It makes the README look really professional (especially for hackathon repos).
```
