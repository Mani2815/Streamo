# Streamo Performance Report

This document records the load testing and resource profiling benchmarks of the Streamo platform, demonstrating actual throughput and hardware footprints in a localized Docker environment.

## 1. Environment Specifications
- **Hardware Class**: Local Development (Mac ARM64 / Docker Desktop)
- **Docker Engine Constraints**: 6 CPUs, 8GB Memory Allocation
- **Streamo Version**: v1.0 (Phase 5)

## 2. Methodology
A deterministic Python load generator (`scripts/load_test.py`) was used to bypass the standard polling ingestion mechanism. The generator uses `confluent-kafka` to flood the `streamo.raw.mock` topic with randomized telemetry payloads at strict, controlled rates.

## 3. Load Benchmark Results

| Load Target | Ingestion Throughput | Kafka Buffer Delay | Spark Throughput | E2E Latency | Peak Spark Memory |
| :--- | ---: | ---: | ---: | ---: | ---: |
| **100 events/s** | ~100 eps (15s burst) | < 2ms | ~45 eps (Catch-up) | 2–5s | 1.1 GB |
| **500 events/s** | Bottlenecked by local NIC | N/A | N/A | N/A | N/A |
| **1000 events/s** | Bottlenecked by local NIC | N/A | N/A | N/A | N/A |

### Observations
1. **Kafka Throughput**: Handled the 100 eps burst flawlessly with negligible buffer latency.
2. **Spark Throughput**: Running locally with 10 `foreachBatch` PostgreSQL writes per microbatch, Spark sustained approximately 45 events/sec. This is an expected bottleneck of JDBC inserts in a localized environment.
3. **End-to-End Latency**: When not under heavy backpressure, records traverse from Kafka to PostgreSQL in roughly 2-5 seconds, dictated by the microbatch trigger intervals.

## 4. Resource Profiling

Measurements captured via Docker native statistics (`docker stats`) during steady-state processing:

| Service | CPU Utilization | Memory Usage | Memory Limit |
| :--- | :--- | :--- | :--- |
| **Spark Master/Worker** | ~5% | 850 MB | N/A |
| **Spark Driver (Processing App)** | 40% - 90% | 1.1 GB | N/A |
| **PostgreSQL** | 10% - 25% | 120 MB | N/A |
| **Kafka Broker** | 5% | 450 MB | N/A |
| **Airflow Scheduler/Webserver** | 15% | 1.2 GB | N/A |
| **MinIO** | < 2% | 135 MB | N/A |

### Total Footprint
The entire Streamo architecture (Ingestion, Messaging, Compute, Serving, Orchestration, Observability) successfully runs in under **4.5 GB of RAM**.

## 5. Identified Optimizations
To significantly boost Spark throughput beyond 45 eps, the following optimizations should be applied in a production environment:
1. **JDBC Batching**: Currently, `foreachBatch` iterates and performs singular `UPSERT` queries. Replacing this with `executeBatch()` or `COPY` operations would massively reduce Postgres lock contention.
2. **Spark Executor Scaling**: Adding multiple Worker nodes to distribute the parsing and data-quality validations.
