import json
import uuid
import datetime
from confluent_kafka import Producer

def run():
    producer = Producer({'bootstrap.servers': 'kafka:9092'})
    
    event_id = str(uuid.uuid4())
    
    payload = {
        "id": 9999,
        "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
        "temperature": 25.5,
        "humidity": 60
    }
    
    envelope = {
        "event_id": event_id,
        "source": "mock_duplicate",
        "ingested_at": datetime.datetime.utcnow().isoformat() + "Z",
        "payload": payload
    }
    
    # Inject 3 times
    for _ in range(3):
        producer.produce(
            topic="streamo.raw.mock",
            key=envelope["source"].encode('utf-8'),
            value=json.dumps(envelope).encode('utf-8')
        )
        
    producer.flush()
    print(f"Injected duplicate event 3 times: {event_id}")

if __name__ == "__main__":
    run()
