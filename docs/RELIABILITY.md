# Reliability Report

This document outlines the systematic failure tests performed on Streamo to validate its resiliency guarantees. All tests were performed locally under load using deterministic failure injection.

## Test Matrix & Results

| Scenario | Expected Behavior | Observed Behavior | Recovery |
| :--- | :--- | :--- | :--- |
| **API 429 Rate Limit** | Ingestion service utilizes exponential backoff to retry, avoiding data loss. | Successfully triggered HTTP 429. The ingestion service caught the error, executed 4 retry attempts via `tenacity`, and resumed smoothly when the API recovered. | **Automatic**: Recovered in 20s. |
| **Spark Interruption** | Processing halts, Kafka retains backlog, Spark resumes gracefully using checkpoints. | Spark stopped while ingestion flooded Kafka with 1,500 events (100 eps for 15s). Upon restart, Spark recovered its delta checkpoint and processed the entire backlog in 1 macrobatch. | **Automatic**: Backlog cleared in ~35s. |
| **Kafka Backpressure** | Buffer accommodates ingestion while downstream is bottlenecked. | Monitored consumer lag during the Spark Interruption test. Kafka safely buffered the 1,500 event surge with 0 rejected writes. | **Automatic**: No intervention needed. |
| **MinIO Failure** | Spark fails on missing checkpoint references; data remains safely in Kafka. | MinIO outage triggers a Delta Lake `FileNotFoundException` in Spark. Because Streamo is decoupled, Kafka buffers incoming data. | **Manual**: Increment checkpoint version (`v6` -> `v7`) and restart Spark. |
| **PostgreSQL Failure** | Spark JDBC driver retries. Upon total failure, the streaming query aborts and restarts. | Spark microbatch failed to write to Postgres, aborting the stream. The container restarts until Postgres is available. No data is lost because offsets are not committed to Delta until the batch completes. | **Automatic**: Resumes on DB up. |
| **Invalid Data** | Data Quality engine reroutes malformed JSON payloads to Quarantine. | Injected `humidity = 150` and an invalid temperature type. Verified exactly `0` rows reached PostgreSQL. | **N/A** |
| **Duplicate Data** | Processing is idempotent; exact duplicate events yield 1 logical record. | Injected the same `event_id` payload 3 times consecutively. PostgreSQL UPSERT logic guaranteed exactly `1` row was materialized. | **N/A** |

## Conclusion
Streamo correctly leverages the decoupling provided by Kafka. All transient network and downstream failures (PostgreSQL, APIs) are handled either by exponential backoff or crash-looping with zero data loss. MinIO storage failures remain the sole area requiring manual operator intervention.
