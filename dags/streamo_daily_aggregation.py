from airflow import DAG
from airflow.providers.postgres.operators.postgres import SQLExecuteQueryOperator
from datetime import datetime, timedelta

default_args = {
    'owner': 'streamo',
    'depends_on_past': False,
    'start_date': datetime(2024, 1, 1),
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 2,
    'retry_delay': timedelta(minutes=5),
}

with DAG(
    'streamo_daily_aggregation',
    default_args=default_args,
    description='Perform scheduled verification/aggregation of processed data',
    schedule_interval='@daily',
    catchup=False,
    tags=['streamo', 'aggregation']
) as dag:

    # 1. Calculate and UPSERT daily summaries from telemetry_aggregates
    calculate_daily_summary = SQLExecuteQueryOperator(
        task_id='calculate_daily_summary',
        conn_id='postgres_streamo',
        sql="""
        INSERT INTO daily_telemetry_summary (summary_date, source, total_records, avg_temperature, avg_humidity, last_updated)
        SELECT 
            DATE(window_start) as summary_date,
            source,
            SUM(record_count) as total_records,
            AVG(avg_temperature) as avg_temperature,
            AVG(avg_humidity) as avg_humidity,
            CURRENT_TIMESTAMP as last_updated
        FROM telemetry_aggregates
        WHERE DATE(window_start) = CURRENT_DATE
        GROUP BY DATE(window_start), source
        ON CONFLICT (summary_date) 
        DO UPDATE SET 
            total_records = EXCLUDED.total_records,
            avg_temperature = EXCLUDED.avg_temperature,
            avg_humidity = EXCLUDED.avg_humidity,
            last_updated = EXCLUDED.last_updated;
        """
    )

    calculate_daily_summary
