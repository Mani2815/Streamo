# Phase 3: Data Quality & PostgreSQL Serving Layer

## Overview
Phase 3 extends the core streaming engine with a rigorous Data Quality (DQ) framework and implements an idempotent PostgreSQL Serving Layer to transform Streamo's data into queryable, analytics-ready structures.

## Architecture
```text
Spark Structured Streaming
         ↓
    JSON Parsing 
         ↓
  Data Quality Engine (is_valid, null_checks, range_checks, format_checks)
         ├── [Invalid] → MinIO (streamo-quarantine)
         └── [Valid]
                ↓
           Deduplication (dropDuplicates on event_id)
                ↓
           MinIO (streamo-processed/records & aggregates)
                &
           PostgreSQL Serving Layer via JDBC `foreachBatch` UPSERTS
```

## Data Quality Rules
- **Null Checks**: Fails if `event_id`, `source`, `ingested_at`, `id`, `timestamp`, `temperature`, or `humidity` are null.
- **Range Checks**: 
  - `temperature` BETWEEN -50 AND 100
  - `humidity` BETWEEN 0 AND 100
- **Format Checks**: `event_id` must match a valid UUID regex.

Invalid records are routed directly to `s3a://streamo-quarantine` and ignored by downstream analytics.

## PostgreSQL Serving Layer
PostgreSQL `streamo` database acts as the primary analytics serving layer.
- `processed_records`: Contains validated, flattened, typed event records.
- `telemetry_aggregates`: Contains 5-minute windowed averages and counts.
- `data_quality_metrics`: Contains total valid, invalid, range/null violations and calculated quality rates.

### Idempotency
Spark writes to PostgreSQL using `foreachBatch` via PySpark. We programmatically execute raw `INSERT ... ON CONFLICT (...) DO UPDATE` statements (`UPSERT`) using the `psycopg2` driver. 
- A duplicate `event_id` hitting `processed_records` will simply update the row in-place, preventing logical duplication.
- A duplicate window aggregation hitting `telemetry_aggregates` updates the average safely.

## Control Plane API
FastAPI now serves data out of PostgreSQL for reporting:
- `GET /api/v1/quality/summary`: DQ summary grouped by source.
- `GET /api/v1/data/{source}`: Paginated raw processed events.
- `GET /api/v1/data/{source}/aggregates`: Paginated windowed aggregates.

## Integration Tests
1. **Valid Data**: Normal telemetry flows successfully to Postgres and `/data/mock`.
2. **Invalid Data**: Emitting `humidity=150` triggered a `range_violation` metric bump and omitted the record from PostgreSQL.
3. **Duplicate Data**: Emitting identical `event_id`s multiple times resulted in exactly **1** row being materialized in PostgreSQL due to `ON CONFLICT` deduplication.

## Known Limitations
- The PySpark job executes the UPSERTs on the Driver node within `foreachBatch`. This is highly efficient for small micro-batches (Streamo defaults to small sliding windows), but for extreme high-throughput scale, a distributed JDBC writer with partition-level execution would be required.
