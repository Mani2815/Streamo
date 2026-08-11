# Streamo
> Real-Time API-to-Analytics Data Engineering Platform

## Problem
External API data often needs ingestion, buffering, processing, validation, storage, and observability before it becomes useful for downstream analytics and business intelligence. Doing this at scale requires a resilient, decoupled architecture that can handle network outages, bad data, and high throughput without dropping a single event.

## Solution
**Streamo** provides an end-to-end, locally-reproducible data pipeline. It ingests data from external HTTP APIs, buffers it durably in Kafka, processes and validates it using Spark Structured Streaming, stores the raw and processed data in an S3-compatible Data Lake, and serves the clean data via PostgreSQL and a FastAPI control plane. The entire system is orchestrated by Airflow and monitored in real-time via Grafana.

## Architecture

```text
REST API
   ↓
Python Ingestion
   ↓
Kafka
   ↓
Spark Structured Streaming
   ├──────────────→ MinIO Raw (S3)
   │
   ├──────────────→ MinIO Processed (S3)
   │
   └──────────────→ Data Quality Engine
                         ↓
                    PostgreSQL
                    /        \
                   ↓          ↓
              FastAPI      Grafana
            Control Plane  Observability

                    Airflow
                       ↓
          Quality / Aggregation / Maintenance
```

## Technology Stack

- **Ingestion**: Python, FastAPI, HTTPX, Tenacity
- **Streaming**: Apache Kafka
- **Processing**: Apache Spark Structured Streaming
- **Storage**: MinIO (S3), PostgreSQL, Parquet
- **Orchestration**: Apache Airflow
- **Observability**: Grafana
- **Infrastructure**: Docker Compose

## Features
- **API Polling & Backoff**: Robust ingestion service that natively handles HTTP 429s and 500s using exponential backoff.
- **Kafka Buffering**: Complete decoupling of ingestion from processing, allowing the pipeline to safely queue data during downstream outages.
- **Spark Structured Streaming**: Event-time processing, watermark-based deduplication, and 5-minute tumbling window aggregations.
- **Data Quality Engine**: Automated quarantine of malformed JSON payloads, null values, and out-of-range sensor data to an isolated MinIO bucket.
- **PostgreSQL Serving Layer**: High-speed SQL analytics layer populated via idempotent JDBC `UPSERTS`.
- **Airflow Orchestration**: Scheduled background tasks that guarantee data freshness, monitor quality SLA rates, and prune historical Postgres records.
- **Infrastructure as Code**: Grafana Dashboards and Datasources are provisioned automatically on startup.

## Quick Start
To launch the entire platform locally:

```bash
# 1. Start the infrastructure
docker compose up -d

# 2. Configure a source in the Control Plane
curl -X POST "http://localhost:8000/api/v1/sources/" \
     -H "Content-Type: application/json" \
     -d '{"name": "mock", "url": "http://mock-api:8001/data", "poll_interval": 10}'
```
- **Airflow UI**: [http://localhost:8082](http://localhost:8082) (admin/admin)
- **Grafana UI**: [http://localhost:3000](http://localhost:3000) (admin/admin)
- **MinIO UI**: [http://localhost:9001](http://localhost:9001) (minioadmin/minioadmin)

## Documentation
- [System Architecture](docs/ARCHITECTURE.md)
- [Technical Decisions & Tradeoffs](docs/TECHNICAL_DECISIONS.md)
- [Reliability & Failure Testing](docs/RELIABILITY.md)
- [Performance & Profiling](docs/PERFORMANCE.md)
- [Operations Guide](docs/OPERATIONS.md)

## Limitations
- Streamo currently runs on a single Docker Compose network. While the architecture is designed to scale horizontally across multiple nodes (Kafka cluster, Spark cluster), local deployment is restricted by Docker Desktop memory limits (Recommended: 8GB RAM).
- The pipeline intentionally does not implement ML/AI features, multi-tenancy, or billing, maintaining strict focus on core Data Engineering fundamentals.
