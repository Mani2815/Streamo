# Streamo Operations Guide

## Airflow Operations

### Accessing Airflow
Airflow Web UI: `http://localhost:8082`
Default credentials: `admin` / `admin`

### Key DAGs
1. **`streamo_data_quality`**: Evaluates data freshness and validates the Data Quality engine. If it fails, check if Kafka/Spark are running.
2. **`streamo_daily_aggregation`**: Aggregates records. It uses UPSERTS. You can safely clear the task in the Airflow UI to trigger a backfill.
3. **`streamo_maintenance`**: Data retention purge. Can be adjusted by editing `dags/streamo_maintenance.py`.

### Troubleshooting Airflow
To clear a stuck task from the command line:
```bash
docker exec -it streamo-airflow-scheduler-1 airflow tasks clear -y streamo_data_quality -t check_freshness
```

## Grafana Operations

### Accessing Grafana
Grafana Web UI: `http://localhost:3000`
Default credentials: `admin` / `admin`

### Dashboards Configuration
Dashboards are defined via code in `/grafana/provisioning/dashboards/`. Any changes to the JSON files must be accompanied by a restart of the Grafana container to apply via the provisioning system:
```bash
docker compose restart grafana
```

## MinIO Storage Operations
MinIO UI: `http://localhost:9001`
Buckets: `streamo-raw`, `streamo-processed`, `streamo-quarantine`

If Spark crashes with a Delta Lake checkpoint error (`FileNotFoundException`), it means the MinIO container likely restarted and lost ephemeral writes due to volume sync latency. In this case, simply increment the checkpoint path version in `main.py` (e.g. `v4/` -> `v5/`) and restart Spark.
