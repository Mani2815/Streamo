import os
import uuid
import random
import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Import from control_plane models
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '../services/control_plane'))
from app.models import Base, Source, ProcessedRecord, TelemetryAggregate, DataQualityMetric

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    print("Error: DATABASE_URL environment variable is required to seed demo data.")
    sys.exit(1)

print(f"Connecting to database to seed demo data...")
engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)

def seed_data():
    session = Session()
    try:
        # Create Tables if they don't exist
        Base.metadata.create_all(engine)

        # 1. Create a Source
        source_name = "demo_iot_sensors"
        existing_source = session.query(Source).filter_by(name=source_name).first()
        if not existing_source:
            source = Source(
                name=source_name,
                url="https://api.example.com/sensors (DEMO)",
                poll_interval=10,
                schema={"temperature": "numeric", "humidity": "numeric", "sensor_id": "string"},
                status="active"
            )
            session.add(source)
            session.commit()
            print(f"Created demo source: {source_name}")
        else:
            print(f"Source {source_name} already exists. Appending demo data.")

        # 2. Create Processed Records
        now = datetime.datetime.now(datetime.timezone.utc)
        print("Generating 50 recent records...")
        records = []
        for i in range(50):
            ts = now - datetime.timedelta(minutes=50-i)
            temp = round(random.uniform(20.0, 35.0), 2)
            hum = round(random.uniform(30.0, 60.0), 2)
            
            records.append(ProcessedRecord(
                event_id=uuid.uuid4(),
                source=source_name,
                ingested_at=ts,
                record_id=random.randint(1000, 9000),
                event_timestamp=ts,
                temperature=temp,
                humidity=hum,
                temperature_f=round((temp * 9/5) + 32, 2),
                payload={"sensor_id": f"sens_{random.randint(1,5)}", "temperature": temp, "humidity": hum},
                processed_at=ts + datetime.timedelta(seconds=2)
            ))
        session.bulk_save_objects(records)
        
        # 3. Create Quality Metrics
        print("Generating Quality Metrics...")
        qm = DataQualityMetric(
            source=source_name,
            run_timestamp=now,
            total_records=1500,
            valid_records=1490,
            invalid_records=10,
            duplicate_records=2,
            null_violations=5,
            range_violations=3,
            freshness_violations=0,
            quality_rate=99.3
        )
        # Handle unique constraint if run multiple times
        existing_qm = session.query(DataQualityMetric).filter_by(source=source_name).first()
        if not existing_qm:
            session.add(qm)
        else:
            existing_qm.total_records += 50
            existing_qm.valid_records += 50
            existing_qm.run_timestamp = now

        # 4. Create Telemetry Aggregates
        print("Generating Telemetry Aggregates...")
        aggs = []
        for i in range(5):
            w_start = now - datetime.timedelta(hours=5-i)
            w_end = w_start + datetime.timedelta(hours=1)
            # Avoid duplicate primary key
            existing_agg = session.query(TelemetryAggregate).filter_by(source=source_name, window_start=w_start).first()
            if not existing_agg:
                aggs.append(TelemetryAggregate(
                    source=source_name,
                    window_start=w_start,
                    window_end=w_end,
                    avg_temperature=round(random.uniform(22.0, 28.0), 2),
                    avg_humidity=round(random.uniform(40.0, 55.0), 2),
                    record_count=random.randint(200, 500)
                ))
        if aggs:
            session.bulk_save_objects(aggs)

        session.commit()
        print("Successfully seeded demo data!")

    except Exception as e:
        session.rollback()
        print(f"Error seeding data: {e}")
    finally:
        session.close()

if __name__ == "__main__":
    seed_data()
