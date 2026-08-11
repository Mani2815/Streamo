from airflow import DAG
from airflow.providers.postgres.operators.postgres import SQLExecuteQueryOperator
from datetime import datetime, timedelta

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
    'streamo_maintenance',
    default_args=default_args,
    description='Perform safe housekeeping operations on PostgreSQL',
    schedule_interval='@daily',
    catchup=False,
    tags=['streamo', 'maintenance']
) as dag:

    # 1. Purge processed_records older than 7 days
    purge_old_records = SQLExecuteQueryOperator(
        task_id='purge_old_records',
        conn_id='postgres_streamo',
        sql="""
        DELETE FROM processed_records 
        WHERE event_timestamp < (NOW() - INTERVAL '7 days');
        """
    )

    purge_old_records
