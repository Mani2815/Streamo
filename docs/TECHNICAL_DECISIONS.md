# Technical Decisions & Architecture Tradeoffs

This document outlines the core infrastructure decisions and design tradeoffs made during the development of Streamo. It explains why specific technologies were chosen over alternatives to satisfy the system's real-time Data Engineering requirements.

## Core Component Decisions

### 1. Kafka as the Messaging Layer
**Reason**: Decoupling, Buffering, and Replayability.
Kafka serves as the central nervous system, isolating the Ingestion layer from the Processing layer. This ensures that if the Spark engine goes down for maintenance (or crashes), the API pollers can continue accepting and buffering data safely. Kafka's persistent log enables complete replay of data in the event of pipeline logic changes.

### 2. Spark Structured Streaming for Compute
**Reason**: Event-time processing, Watermarking, and Exactly-Once Semantics.
While simpler stream processors exist, Spark provides native support for complex Event-Time operations. Streamo utilizes Spark's watermarking capabilities to safely compute 5-minute tumbling window aggregates while gracefully handling late-arriving data. Additionally, Spark's Delta Lake checkpointing integrates perfectly with Kafka offsets to provide end-to-end exactly-once resilience.

### 3. MinIO for the Data Lake
**Reason**: S3-compatibility without cloud cost.
MinIO provides a localized, S3-compliant object store. Spark utilizes it identically to AWS S3, allowing the raw data (`streamo-raw`) and processed Parquet data (`streamo-processed`) to be safely retained. Using MinIO enables full reproducibility of the Data Lake on a local developer machine.

### 4. PostgreSQL for the Serving Layer
**Reason**: Relational integrity and sub-second SQL accessibility.
Instead of forcing the FastAPI control plane or Grafana to query heavy Parquet files directly, Streamo uses Postgres as an operational Serving Layer. Postgres allows for highly efficient `UPSERT` (ON CONFLICT DO UPDATE) operations, guaranteeing idempotency during Spark microbatches. 

### 5. Airflow for Orchestration
**Reason**: Scheduled maintenance and Quality monitoring.
Airflow is deliberately kept out of the streaming data path. Instead, it is used for macro-level orchestration: running daily cleanup jobs to purge old PostgreSQL records, rolling up aggregates, and executing periodic Data Quality alerts to ensure pipeline SLAs (freshness > 15m) are met.

### 6. Grafana for Observability
**Reason**: Real-time SQL visualization.
Grafana hooks directly into PostgreSQL to provide a live control tower of pipeline health. It requires zero custom UI code and can be provisioned automatically via Infrastructure-as-Code YAML files.

---

## Architecture Tradeoffs

### MinIO instead of Cloud S3
- **Tradeoff**: While a true cloud environment would use AWS S3 for durability, MinIO was chosen to keep the entire Streamo stack runnable locally via Docker Compose. This trades off multi-AZ durability for zero-cost developer reproducibility. The API interface remains identical.

### PostgreSQL instead of a Cloud Data Warehouse
- **Tradeoff**: Technologies like Snowflake or BigQuery are standard for analytics. However, for a portfolio-scale workload where sub-second latency is required by a serving API (FastAPI) and Grafana, PostgreSQL is far superior and significantly cheaper to run locally.

### Airflow Alongside Spark
- **Tradeoff**: Introducing Airflow increases the memory footprint by ~1GB. However, attempting to run scheduled database maintenance or alerting tasks directly inside Spark Structured Streaming breaks the paradigm of a streaming engine. Airflow provides the necessary DAG orchestration that streaming engines lack.

### Single-Node Infrastructure
- **Tradeoff**: Streamo currently runs on a single Docker Compose network. While it does not utilize a Kubernetes cluster for true horizontal scaling, the architecture itself is structurally distributed. Kafka, Spark, and MinIO can all be scaled across multiple nodes without modifying the Streamo codebase.
