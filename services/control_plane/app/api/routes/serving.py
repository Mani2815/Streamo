from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List, Dict, Any
from ...database import get_db

router = APIRouter()

@router.get("/pipeline/status")
def get_pipeline_status(db: Session = Depends(get_db)):
    try:
        # Check if DB is alive
        result = db.execute(text("SELECT 1")).scalar()
        return {"status": "operational", "database": "connected" if result == 1 else "unknown"}
    except Exception as e:
        return {"status": "degraded", "database": "disconnected", "error": str(e)}

@router.get("/quality/summary")
def get_quality_summary(db: Session = Depends(get_db)):
    query = text("""
        SELECT 
            source,
            SUM(total_records) as total_records,
            SUM(valid_records) as valid_records,
            SUM(invalid_records) as invalid_records,
            SUM(null_violations) as null_violations,
            SUM(range_violations) as range_violations
        FROM data_quality_metrics
        GROUP BY source
    """)
    results = db.execute(query).fetchall()
    
    summary = []
    for r in results:
        quality_rate = (float(r.valid_records) / float(r.total_records) * 100.0) if r.total_records > 0 else 100.0
        summary.append({
            "source": r.source,
            "total_records": r.total_records,
            "valid_records": r.valid_records,
            "invalid_records": r.invalid_records,
            "null_violations": r.null_violations,
            "range_violations": r.range_violations,
            "quality_rate": round(quality_rate, 2)
        })
    return summary

@router.get("/data/{source}")
def get_source_data(
    source: str, 
    limit: int = Query(20, ge=1, le=1000), 
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    query = text("""
        SELECT event_id, ingested_at, record_id, event_timestamp, 
               temperature, humidity, temperature_f, processed_at
        FROM processed_records
        WHERE source = :source
        ORDER BY event_timestamp DESC
        LIMIT :limit OFFSET :offset
    """)
    results = db.execute(query, {"source": source, "limit": limit, "offset": offset}).fetchall()
    
    data = []
    for r in results:
        data.append({
            "event_id": str(r.event_id),
            "ingested_at": r.ingested_at,
            "record_id": r.record_id,
            "event_timestamp": r.event_timestamp,
            "temperature": r.temperature,
            "humidity": r.humidity,
            "temperature_f": r.temperature_f,
            "processed_at": r.processed_at
        })
    return {"source": source, "count": len(data), "data": data}

@router.get("/data/{source}/aggregates")
def get_source_aggregates(
    source: str, 
    limit: int = Query(20, ge=1, le=1000), 
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    query = text("""
        SELECT window_start, window_end, avg_temperature, avg_humidity, record_count
        FROM telemetry_aggregates
        WHERE source = :source
        ORDER BY window_start DESC
        LIMIT :limit OFFSET :offset
    """)
    results = db.execute(query, {"source": source, "limit": limit, "offset": offset}).fetchall()
    
    aggregates = []
    for r in results:
        aggregates.append({
            "window_start": r.window_start,
            "window_end": r.window_end,
            "avg_temperature": round(r.avg_temperature, 2) if r.avg_temperature else None,
            "avg_humidity": round(r.avg_humidity, 2) if r.avg_humidity else None,
            "record_count": r.record_count
        })
    return {"source": source, "count": len(aggregates), "data": aggregates}
