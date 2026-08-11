CREATE TABLE IF NOT EXISTS daily_telemetry_summary (
    summary_date DATE PRIMARY KEY,
    source VARCHAR(255) NOT NULL,
    total_records BIGINT NOT NULL DEFAULT 0,
    avg_temperature DECIMAL(5, 2),
    avg_humidity DECIMAL(5, 2),
    last_updated TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE OR REPLACE VIEW streamo_pipeline_summary AS
SELECT 
    source,
    MAX(event_timestamp) as latest_event_time,
    MAX(processed_at) as latest_processing_time,
    COUNT(*) as total_records,
    EXTRACT(EPOCH FROM (NOW() - MAX(processed_at))) as freshness_seconds
FROM processed_records
GROUP BY source;

CREATE OR REPLACE VIEW streamo_quality_summary AS
SELECT 
    source,
    SUM(total_records) as total_records,
    SUM(valid_records) as valid_records,
    SUM(invalid_records) as invalid_records,
    SUM(null_violations) as null_violations,
    SUM(range_violations) as range_violations,
    CASE WHEN SUM(total_records) > 0 THEN (SUM(valid_records)::FLOAT / SUM(total_records)::FLOAT) * 100.0 ELSE 100.0 END as quality_rate
FROM data_quality_metrics
GROUP BY source;
