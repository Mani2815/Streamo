import os
from pyspark.sql import SparkSession

def main():
    MINIO_ENDPOINT = os.environ.get("MINIO_ENDPOINT", "http://minio:9000")
    MINIO_ACCESS_KEY = os.environ.get("MINIO_ACCESS_KEY", "streamo")
    MINIO_SECRET_KEY = os.environ.get("MINIO_SECRET_KEY", "streamo_secret")

    spark = (
        SparkSession.builder
        .appName("StreamoVerify")
        .config("spark.hadoop.fs.s3a.endpoint", MINIO_ENDPOINT)
        .config("spark.hadoop.fs.s3a.access.key", MINIO_ACCESS_KEY)
        .config("spark.hadoop.fs.s3a.secret.key", MINIO_SECRET_KEY)
        .config("spark.hadoop.fs.s3a.path.style.access", "true")
        .config("spark.hadoop.fs.s3a.connection.ssl.enabled", "false")
        .config("spark.hadoop.fs.s3a.impl", "org.apache.hadoop.fs.s3a.S3AFileSystem")
        .getOrCreate()
    )
    spark.sparkContext.setLogLevel("ERROR")

    print("=== RAW PERSISTENCE ===")
    raw_df = spark.read.parquet("s3a://streamo-raw/source=mock/")
    raw_df.printSchema()
    raw_df.show(5, truncate=False)

    print("=== PROCESSED RECORDS ===")
    records_df = spark.read.parquet("s3a://streamo-processed/records/source=mock/")
    records_df.printSchema()
    records_df.show(5, truncate=False)

    print("=== PROCESSED AGGREGATES ===")
    try:
        agg_df = spark.read.parquet("s3a://streamo-processed/aggregates/source=mock/")
        agg_df.printSchema()
        agg_df.show(5, truncate=False)
    except Exception as e:
        print("Aggregates not yet materialized or empty:", e)

if __name__ == "__main__":
    main()
