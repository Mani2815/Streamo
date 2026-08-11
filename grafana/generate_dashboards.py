import json
import os

DASHBOARDS_DIR = "provisioning/dashboards"
os.makedirs(DASHBOARDS_DIR, exist_ok=True)

def create_dashboard(uid, title, panels):
    return {
        "uid": uid,
        "title": title,
        "tags": [ "streamo" ],
        "timezone": "browser",
        "schemaVersion": 39,
        "refresh": "30s",
        "panels": panels
    }

def create_stat_panel(title, id, gridPos, target_sql):
    return {
        "id": id,
        "title": title,
        "type": "stat",
        "gridPos": gridPos,
        "targets": [
            {
                "datasource": {"type": "postgres", "uid": "PostgreSQL"},
                "format": "table",
                "rawQuery": True,
                "rawSql": target_sql,
                "refId": "A"
            }
        ],
        "options": {
            "reduceOptions": {"values": False, "calcs": ["lastNotNull"], "fields": ""},
            "orientation": "auto",
            "textMode": "auto",
            "colorMode": "value",
            "graphMode": "area"
        }
    }

def create_timeseries_panel(title, id, gridPos, target_sql):
    return {
        "id": id,
        "title": title,
        "type": "timeseries",
        "gridPos": gridPos,
        "targets": [
            {
                "datasource": {"type": "postgres", "uid": "PostgreSQL"},
                "format": "time_series",
                "rawQuery": True,
                "rawSql": target_sql,
                "refId": "A"
            }
        ]
    }

# 1. Streamo Overview
overview = create_dashboard("overview", "Streamo Overview", [
    create_stat_panel("Latest Event Time", 1, {"h": 4, "w": 6, "x": 0, "y": 0}, 
                      "SELECT latest_event_time FROM streamo_pipeline_summary WHERE source='mock'"),
    create_stat_panel("Data Freshness (seconds)", 2, {"h": 4, "w": 6, "x": 6, "y": 0}, 
                      "SELECT freshness_seconds FROM streamo_pipeline_summary WHERE source='mock'"),
    create_stat_panel("Total Records Processed", 3, {"h": 4, "w": 6, "x": 12, "y": 0}, 
                      "SELECT total_records FROM streamo_pipeline_summary WHERE source='mock'"),
    create_stat_panel("Quality Rate %", 4, {"h": 4, "w": 6, "x": 18, "y": 0}, 
                      "SELECT quality_rate FROM streamo_quality_summary WHERE source='mock'")
])

# 2. Pipeline Observability
observability = create_dashboard("observability", "Pipeline Observability", [
    create_timeseries_panel("Ingestion vs Processing Time", 1, {"h": 8, "w": 12, "x": 0, "y": 0}, 
                            "SELECT event_timestamp AS time, 1 AS ingested FROM processed_records ORDER BY time DESC LIMIT 100"),
    create_timeseries_panel("Processing Latency", 2, {"h": 8, "w": 12, "x": 12, "y": 0}, 
                            "SELECT event_timestamp AS time, EXTRACT(EPOCH FROM (processed_at - event_timestamp)) as latency FROM processed_records ORDER BY time DESC LIMIT 100")
])

# 3. Data Quality
quality = create_dashboard("quality", "Data Quality", [
    create_stat_panel("Total Records", 1, {"h": 4, "w": 4, "x": 0, "y": 0}, 
                      "SELECT total_records FROM streamo_quality_summary"),
    create_stat_panel("Valid Records", 2, {"h": 4, "w": 4, "x": 4, "y": 0}, 
                      "SELECT valid_records FROM streamo_quality_summary"),
    create_stat_panel("Invalid Records", 3, {"h": 4, "w": 4, "x": 8, "y": 0}, 
                      "SELECT invalid_records FROM streamo_quality_summary"),
    create_stat_panel("Range Violations", 4, {"h": 4, "w": 4, "x": 12, "y": 0}, 
                      "SELECT range_violations FROM streamo_quality_summary"),
    create_stat_panel("Null Violations", 5, {"h": 4, "w": 4, "x": 16, "y": 0}, 
                      "SELECT null_violations FROM streamo_quality_summary")
])

# 4. Telemetry Analytics
analytics = create_dashboard("analytics", "Telemetry Analytics", [
    create_timeseries_panel("Temperature Trend", 1, {"h": 8, "w": 12, "x": 0, "y": 0}, 
                            "SELECT window_start AS time, avg_temperature AS value FROM telemetry_aggregates ORDER BY time DESC LIMIT 100"),
    create_timeseries_panel("Humidity Trend", 2, {"h": 8, "w": 12, "x": 12, "y": 0}, 
                            "SELECT window_start AS time, avg_humidity AS value FROM telemetry_aggregates ORDER BY time DESC LIMIT 100")
])

with open(f"{DASHBOARDS_DIR}/overview.json", "w") as f:
    json.dump(overview, f, indent=2)

with open(f"{DASHBOARDS_DIR}/observability.json", "w") as f:
    json.dump(observability, f, indent=2)

with open(f"{DASHBOARDS_DIR}/quality.json", "w") as f:
    json.dump(quality, f, indent=2)

with open(f"{DASHBOARDS_DIR}/analytics.json", "w") as f:
    json.dump(analytics, f, indent=2)

print("Dashboards generated successfully.")
