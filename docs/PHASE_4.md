# Phase 4: Orchestration & Observability

## Overview
Phase 4 implements the orchestration and observability layer for Streamo. We use **Apache Airflow** to orchestrate metadata validation and background maintenance, and **Grafana** to visualize real-time pipeline telemetry and data quality.

## Airflow Orchestration
Airflow operates as the macro-level scheduler, executing checks against the PostgreSQL serving layer without interfering with the micro-batch processing of Spark. 

Three DAGs are implemented:
1. **`streamo_data_quality`**: Runs every 15 minutes. It asserts that data freshness (time since last process) is within 15 minutes and that the overall quality rate of the pipeline stays above 95%. It fails the task if either condition is breached.
2. **`streamo_daily_aggregation`**: Runs daily. It rolls up the 5-minute telemetry aggregates into a `daily_telemetry_summary` table in PostgreSQL. It leverages idempotent `ON CONFLICT DO UPDATE` queries.
3. **`streamo_maintenance`**: Runs daily. It cleans up the `processed_records` table by purging records older than 7 days, preventing PostgreSQL bloat.

## Grafana Observability
Grafana provides visual dashboards querying the PostgreSQL serving layer dynamically. Dashboards are configured as code using Grafana Provisioning (`/etc/grafana/provisioning`).

Four dashboards exist:
1. **Streamo Overview**: High-level KPIs including latest event time, total records, freshness, and quality rate.
2. **Pipeline Observability**: Real-time timeseries showing ingestion volume vs processing latency to measure lag.
3. **Data Quality**: Categorized views of null violations, range violations, and total valid vs invalid sizes.
4. **Telemetry Analytics**: Business-level dashboards charting Temperature and Humidity trends.

## Resilience
- Airflow is configured with exponential backoff and retries. If the Data Quality DAG fails due to stale data, it automatically retries 5 minutes later.
- Idempotent DAG design ensures `daily_aggregation` can be backfilled safely.
- Dashboard queries are backed by optimized SQL views (`streamo_pipeline_summary` and `streamo_quality_summary`) to prevent full table scans and memory exhaustion in the PostgreSQL instance.
