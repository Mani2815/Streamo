-- Connect to streamo database
\c streamo;

-- 1. sources table
CREATE TABLE IF NOT EXISTS sources (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL UNIQUE,
    url VARCHAR(1024) NOT NULL,
    poll_interval INTEGER NOT NULL,
    schema JSONB,
    status VARCHAR(50) DEFAULT 'active',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 2. processed_records table
CREATE TABLE IF NOT EXISTS processed_records (
    event_id UUID PRIMARY KEY,
    source VARCHAR(255) NOT NULL,
    ingested_at TIMESTAMP WITH TIME ZONE NOT NULL,
    record_id BIGINT,
    event_timestamp TIMESTAMP WITH TIME ZONE,
    temperature DOUBLE PRECISION,
    humidity DOUBLE PRECISION,
    temperature_f DOUBLE PRECISION,
    payload JSONB,
    processed_at TIMESTAMP WITH TIME ZONE NOT NULL,
    served_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Constraints
ALTER TABLE processed_records 
    ADD CONSTRAINT check_temperature_range CHECK (temperature BETWEEN -50 AND 100),
    ADD CONSTRAINT check_humidity_range CHECK (humidity BETWEEN 0 AND 100);

-- Indexes for querying
CREATE INDEX idx_processed_records_source ON processed_records(source);
CREATE INDEX idx_processed_records_event_timestamp ON processed_records(event_timestamp);

-- 3. telemetry_aggregates table
CREATE TABLE IF NOT EXISTS telemetry_aggregates (
    source VARCHAR(255) NOT NULL,
    window_start TIMESTAMP WITH TIME ZONE NOT NULL,
    window_end TIMESTAMP WITH TIME ZONE NOT NULL,
    avg_temperature DOUBLE PRECISION,
    avg_humidity DOUBLE PRECISION,
    record_count BIGINT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT unique_source_window UNIQUE (source, window_start)
);

-- 4. data_quality_metrics table
CREATE TABLE IF NOT EXISTS data_quality_metrics (
    id SERIAL PRIMARY KEY,
    source VARCHAR(255) NOT NULL,
    run_timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    total_records BIGINT NOT NULL DEFAULT 0,
    valid_records BIGINT NOT NULL DEFAULT 0,
    invalid_records BIGINT NOT NULL DEFAULT 0,
    duplicate_records BIGINT NOT NULL DEFAULT 0,
    null_violations BIGINT NOT NULL DEFAULT 0,
    range_violations BIGINT NOT NULL DEFAULT 0,
    freshness_violations BIGINT NOT NULL DEFAULT 0,
    quality_rate DOUBLE PRECISION NOT NULL DEFAULT 100.0,
    CONSTRAINT unique_source_run UNIQUE (source, run_timestamp)
);
