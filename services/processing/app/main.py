import os
import sys
import subprocess

# Install psycopg2 dynamically on the Spark Driver for PostgreSQL connections
subprocess.check_call([sys.executable, "-m", "pip", "install", "--target=/tmp/pip_pkgs", "psycopg2-binary"])
sys.path.insert(0, '/tmp/pip_pkgs')

import psycopg2
from psycopg2.extras import execute_values
from pyspark.sql import SparkSession
from pyspark.sql.functions import (
    col, from_json, to_timestamp, year, month, dayofmonth, hour,
    expr, window, avg, count, current_timestamp, sum
)
from pyspark.sql.types import (
    StructType, StructField, StringType, IntegerType, DoubleType
)

# Configuration from environment
KAFKA_BOOTSTRAP_SERVERS = os.environ.get("KAFKA_BOOTSTRAP_SERVERS", "streamo-kafka:9092")
MINIO_ENDPOINT = os.environ.get("MINIO_ENDPOINT", "http://minio:9000")
MINIO_ACCESS_KEY = os.environ.get("MINIO_ACCESS_KEY", "streamo")
MINIO_SECRET_KEY = os.environ.get("MINIO_SECRET_KEY", "streamo_secret")

PG_HOST = os.environ.get("POSTGRES_HOST", "postgres")
PG_PORT = os.environ.get("POSTGRES_PORT", "5432")
PG_DB = os.environ.get("POSTGRES_DB", "streamo")
PG_USER = os.environ.get("POSTGRES_USER", "streamo_user")
PG_PASS = os.environ.get("POSTGRES_PASSWORD", "streamo_password")

def get_pg_conn():
    return psycopg2.connect(host=PG_HOST, port=PG_PORT, dbname=PG_DB, user=PG_USER, password=PG_PASS)

def create_spark_session():
    return (
        SparkSession.builder
        .appName("StreamoProcessing")
        .config("spark.hadoop.fs.s3a.endpoint", MINIO_ENDPOINT)
        .config("spark.hadoop.fs.s3a.access.key", MINIO_ACCESS_KEY)
        .config("spark.hadoop.fs.s3a.secret.key", MINIO_SECRET_KEY)
        .config("spark.hadoop.fs.s3a.path.style.access", "true")
        .config("spark.hadoop.fs.s3a.connection.ssl.enabled", "false")
        .config("spark.hadoop.fs.s3a.impl", "org.apache.hadoop.fs.s3a.S3AFileSystem")
        .getOrCreate()
    )

def get_event_schema():
    event_schema = StructType([
        StructField("event_id", StringType(), True),
        StructField("source", StringType(), True),
        StructField("ingested_at", StringType(), True),
        StructField("payload", StringType(), True), # Store as raw JSON string for dynamic schema
    ])
    return event_schema

def upsert_postgres_records(batch_df, epoch_id):
    rows = batch_df.collect()
    print(f"DEBUG: Upserting {len(rows)} records for epoch {epoch_id}", flush=True)
    if not rows: return
    conn = get_pg_conn()
    cur = conn.cursor()
    query = """
    INSERT INTO processed_records (
        event_id, source, ingested_at, record_id, event_timestamp, 
        temperature, humidity, temperature_f, payload, processed_at
    ) VALUES %s
    ON CONFLICT (event_id) DO UPDATE SET
        temperature = EXCLUDED.temperature,
        humidity = EXCLUDED.humidity,
        payload = EXCLUDED.payload,
        processed_at = EXCLUDED.processed_at
    """
    seen = set()
    values = []
    for r in rows:
        if r.event_id not in seen:
            seen.add(r.event_id)
            values.append((
                r.event_id, r.source, r.ingested_at, r.id, r.timestamp,
                r.temperature, r.humidity, r.temperature_f, r.payload, r.processed_at
            ))
    # postgres jsonb accepts valid json string implicitly
    execute_values(cur, query, values, template="(%s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s)")
    conn.commit()
    cur.close()
    conn.close()

def upsert_postgres_aggregates(batch_df, batch_id):
    rows = batch_df.collect()
    if not rows: return
    conn = get_pg_conn()
    cur = conn.cursor()
    query = """
    INSERT INTO telemetry_aggregates (
        source, window_start, window_end, avg_temperature, avg_humidity, record_count
    ) VALUES %s
    ON CONFLICT (source, window_start) DO UPDATE SET
        avg_temperature = EXCLUDED.avg_temperature,
        avg_humidity = EXCLUDED.avg_humidity,
        record_count = EXCLUDED.record_count
    """
    values = [(
        r.source, r.window.start, r.window.end, r.avg_temperature, r.avg_humidity, r.record_count
    ) for r in rows]
    execute_values(cur, query, values)
    conn.commit()
    cur.close()
    conn.close()

def upsert_postgres_metrics(batch_df, batch_id):
    rows = batch_df.collect()
    if not rows: return
    conn = get_pg_conn()
    cur = conn.cursor()
    query = """
    INSERT INTO data_quality_metrics (
        source, run_timestamp, total_records, valid_records, invalid_records, null_violations, range_violations, quality_rate
    ) VALUES %s
    ON CONFLICT (source, run_timestamp) DO UPDATE SET
        total_records = EXCLUDED.total_records,
        valid_records = EXCLUDED.valid_records,
        invalid_records = EXCLUDED.invalid_records,
        null_violations = EXCLUDED.null_violations,
        range_violations = EXCLUDED.range_violations,
        quality_rate = EXCLUDED.quality_rate
    """
    values = [(
        r.source, r.window.start, r.total_records, r.valid_records, r.invalid_records, 
        r.null_violations, r.range_violations, 
        (r.valid_records / r.total_records * 100.0) if r.total_records > 0 else 100.0
    ) for r in rows]
    execute_values(cur, query, values)
    conn.commit()
    cur.close()
    conn.close()

def main():
    spark = create_spark_session()
    spark.sparkContext.setLogLevel("WARN")
    
    # 1. Read Raw Kafka Stream
    raw_kafka_df = (
        spark.readStream
        .format("kafka")
        .option("kafka.bootstrap.servers", KAFKA_BOOTSTRAP_SERVERS)
        .option("subscribePattern", "streamo\\.raw\\..*")
        .option("startingOffsets", "earliest")
        .option("failOnDataLoss", "false")
        .load()
    )
    
    raw_json_df = raw_kafka_df.selectExpr("CAST(value AS STRING) as raw_value")
    
    # 2. Parse event envelope
    schema = get_event_schema()
    parsed_df = raw_json_df.withColumn("parsed", from_json(col("raw_value"), schema))
    
    # Extract timestamps for partitioning
    ts_df = parsed_df.withColumn("ingested_ts", to_timestamp(col("parsed.ingested_at")))
    
    # 3. Raw Persistence (Query 1)
    raw_persistence_df = ts_df \
     .withColumn("year", year("ingested_ts")) \
     .withColumn("month", month("ingested_ts")) \
     .withColumn("day", dayofmonth("ingested_ts")) \
     .withColumn("hour", hour("ingested_ts")) \
     .select(col("parsed.source").alias("source"), "raw_value", "year", "month", "day", "hour")
    
    raw_persistence_df.writeStream \
        .format("parquet") \
        .option("path", "s3a://streamo-raw/") \
        .option("checkpointLocation", "s3a://streamo-processed/checkpoints/v11/raw/") \
        .partitionBy("source", "year", "month", "day", "hour") \
        .outputMode("append") \
        .start()
        
    # 4. Data Quality Rules (Dynamic)
    dq_df = ts_df.withColumn("is_null_violation", expr(
        "parsed.event_id IS NULL OR parsed.source IS NULL OR parsed.ingested_at IS NULL"
    )).withColumn("is_format_violation", expr(
        "NOT (parsed.event_id RLIKE '^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$')"
    )).withColumn("is_json_valid", expr(
        "get_json_object(parsed.payload, '$') IS NOT NULL"
    )).withColumn("temp_val", expr(
        "get_json_object(parsed.payload, '$.temperature')"
    )).withColumn("hum_val", expr(
        "get_json_object(parsed.payload, '$.humidity')"
    )).withColumn("is_range_violation", expr(
        "(temp_val IS NOT NULL AND (CAST(temp_val AS DOUBLE) < -50 OR CAST(temp_val AS DOUBLE) > 100)) OR "
        "(hum_val IS NOT NULL AND (CAST(hum_val AS DOUBLE) < 0 OR CAST(hum_val AS DOUBLE) > 100))"
    )).withColumn("is_valid", expr("NOT is_null_violation AND is_json_valid AND NOT is_range_violation AND NOT is_format_violation"))
    
    # 5. Quarantine Invalid Records (Query 2)
    invalid_df = dq_df.filter(col("is_valid") == False).select(col("parsed.source").alias("source"), "raw_value")
    invalid_df.writeStream \
        .format("parquet") \
        .option("path", "s3a://streamo-quarantine/") \
        .option("checkpointLocation", "s3a://streamo-processed/checkpoints/v11/quarantine/") \
        .partitionBy("source") \
        .outputMode("append") \
        .start()
        
    # 6. Process Valid Records (Deduplication)
    valid_df = dq_df.filter(col("is_valid") == True).select(
        col("parsed.event_id").alias("event_id"),
        col("parsed.source").alias("source"),
        col("ingested_ts").alias("ingested_at"),
        col("parsed.payload").alias("payload"),
        expr("get_json_object(parsed.payload, '$.id')").cast("bigint").alias("id"),
        expr("COALESCE(to_timestamp(get_json_object(parsed.payload, '$.timestamp')), to_timestamp(get_json_object(parsed.payload, '$.time')), ingested_ts)").alias("timestamp"),
        expr("get_json_object(parsed.payload, '$.temperature')").cast("double").alias("temperature"),
        expr("get_json_object(parsed.payload, '$.humidity')").cast("double").alias("humidity")
    )
    
    enriched_df = valid_df \
        .withColumn("temperature_f", (col("temperature") * 9/5) + 32) \
        .withColumn("processed_at", current_timestamp()) \
        .withColumn("year", year("timestamp")) \
        .withColumn("month", month("timestamp")) \
        .withColumn("day", dayofmonth("timestamp")) \
        .withColumn("hour", hour("timestamp")) \
        .withWatermark("timestamp", "10 minutes")
        
    dedup_df = enriched_df.dropDuplicates(["event_id"])
    
    # 7. Write Processed Records to MinIO    # Output 1: Upsert to PostgreSQL
    enriched_df.writeStream \
        .foreachBatch(upsert_postgres_records) \
        .outputMode("update") \
        .option("checkpointLocation", "s3a://streamo-processed/checkpoints/v11/postgres/") \
        .start()
        
    dedup_df.writeStream \
        .format("parquet") \
        .option("path", "s3a://streamo-processed/events/") \
        .option("checkpointLocation", "s3a://streamo-processed/checkpoints/v11/parquet/") \
        .partitionBy("year", "month", "day", "hour") \
        .outputMode("append") \
        .start()
        
    # 8. Aggregates to MinIO & Postgres (Query 4)
    # Aggregation requires grouping by source
    agg_df = dedup_df.groupBy(
        window(col("timestamp"), "5 minutes"), col("source")
    ).agg(
        avg("temperature").alias("avg_temperature"),
        avg("humidity").alias("avg_humidity"),
        count(expr("COALESCE(id, 1)")).alias("record_count")
    )
    
    agg_df.writeStream \
        .foreachBatch(upsert_postgres_aggregates) \
        .outputMode("update") \
        .option("checkpointLocation", "s3a://streamo-processed/checkpoints/v11/aggregates/") \
        .start()

    # 9. Data Quality Metrics (Query 5)
    dq_summary_df = dq_df.withWatermark("ingested_ts", "5 minutes").groupBy(
        window(col("ingested_ts"), "5 minutes"), col("parsed.source").alias("source")
    ).agg(
        count(col("raw_value")).alias("total_records"),
        sum(expr("CASE WHEN is_valid THEN 1 ELSE 0 END")).alias("valid_records"),
        sum(expr("CASE WHEN NOT is_valid THEN 1 ELSE 0 END")).alias("invalid_records"),
        sum(expr("CASE WHEN is_null_violation THEN 1 ELSE 0 END")).alias("null_violations"),
        sum(expr("CASE WHEN is_range_violation THEN 1 ELSE 0 END")).alias("range_violations")
    )

    dq_summary_df.writeStream \
        .foreachBatch(upsert_postgres_metrics) \
        .option("checkpointLocation", "s3a://streamo-processed/checkpoints/v9/metrics_pg/") \
        .outputMode("update") \
        .start()
    
    spark.streams.awaitAnyTermination()

if __name__ == "__main__":
    main()
