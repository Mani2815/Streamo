from sqlalchemy import Column, Integer, String, JSON, DateTime, Float, BigInteger, CheckConstraint, Index, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from .database import Base

class Source(Base):
    __tablename__ = "sources"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)
    url = Column(String, nullable=False)
    poll_interval = Column(Integer, nullable=False, default=60)
    schema = Column(JSON, nullable=True)
    status = Column(String(50), default='active')
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

class ProcessedRecord(Base):
    __tablename__ = "processed_records"
    event_id = Column(UUID(as_uuid=True), primary_key=True)
    source = Column(String(255), nullable=False)
    ingested_at = Column(DateTime(timezone=True), nullable=False)
    record_id = Column(BigInteger)
    event_timestamp = Column(DateTime(timezone=True))
    temperature = Column(Float)
    humidity = Column(Float)
    temperature_f = Column(Float)
    payload = Column(JSON)
    processed_at = Column(DateTime(timezone=True), nullable=False)
    served_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        CheckConstraint('temperature BETWEEN -50 AND 100', name='check_temperature_range'),
        CheckConstraint('humidity BETWEEN 0 AND 100', name='check_humidity_range'),
        Index('idx_processed_records_source', 'source'),
        Index('idx_processed_records_event_timestamp', 'event_timestamp'),
    )

class TelemetryAggregate(Base):
    __tablename__ = "telemetry_aggregates"
    source = Column(String(255), nullable=False, primary_key=True)
    window_start = Column(DateTime(timezone=True), nullable=False, primary_key=True)
    window_end = Column(DateTime(timezone=True), nullable=False)
    avg_temperature = Column(Float)
    avg_humidity = Column(Float)
    record_count = Column(BigInteger, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class DataQualityMetric(Base):
    __tablename__ = "data_quality_metrics"
    id = Column(Integer, primary_key=True)
    source = Column(String(255), nullable=False)
    run_timestamp = Column(DateTime(timezone=True), nullable=False)
    total_records = Column(BigInteger, nullable=False, default=0)
    valid_records = Column(BigInteger, nullable=False, default=0)
    invalid_records = Column(BigInteger, nullable=False, default=0)
    duplicate_records = Column(BigInteger, nullable=False, default=0)
    null_violations = Column(BigInteger, nullable=False, default=0)
    range_violations = Column(BigInteger, nullable=False, default=0)
    freshness_violations = Column(BigInteger, nullable=False, default=0)
    quality_rate = Column(Float, nullable=False, default=100.0)

    __table_args__ = (
        UniqueConstraint('source', 'run_timestamp', name='unique_source_run'),
    )
