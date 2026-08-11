from pyspark.sql import SparkSession
from pyspark.sql.functions import col, from_json
from pyspark.sql.types import StructType, StructField, StringType

spark = SparkSession.builder.master("local[*]").getOrCreate()

data = ['{"event_id": "123", "source": "Meteo", "ingested_at": "2026", "payload": {"latitude": 12.97}}']
df = spark.createDataFrame([(d,) for d in data], ["value"])

event_schema = StructType([
    StructField("event_id", StringType(), True),
    StructField("source", StringType(), True),
    StructField("ingested_at", StringType(), True),
    StructField("payload", StringType(), True),
])

parsed_df = df.select(
    from_json(col("value"), event_schema).alias("data")
).select("data.*")

parsed_df.show(truncate=False)
