# Phase 2: Streaming Data Processing

## Overview
Phase 2 establishes the core streaming processing engine of Streamo. It reads from the Kafka event bus and uses **Apache Spark Structured Streaming** to continuously process telemetry events in real time. 

## Data Flow
```text
API
 ↓
Kafka (streamo.raw.mock)
 ├──→ MinIO Raw (s3a://streamo-raw/source=mock/)
 └──→ Spark Processing Application
       ↓
   MinIO Processed (s3a://streamo-processed/records/ & s3a://streamo-processed/aggregates/)
```

## Architecture

### Spark Processing Application
A PySpark Structured Streaming application (`services/processing/app/main.py`) runs concurrently with our infrastructure. 

The application launches four parallel streams from the `streamo.raw.mock` topic:
1. **Quarantine Stream**: Invalid JSON objects that cannot be parsed by our explicit schema are filtered out and written to `streamo-quarantine` for inspection, ensuring the main pipeline never crashes.
2. **Raw Persistence**: Valid event envelopes are immediately persisted in Parquet format, partitioned logically by `year, month, day, hour`. This acts as an immutable historical record.
3. **Processed Records (Deduplication)**: Events are normalized, flattened, and typed correctly. A 10-minute watermark bounds state, allowing late-arriving events to be gracefully processed while identical `event_id`s are dropped.
4. **Aggregated Metrics**: A 5-minute tumbling window computes the average temperature and humidity of the events and writes the results as Parquet.

### Resilience and Recovery
- All streams use checkpointing stored in `s3a://streamo-processed/checkpoints/*`.
- If Spark or MinIO fails, the streaming query automatically resumes processing from the exact offset it left off, catching up on the backlog piled up in Kafka.

## Storage Layout
```text
streamo-raw/
└── source=mock/
    └── year=2026/
        └── month=08/
            └── day=09/
                └── hour=17/
                    └── part-*.snappy.parquet

streamo-processed/
├── records/
│   └── source=mock/
│       └── part-*.snappy.parquet
└── aggregates/
    └── source=mock/
        └── part-*.snappy.parquet
```

## Known Limitations
- The current implementation processes all streams using a single Spark application context. While efficient, a crash in one query (if not handled robustly) could restart the entire application context.
- Running Kafka, Spark, Postgres, and MinIO all locally on a single machine requires significant RAM. Memory allocation tuning (`docker-compose.yml`) is necessary for low-end hardware.
