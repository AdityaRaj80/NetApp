# MovingData: Intelligent Multi-Cloud Data Pipeline

> **Secure, adaptive data-in-motion demo built for the NetApp "Data in Motion" hackathon.**
>
> MovingData encrypts payloads end-to-end, streams telemetry, and keeps objects in sync across simulated AWS S3 (MinIO), Azure Blob (Azurite), and Google Cloud Storage (FakeGCS).

---

## Table of Contents
1. [Project Vision](#project-vision)
2. [Solution Highlights](#solution-highlights)
3. [System Architecture](#system-architecture)
4. [Repository Layout](#repository-layout)
5. [Core Components](#core-components)
6. [Prerequisites](#prerequisites)
7. [Running the Platform](#running-the-platform)
   - [Full stack with Docker Compose](#full-stack-with-docker-compose)
   - [Streaming sandbox (optional)](#streaming-sandbox-optional)
   - [Local Python development](#local-python-development)
8. [Configuration Reference](#configuration-reference)
9. [Security & Compliance](#security--compliance)
10. [Predictive Tiering & Automation](#predictive-tiering--automation)
11. [Observability & Verification](#observability--verification)
12. [Troubleshooting](#troubleshooting)
13. [Roadmap](#roadmap)
14. [Team](#team)

---

## Project Vision
Modern data teams juggle analytics workloads, compliance audits, and operational telemetry that span multiple clouds. The goal of MovingData is to demonstrate how an intelligent control plane can:

* keep data encrypted throughout its life cycle,
* replicate objects consistently across heterogeneous providers,
* stream access events in real time, and
* recommend optimal storage tiers using lightweight machine learning.

The project was originally produced for the NetApp **Data-in-Motion** hackathon and continues to evolve as a reference for secure, multi-cloud data automation.

---

## Solution Highlights
* **End-to-end encryption** – Application-level encryption with Fernet, combined with MinIO SSE-KMS for data-at-rest protection.
* **Multi-cloud replication** – Deterministic replication and checksum verification across MinIO, Azurite, and FakeGCS from a single API call.
* **Event-driven automation** – Kafka-compatible Redpanda broker powers telemetry ingestion and synthetic workload generation.
* **Predictive tiering** – Gradient-boosted (or centroid fallback) model recommends hot/warm/cold tiers based on historical access patterns.
* **Mission control dashboard** – Streamlit UI surfaces file inventories, policy decisions, alerts, and live stream metrics.
* **Container-first deployment** – One command (`docker compose up`) brings the complete lab online for demo or experimentation.

---

## System Architecture
```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              Control Plane (API)                            │
│  FastAPI service                                                            │
│  • Encrypts payloads, enforces role-based access                            │
│  • Calls orchestrator to seed data, move objects, and verify replicas       │
│  • Streams access metrics to Redpanda & optional stream microservice        │
└─────────────────────────────────────────────────────────────────────────────┘
           │                        │                          │
           │                        │                          │
┌──────────▼──────────┐  ┌──────────▼──────────┐    ┌──────────▼──────────┐
│       MinIO         │  │       Azurite       │    │       FakeGCS        │
│  (AWS S3 simulator) │  │ (Azure Blob emu.)   │    │ (GCS emulator)       │
└──────────┬──────────┘  └──────────┬──────────┘    └──────────┬──────────┘
           │                        │                          │
           └───────────────┬────────┴───────────────┬──────────┘
                           │                        │
                 ┌─────────▼─────────┐   ┌──────────▼───────────┐
                 │     MongoDB       │   │      Redpanda         │
                 │ Metadata & policy │   │ Kafka-compatible bus  │
                 └─────────┬─────────┘   └──────────┬───────────┘
                           │                        │
                ┌──────────▼──────────┐   ┌─────────▼───────────┐
                │  Streamlit UI       │   │  Streaming services  │
                │ Mission control     │   │ Producer / consumer  │
                └─────────────────────┘   └──────────────────────┘
```

---

## Repository Layout
| Path | Purpose |
| ---- | ------- |
| `README.md` | You are here – comprehensive documentation for the project. |
| `hackathon-main/NetApp-main/app/` | Python sources for the API, orchestrator, streaming utilities, and Streamlit dashboards. |
| `hackathon-main/NetApp-main/infra/` | Docker Compose definitions and container assets for local deployment. |
| `hackathon-main/NetApp-main/data/` | Seed files and simulated blob storage directories used during demos. |
| `hackathon-main/NetApp-main/ui/` | Stream-specific dashboards used by the optional streaming sandbox. |
| `hackathon-main/NetApp-main/README_NetApp_Data_in_Motion.md` | Original hackathon write-up with high-level talking points. |

---

## Core Components
### FastAPI control plane (`app/api/server.py`)
* Publishes REST endpoints for seeding demo data, initiating file moves, exposing telemetry, and managing the predictive model.
* Encrypts every payload before dispatching it to the storage layer and enforces role-aware decryption via the security manager.
* Streams synthetic access events to Kafka/Redpanda and forwards sensor events to the optional streaming API.

### Orchestrator (`app/orchestrator/`)
* `mover.py` guarantees buckets exist, seeds objects, and shuffles blobs across providers while preserving encryption.
* `rules.py` captures rule-based policies (e.g., temperature or latency driven decisions) that supplement ML predictions.
* `consistency.py` manages replica verification, backoff-aware retries, and conflict detection when providers diverge.
* `predictive.py` encapsulates the gradient boosting / centroid fallback model used for tier recommendations.

### Security manager (`app/security/policies.py`)
* Centralizes encryption keys, allowed roles, and Fernet helpers per storage location.
* Allows overrides via environment variables to plug in customer-specific KMS material.

### Streamlit dashboards (`app/ui/dashboard.py`, `ui/stream_dashboard.py`)
* `dashboard.py` powers the mission control page that visualizes file inventories, alerts, policy decisions, and stream metrics.
* `stream_dashboard.py` (optional sandbox) highlights anomaly detection on raw sensor data flowing through the streaming API.

### Streaming utilities (`app/streaming/`)
* Lightweight Kafka producers/consumers simulate IoT-style temperature events and forward anomalies to the API.
* Optional FastAPI microservice (`infra/stream-compose.yml`) exposes `/stream/event` and `/stream/peek` endpoints for stream visualization.

---

## Prerequisites
| Requirement | Minimum Version | Notes |
| ----------- | ---------------- | ----- |
| Docker | 20.10+ | Required for the full containerized demo. |
| Docker Compose | v2.17+ | Compose file targets version `3.x`. |
| Python | 3.11 | Needed only for local development outside containers. |
| Make / Bash | Optional | Simplifies command execution on macOS/Linux. |

---

## Running the Platform
### Full stack with Docker Compose
1. **Clone the repository**
   ```bash
   git clone https://github.com/AdityaRaj80/MovingData.git
   cd MovingData/hackathon-main/NetApp-main/infra
   ```
2. **Boot all services**
   ```bash
   docker compose up -d --build
   ```
3. **Verify container health**
   ```bash
   docker compose ps
   ```
4. **Access the experiences**
   * FastAPI docs: http://localhost:8001/docs
   * Mission control dashboard: http://localhost:8501
   * MinIO console: http://localhost:9001 (user `minio`, password `minio12345`)
   * Redpanda broker: Kafka bootstrap available on `localhost:9092`

> ℹ️ Buckets/containers are created automatically on first run. The API seeds demo objects into `netapp-bucket` (S3), `netapp-blob` (Azure), and `netapp-gcs` (GCP) when you call the seeding endpoints below.

#### Useful API workflows
```bash
# Populate demo files and baseline metadata
curl -X POST http://localhost:8001/seed

# Trigger replication test with checksum validation across providers
curl -X POST http://localhost:8001/storage_test

# Simulate burst of access events and streaming traffic
curl -X POST http://localhost:8001/simulate/burst -H "Content-Type: application/json" -d '{"events": 250}'
```

### Streaming sandbox (optional)
If you want to experiment with the standalone streaming microservice and Streamlit dashboard, run:
```bash
cd MovingData/hackathon-main/NetApp-main/infra
docker compose -f stream-compose.yml up -d --build
```
This stack exposes:
* Stream API (FastAPI): http://localhost:8001/stream/docs
* Stream dashboard: http://localhost:8601
* Kafka producer/consumer wired to the same topic (`sensor_stream`) used by the main platform.

### Local Python development
You can run the FastAPI service directly on your workstation for debugging:
```bash
cd MovingData/hackathon-main/NetApp-main/app
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn api.server:app --reload --port 8001
```
Override environment variables as needed (see below) to point at local or remote storage endpoints. The Streamlit UI can be started with:
```bash
streamlit run ui/dashboard.py --server.port 8501
```

---

## Configuration Reference
The services pick up defaults from `infra/docker-compose.yml`, but you can customize behavior with environment variables:

| Variable | Purpose | Default |
| -------- | ------- | ------- |
| `KAFKA_BOOTSTRAP` | Kafka/Redpanda bootstrap broker used by the API and streaming jobs. | `redpanda:9092` |
| `TOPIC_ACCESS` | Kafka topic for access events. | `access-events` |
| `MONGO_URL` | MongoDB connection string for metadata. | `mongodb://mongo:27017` |
| `S3_ENDPOINT` / `S3_ACCESS_KEY` / `S3_SECRET_KEY` | MinIO connection details. | `http://minio:9000`, `minio`, `minio12345` |
| `AZURITE_BLOB_URL` | Azurite blob endpoint. | `http://azurite:10000/devstoreaccount1` |
| `GCS_ENDPOINT` | FakeGCS base URL. | `http://fakegcs:4443` |
| `S3_BUCKET` / `GCS_BUCKET` | Target buckets per provider. | `netapp-bucket`, `netapp-gcs` |
| `ALERT_*` variables | Thresholds for latency, cost, and stream anomaly alerts. | Tuned defaults in `api/server.py` |
| `ENABLE_SYNTHETIC_LOAD` | Toggle background traffic simulation. | `1` (enabled) |
| `S3_ENCRYPTION_KEY`, `AZURE_ENCRYPTION_KEY`, `GCS_ENCRYPTION_KEY` | Optional base64 Fernet keys that override built-in defaults per location. | Pre-generated demo keys |
| `S3_ALLOWED_ROLES`, etc. | CSV role overrides for RBAC enforcement. | Location-specific defaults + `system` |

When extending the system, add new variables to the Compose files and document them here to keep the reference current.

---

## Security & Compliance
* **Application encryption** – Every object body is encrypted using the Fernet symmetric algorithm before it leaves the API process. Keys are stored per location and may be swapped via environment variables at runtime.
* **MinIO SSE-KMS** – The MinIO container enables server-side encryption with the static key alias `netapp-key`, providing an additional layer of protection for data at rest.
* **Role-aware access control** – The security manager validates that callers possess at least one authorized role before decrypting or encrypting payloads for a given location. This allows different departments (analytics, operations, compliance) to have scoped access.
* **Audit metadata** – Encryption policy descriptors are persisted alongside file metadata in MongoDB, making it easy to export evidence for audits.

To confirm encryption status:
```bash
# Validate MinIO KMS key rotation/health
docker exec -it infra-minio-1 sh -lc "mc admin kms key status local"

# Inspect a replicated object and confirm SSE-KMS metadata
docker exec -it infra-minio-1 sh -lc "mc stat local/netapp-bucket/file_001.txt"
```

---

## Predictive Tiering & Automation
The orchestrator blends rule-based policies with ML-backed predictions to decide whether content should live in hot, warm, or cold storage:

1. **Feature extraction** – Access frequency, latency, size, recent anomalies, and cost estimates are tracked per file.
2. **Model inference** – `TierPredictor` (HistGradientBoosting or centroid fallback) recommends the optimal tier and provides confidence scores.
3. **Policy enforcement** – `rules.py` layers deterministic safeguards (e.g., force hot tier when latency spikes) before invoking the mover.
4. **Secure migration** – `mover.py` decrypts with the source key, re-encrypts with the destination key, and uploads the result with checksum validation.

You can submit custom training data to refine behavior:
```bash
curl -X POST http://localhost:8001/predictive/train \
  -H "Content-Type: application/json" \
  -d '{"auto_label": true, "records": [...]}'
```

---

## Observability & Verification
* **Health checks** – `GET /health` returns live service metrics, stream status, and alert counts.
* **Consistency reporting** – `GET /consistency/status` surfaces replica drift, retry counts, and last sync timestamps.
* **Streaming metrics** – `GET /streaming/metrics` exposes throughput, active device counts, and producer readiness for dashboard consumption.
* **UI drill-downs** – The Streamlit dashboard lists each file with estimated storage cost, location, alerts, and security policy metadata.

For quick manual validation:
```bash
# View the most recent access events stored in MongoDB
mongo --host localhost --eval 'db.access_events.find().sort({ts:-1}).limit(5)' netapp

# Tail container logs during a migration
docker compose logs -f api
```

---

## Troubleshooting
| Symptom | Possible Cause | Suggested Fix |
| ------- | -------------- | ------------- |
| Streamlit dashboard shows "API offline" | FastAPI container still warming up or crashed. | `docker compose logs api` and restart with `docker compose restart api`. |
| MinIO upload failures | Buckets missing or credentials invalid. | Call `/seed` to create buckets, verify creds in `.env` or Compose file. |
| Kafka timeouts | Redpanda container not reachable. | Confirm `docker compose ps`, ensure port 9092 unused, restart `redpanda`. |
| Decryption errors | Role mismatch or incorrect Fernet key overrides. | Ensure `principal_roles` include the expected role and Fernet keys are 32-byte base64 strings. |
| FakeGCS TLS issues on host | FakeGCS serves HTTP over port 4443. | Use `http://` URLs and disable certificate verification when testing manually. |

---

## Roadmap
* Integrate real cloud providers (AWS, Azure, GCP) via credentials rather than emulators.
* Add Kubernetes manifests and GitOps automation for production deployment.
* Expand predictive features with reinforcement learning and seasonal awareness.
* Incorporate cost-optimization feedback loops tied to real billing APIs.

---

## Team
* Pranak Shah (2022B2A71344P)
* Aditya Raj (2022B2A41583P)
* Kush Natani (2022B4AA1288P)
* Dhruv Gupta (2022A3PS1206P)

> **MovingData — redefining secure data in motion, one replica at a time.**
