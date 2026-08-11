import json
import uuid
import datetime
import random
import time
from confluent_kafka import Producer
import argparse

def create_event(source_name="mock"):
    payload = {
        "id": random.randint(1000, 9999),
        "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
        "temperature": round(random.uniform(10.0, 35.0), 1),
        "humidity": random.randint(40, 90)
    }
    envelope = {
        "event_id": str(uuid.uuid4()),
        "source": source_name,
        "ingested_at": datetime.datetime.utcnow().isoformat() + "Z",
        "payload": payload
    }
    return envelope

def delivery_report(err, msg):
    pass # Silent for high throughput

def run_load_test(events_per_sec, duration_sec):
    producer = Producer({
        'bootstrap.servers': 'kafka:9092',
        'linger.ms': 10,
        'batch.num.messages': 1000,
        'queue.buffering.max.messages': 1000000
    })
    
    total_events = events_per_sec * duration_sec
    print(f"Starting load test: {events_per_sec} eps for {duration_sec}s (Total: {total_events})")
    
    start_time = time.time()
    events_sent = 0
    
    while time.time() - start_time < duration_sec:
        loop_start = time.time()
        
        for _ in range(events_per_sec):
            event = create_event()
            producer.produce(
                topic=f"streamo.raw.mock",
                key=event["source"].encode('utf-8'),
                value=json.dumps(event).encode('utf-8'),
                on_delivery=delivery_report
            )
            events_sent += 1
            
        producer.poll(0)
        
        # Sleep for remainder of the second
        elapsed = time.time() - loop_start
        if elapsed < 1.0:
            time.sleep(1.0 - elapsed)
            
    producer.flush()
    print(f"Load test complete. Sent {events_sent} events.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--eps", type=int, default=100)
    parser.add_argument("--duration", type=int, default=30)
    args = parser.parse_args()
    
    run_load_test(args.eps, args.duration)
