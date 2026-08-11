from airflow import DAG
from airflow.providers.postgres.operators.postgres import SQLExecuteQueryOperator
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta
import logging

default_args = {
    'owner': 'streamo',
    'depends_on_past': False,
    'start_date': datetime(2024, 1, 1),
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

with DAG(
    'streamo_data_quality',
    default_args=default_args,
    description='Periodically verify data quality in PostgreSQL',
    schedule_interval='*/15 * * * *',
    catchup=False,
    tags=['streamo', 'quality']
) as dag:

    # 1. Check data freshness (fail if no new data in last 15 min)
    check_freshness = SQLExecuteQueryOperator(
        task_id='check_freshness',
        conn_id='postgres_streamo',
        sql="""
        DO $$
        DECLARE
            latest_time TIMESTAMP WITH TIME ZONE;
        BEGIN
            SELECT MAX(processed_at) INTO latest_time FROM processed_records;
            IF latest_time < (NOW() - INTERVAL '15 minutes') THEN
                RAISE EXCEPTION 'Data is not fresh. Latest processed time: %', latest_time;
            END IF;
        END $$;
        """
    )

    # 2. Check quality rate (fail if below 95%)
    check_quality_rate = SQLExecuteQueryOperator(
        task_id='check_quality_rate',
        conn_id='postgres_streamo',
        sql="""
        DO $$
        DECLARE
            q_rate FLOAT;
        BEGIN
            SELECT quality_rate INTO q_rate FROM streamo_quality_summary WHERE source = 'mock';
            IF q_rate < 95.0 THEN
                RAISE EXCEPTION 'Quality rate is below 95%%! Current rate: %', q_rate;
            END IF;
        END $$;
        """
    )

    # 3. Dummy success persistence task
    def log_success():
        logging.info("Data Quality checks passed successfully.")

    persist_success = PythonOperator(
        task_id='persist_success',
        python_callable=log_success
    )

    check_freshness >> check_quality_rate >> persist_success
