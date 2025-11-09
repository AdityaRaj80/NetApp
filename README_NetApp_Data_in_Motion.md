# 🔐 NetApp — Data-in-Motion

This project demonstrates a **secure, multi-cloud data pipeline** with automatic replication across **AWS S3 (MinIO)**, **Azure Blob (Azurite)**, and **GCP Storage (FakeGCS)** — complete with **encryption-at-rest**, **encryption-in-transit**, and **application-level encryption**.

Built for the **NetApp Hackathon**, it shows how intelligent storage policies can adapt to data movement, cost, and latency, while keeping data secure everywhere.

---

## 🚀 Architecture Overview

| Layer | Component | Description |
|-------|------------|-------------|
| **API Layer** | FastAPI (`infra-api`) | Handles requests, simulates events, performs encryption before storage. |
| **UI Layer** | Streamlit Dashboard (`infra-ui`) | Visualizes storage metrics, cost, and replication status. |
| **Storage Layer** | Multi-cloud setup using Docker Compose:<br>• **MinIO (S3)** — primary object storage<br>• **Azurite (Azure Blob)** — Azure simulation<br>• **FakeGCS** — GCP bucket simulation |
| **Data Plane** | Redpanda (Kafka) | Event streaming for “data in motion”. |
| **Database** | MongoDB | Metadata, policy, and event logging. |
| **Encryption** | App-level (Fernet) + MinIO KMS (SSE-KMS) | Double-layered protection for data at rest. |

---

## 🧩 Key Features

- **End-to-end Encryption**
  - App-level encryption (Fernet/AES) before upload → protects data even from storage layer.
  - **MinIO KMS with SSE-KMS** encryption-at-rest.
  - Verified KMS key: `netapp-key (Encryption ✔ | Decryption ✔)`.

- **Multi-Cloud Replication**
  - Automatically replicates objects to S3 (MinIO), Azure Blob, and GCS.
  - Endpoint verification for each storage provider.

- **Containerized Infrastructure**
  - All services orchestrated with Docker Compose.
  - Easy to spin up or down locally.

- **Streaming & Metrics**
  - Real-time event generation using Redpanda.
  - Streamlit dashboard for monitoring policy decisions and latency.

---

## ⚙️ Quick Start

### 1️⃣ Clone the Repository
```bash
git clone https://github.com/<your-username>/MovingData.git
cd hackathon-main/NetApp-main/infra
```

### 2️⃣ Build and Start Containers
```bash
docker compose up -d --build
```

All services (`api`, `ui`, `minio`, `azure`, `gcs`, `mongo`, `redpanda`) will start automatically.

---

## 🔒 Data Encryption Setup

### ✅ MinIO (S3) — Server-Side Encryption (SSE-KMS)
The `minio` service includes a **KMS configuration** in `docker-compose.yml`:

```yaml
environment:
  MINIO_ROOT_USER: minio
  MINIO_ROOT_PASSWORD: minio12345
  MINIO_KMS_SECRET_KEY: "netapp-key:BASE64_32B_KEY"
  MINIO_KMS_AUTO_ENCRYPTION: "on"
```

### ✅ Application-Level Encryption
The API uses **Fernet** encryption (`cryptography` package) to encrypt file bytes before upload.  
All stored files begin with `gAAAAA...` indicating encrypted ciphertext.

### 🔍 Verification

```bash
# check KMS status
docker exec -it infra-minio-1 sh -lc "mc admin kms key status local"

# sample output
Key: netapp-key
   - Encryption ✔
   - Decryption ✔

# check file encryption metadata
docker exec -it infra-minio-1 sh -lc "mc stat local/netapp-bucket/file_001.txt"
# -> Encryption: SSE-KMS (arn:aws:kms:netapp-key)
```

---

## 📡 API Endpoints

| Endpoint | Method | Description |
|-----------|--------|-------------|
| `/health` | GET | Health check for the API. |
| `/files` | GET | List existing files. |
| `/storage_test` | POST | Write test objects to all connected cloud storages. |
| `/seed` | POST | Create demo policy files. |
| `/consistency/status` | GET | View sync status across clouds. |
| `/simulate/burst` | POST | Simulate a burst of events for streaming. |

### Example
```bash
curl -X POST http://127.0.0.1:8001/storage_test
```

Response:
```json
{
  "s3": { "ok": true, "sha": "ad4917e1df52fe0c", "bucket": "netapp-bucket" },
  "azure": { "ok": true, "sha": "ad4917e1df52fe0c", "container": "netapp-blob" },
  "gcs": { "ok": true, "sha": "ad4917e1df52fe0c", "bucket": "netapp-gcs" }
}
```

---

## 📊 Verifying Encryption in MinIO

```bash
# list encrypted objects
docker exec -it infra-minio-1 sh -lc "mc ls local/netapp-bucket | head -n 5"

# show metadata
docker exec -it infra-minio-1 sh -lc "mc stat local/netapp-bucket/file_001.txt"
```

Example Output:
```
Encryption: SSE-KMS (arn:aws:kms:netapp-key)
Metadata  : Content-Type: binary/octet-stream
```

---

## 🧠 Tech Stack

- **Backend:** FastAPI, Python 3.11  
- **Frontend:** Streamlit  
- **Storage:** MinIO (S3), Azurite, FakeGCS  
- **Database:** MongoDB  
- **Streaming:** Redpanda  
- **Encryption:** Cryptography (Fernet) + MinIO KMS  
- **Containerization:** Docker & Docker Compose

---

## 🧾 Verification Summary

| Layer | Mechanism | Verified |
|--------|------------|----------|
| Application | Fernet (AES-128-GCM) | ✔ via ciphertext `gAAAAA...` |
| Storage | MinIO SSE-KMS | ✔ `Encryption: SSE-KMS (arn:aws:kms:netapp-key)` |
| KMS | Static Key `netapp-key` | ✔ Encryption / Decryption successful |
| Network | Containerized localhost bridge | ✔ isolated secure networking |


## 🏁 Status
✅ Fully functional multi-cloud encrypted data pipeline.  
✅ Verified encryption (Fernet + SSE-KMS).  
✅ Tested via `/storage_test` API endpoint.  
Ready for deployment & demonstration.
