import json
import uuid
import datetime
from confluent_kafka import Producer

def run():
    producer = Producer({'bootstrap.servers': 'kafka:9092'})
    
    # Bad Event 1: Invalid humidity (150 > 100), bad temperature type
    payload = {
        "id": 1234,
        "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
        "temperature": "very hot",
        "humidity": 150
    }
    
    envelope = {
        "event_id": str(uuid.uuid4()),
        "source": "mock_bad",
        "ingested_at": datetime.datetime.utcnow().isoformat() + "Z",
        "payload": payload
    }
    
    producer.produce(
        topic="streamo.raw.mock",
        key=envelope["source"].encode('utf-8'),
        value=json.dumps(envelope).encode('utf-8')
    )
    producer.flush()
    print(f"Injected bad event: {envelope['event_id']}")

if __name__ == "__main__":
    run()
