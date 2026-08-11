import json
import time
import uuid
import datetime
from confluent_kafka import Producer

p = Producer({'bootstrap.servers': 'kafka:9092'})

def delivery_report(err, msg):
    if err is not None:
        print(f'Message delivery failed: {err}')
    else:
        print(f'Message delivered to {msg.topic()}')

def make_event(humidity_val, advance_minutes=0):
    t = datetime.datetime.utcnow() + datetime.timedelta(minutes=advance_minutes)
    return {
        "event_id": str(uuid.uuid4()),
        "source": "sales",
        "ingested_at": t.isoformat() + 'Z',
        "payload": {
            "temperature": 25.0,
            "humidity": humidity_val
        }
    }

# Good record for sales
p.produce('streamo.raw.sales', json.dumps(make_event(50.0)).encode('utf-8'), callback=delivery_report)

# Bad record for sales (range violation: humidity > 100)
p.produce('streamo.raw.sales', json.dumps(make_event(150.0)).encode('utf-8'), callback=delivery_report)

# Advance watermark by 6 minutes
p.produce('streamo.raw.sales', json.dumps(make_event(50.0, advance_minutes=6)).encode('utf-8'), callback=delivery_report)

p.flush()
print("Injected events.")
