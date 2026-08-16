from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
import httpx
from typing import List, Dict, Any
import os
import time

from ... import models, schemas
from ...database import get_db

from confluent_kafka.admin import AdminClient, NewTopic

router = APIRouter()
KAFKA_BOOTSTRAP_SERVERS = os.environ.get("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092")

def infer_schema(data: Any) -> Dict[str, str]:
    schema = {}
    if isinstance(data, list) and len(data) > 0:
        data = data[0]
    
    if not isinstance(data, dict):
        return schema
        
    for k, v in data.items():
        if isinstance(v, bool):
            schema[k] = "boolean"
        elif isinstance(v, int):
            schema[k] = "numeric"
        elif isinstance(v, float):
            schema[k] = "numeric"
        elif isinstance(v, str):
            # very basic datetime check
            if "T" in v and "Z" in v or "-" in v and ":" in v:
                schema[k] = "datetime"
            else:
                schema[k] = "string"
        else:
            schema[k] = "string"
    return schema

@router.post("/validate", response_model=schemas.SourceValidateResponse)
async def validate_source(source: schemas.SourceValidateRequest):
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(str(source.url), timeout=10.0)
            
        content_type = response.headers.get("content-type", "")
        is_json = "application/json" in content_type
        
        detected_fields = {}
        if response.status_code == 200 and is_json:
            try:
                data = response.json()
                detected_fields = infer_schema(data)
            except:
                is_json = False
        
        return schemas.SourceValidateResponse(
            valid=response.status_code == 200 and is_json,
            status_code=response.status_code,
            content_type=content_type,
            detected_fields=detected_fields
        )
    except Exception as e:
        return schemas.SourceValidateResponse(
            valid=False,
            error=str(e)
        )

@router.post("/", response_model=schemas.Source)
def create_source(source: schemas.SourceCreate, db: Session = Depends(get_db)):
    db_source = db.query(models.Source).filter(models.Source.name == source.name).first()
    if db_source:
        raise HTTPException(status_code=400, detail="Source already registered")
    
    # We should validate to save the schema
    new_source = models.Source(
        name=source.name,
        url=str(source.url),
        poll_interval=source.poll_interval,
        status="active"
    )
    db.add(new_source)
    db.commit()
    db.refresh(new_source)
    
    ensure_topic_exists(new_source.name)
    return new_source

@router.get("/", response_model=List[schemas.Source])
def get_sources(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    sources = db.query(models.Source).offset(skip).limit(limit).all()
    return sources

@router.get("/{id}", response_model=schemas.Source)
def get_source(id: int, db: Session = Depends(get_db)):
    source = db.query(models.Source).filter(models.Source.id == id).first()
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")
    return source

def ensure_topic_exists(source_name: str):
    topic_name = f"streamo.raw.{source_name}"
    try:
        admin_client = AdminClient({'bootstrap.servers': KAFKA_BOOTSTRAP_SERVERS})
        new_topic = NewTopic(topic_name, num_partitions=1, replication_factor=1)
        fs = admin_client.create_topics([new_topic])
        for topic, f in fs.items():
            try:
                f.result()  # The result itself is None
            except Exception as e:
                if "TOPIC_ALREADY_EXISTS" not in str(e):
                    print(f"Failed to create topic {topic}: {e}")
    except Exception as e:
        print(f"Error communicating with Kafka Admin: {e}")

@router.post("/{id}/start")
def start_source(id: int, db: Session = Depends(get_db)):
    source = get_source(id, db)
    source.status = "active"
    db.commit()
    ensure_topic_exists(source.name)
    return {"status": "active"}

@router.post("/{id}/pause")
def pause_source(id: int, db: Session = Depends(get_db)):
    source = get_source(id, db)
    source.status = "paused"
    db.commit()
    return {"status": "paused"}

@router.post("/{id}/stop")
def stop_source(id: int, db: Session = Depends(get_db)):
    source = get_source(id, db)
    source.status = "stopped"
    db.commit()
    return {"status": "stopped"}

def calculate_iqr_anomalies(values: List[float]) -> int:
    if not values or len(values) < 4:
        return 0
    s_vals = sorted(values)
    n = len(s_vals)
    q1 = s_vals[n // 4]
    q3 = s_vals[(3 * n) // 4]
    iqr = q3 - q1
    lower_bound = q1 - 1.5 * iqr
    upper_bound = q3 + 1.5 * iqr
    
    anomalies = 0
    for v in values:
        if v < lower_bound or v > upper_bound:
            anomalies += 1
    return anomalies

def calculate_trend(values: List[float]) -> dict:
    if len(values) < 4:
        return {"direction": "Stable", "percentage": 0.0}
    half = len(values) // 2
    first_half = values[:half]
    second_half = values[half:]
    
    avg_first = sum(first_half) / len(first_half)
    avg_second = sum(second_half) / len(second_half)
    
    if avg_first == 0:
        return {"direction": "Stable", "percentage": 0.0}
        
    pct_change = ((avg_second - avg_first) / avg_first) * 100
    
    if pct_change > 1.0:
        direction = "Increasing"
    elif pct_change < -1.0:
        direction = "Decreasing"
    else:
        direction = "Stable"
        
    return {"direction": direction, "percentage": round(pct_change, 1)}

@router.get("/{id}/analytics")
def get_source_analytics(id: int, db: Session = Depends(get_db)):
    source = get_source(id, db)
    # Get last 500 records chronologically
    sql = text("""
        SELECT * FROM (
            SELECT event_timestamp, processed_at, payload
            FROM processed_records
            WHERE source = :source
            ORDER BY processed_at DESC
            LIMIT 500
        ) sub
        ORDER BY processed_at ASC
    """)
    result = db.execute(sql, {"source": source.name}).fetchall()
    
    data = []
    for row in result:
        data.append({
            "timestamp": row[0].isoformat() if row[0] else None,
            "processed_at": row[1].isoformat() if row[1] else None,
            "payload": row[2]
        })
        
    # Get KPIs
    count_sql = text("SELECT COUNT(*) FROM processed_records WHERE source = :source")
    total_records = db.execute(count_sql, {"source": source.name}).scalar()
    
    q_sql = text("""
        SELECT quality_rate
        FROM data_quality_metrics
        WHERE source = :source
        ORDER BY run_timestamp DESC
        LIMIT 1
    """)
    q_res = db.execute(q_sql, {"source": source.name}).first()
    quality_rate = q_res[0] if q_res else 100.0
    
    ingestion_rate = 0.0
    if len(result) > 1 and result[-1][1] and result[0][1]:
        delta_seconds = (result[-1][1] - result[0][1]).total_seconds()
        if delta_seconds > 0:
            ingestion_rate = round(len(result) / delta_seconds, 2)
            
    freshness_seconds = None
    if result and result[-1][1]:
        import datetime
        now = datetime.datetime.now(datetime.timezone.utc)
        freshness_seconds = int((now - result[-1][1]).total_seconds())
            
    # Classify schema
    schema = {}
    if data and data[-1]["payload"]:
        for k, v in data[-1]["payload"].items():
            if "id" in k.lower():
                schema[k] = "identifier"
            elif isinstance(v, (int, float)) and not isinstance(v, bool):
                schema[k] = "metric"
            else:
                schema[k] = "dimension"
                
    metric_values = {k: [] for k, v in schema.items() if v == "metric"}
    for d in data:
        if not d["payload"]: continue
        for k in metric_values.keys():
            if k in d["payload"] and isinstance(d["payload"][k], (int, float)):
                metric_values[k].append(float(d["payload"][k]))
                
    metrics_summary = {}
    insights = []
    
    for k, vals in metric_values.items():
        if not vals: continue
        avg_val = round(sum(vals) / len(vals), 2)
        min_val = round(min(vals), 2)
        max_val = round(max(vals), 2)
        
        trend = calculate_trend(vals)
        anomalies = calculate_iqr_anomalies(vals)
        
        metrics_summary[k] = {
            "avg": avg_val,
            "min": min_val,
            "max": max_val,
            "trend": trend,
            "anomalies": anomalies
        }
        
        # Generate Insights
        if trend["direction"] == "Increasing":
            insights.append(f"{k.capitalize()} increased {trend['percentage']}% compared with the previous period.")
        elif trend["direction"] == "Decreasing":
            insights.append(f"{k.capitalize()} decreased {abs(trend['percentage'])}% compared with the previous period.")
        else:
            insights.append(f"{k.capitalize()} remained relatively stable.")
            
        if anomalies > 0:
            insights.append(f"⚠ {anomalies} potential anomalies detected in {k}.")
            
    if not insights:
        insights.append("Not enough data to determine a trend.")
        
    return {
        "kpis": {
            "total_records": total_records,
            "quality_rate": quality_rate,
            "freshness_seconds": freshness_seconds,
            "ingestion_rate": ingestion_rate
        },
        "schema": schema,
        "metrics_summary": metrics_summary,
        "insights": insights,
        "data": data
    }

@router.get("/{id}/quality")
def get_source_quality(id: int, db: Session = Depends(get_db)):
    source = get_source(id, db)
    
    count_sql = text("SELECT COUNT(*) FROM processed_records WHERE source = :source")
    actual_valid = db.execute(count_sql, {"source": source.name}).scalar()
    
    sql = text("""
        SELECT invalid_records, duplicate_records, null_violations, range_violations
        FROM data_quality_metrics
        WHERE source = :source
        ORDER BY run_timestamp DESC
        LIMIT 1
    """)
    result = db.execute(sql, {"source": source.name}).first()
    
    if not result:
        return {
            "total_records": actual_valid,
            "valid_records": actual_valid,
            "invalid_records": 0,
            "duplicate_records": 0,
            "null_violations": 0,
            "range_violations": 0,
            "format_violations": 0,
            "quality_rate": 100.0 if actual_valid > 0 else None
        }
    
    invalid_records = result[0]
    duplicate_records = result[1]
    null_violations = result[2]
    range_violations = result[3]
    
    # Approximate format violations
    format_violations = invalid_records - (null_violations + range_violations)
    if format_violations < 0:
        format_violations = 0
        
    total = actual_valid + invalid_records
    quality_rate = (actual_valid / total * 100.0) if total > 0 else None
    
    return {
        "total_records": total,
        "valid_records": actual_valid,
        "invalid_records": invalid_records,
        "duplicate_records": duplicate_records,
        "null_violations": null_violations,
        "range_violations": range_violations,
        "format_violations": format_violations,
        "quality_rate": round(quality_rate, 2) if quality_rate is not None else None
    }

@router.get("/{id}/records")
def get_source_records(id: int, db: Session = Depends(get_db)):
    source = get_source(id, db)
    sql = text("""
        SELECT event_id, event_timestamp, payload, temperature, humidity
        FROM processed_records
        WHERE source = :source
        ORDER BY event_timestamp DESC
        LIMIT 20
    """)
    result = db.execute(sql, {"source": source.name}).fetchall()
    records = []
    for row in result:
        records.append({
            "event_id": row[0],
            "timestamp": row[1].isoformat() if row[1] else None,
            "payload": row[2],
            "temperature": row[3],
            "humidity": row[4]
        })
    return {"records": records}
