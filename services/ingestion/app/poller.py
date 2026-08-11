import time
import httpx
import json
from typing import Any, Dict
from .api_client import APIClient
from .kafka_producer import StreamoKafkaProducer
from .models import EventEnvelope
from .logging_config import get_logger, StructuredLogger
from .config import CONTROL_PLANE_URL, STATIC_SOURCE_NAME, STATIC_SOURCE_URL, STATIC_POLL_INTERVAL

base_logger = get_logger()
log = StructuredLogger(base_logger)

def normalize_payload(data: Any) -> list[Dict[str, Any]]:
    if isinstance(data, list):
        return [d for d in data if isinstance(d, dict)]
    
    if isinstance(data, dict):
        scalars = {k: v for k, v in data.items() if not isinstance(v, (list, dict))}
        
        # Check if root is columnar (e.g. {"time": [...], "temp": [...]})
        list_lengths = {k: len(v) for k, v in data.items() if isinstance(v, list)}
        if list_lengths and len(set(list_lengths.values())) == 1:
            length = list(list_lengths.values())[0]
            if length > 0:
                list_data = {k: v for k, v in data.items() if isinstance(v, list)}
                records = []
                for i in range(length):
                    rec = scalars.copy()
                    for k, v in list_data.items():
                        rec[k] = v[i]
                    records.append(rec)
                return records
                
        # Check 1 level deep for columnar (e.g. Open-Meteo {"hourly": {"time": [...], "temp": [...]}})
        for k, v in data.items():
            if isinstance(v, dict):
                list_lengths = {sub_k: len(sub_v) for sub_k, sub_v in v.items() if isinstance(sub_v, list)}
                if list_lengths and len(set(list_lengths.values())) == 1:
                    length = list(list_lengths.values())[0]
                    if length > 0:
                        list_data = {sub_k: sub_v for sub_k, sub_v in v.items() if isinstance(sub_v, list)}
                        records = []
                        for i in range(length):
                            rec = scalars.copy()
                            for sub_k, sub_v in list_data.items():
                                rec[sub_k] = sub_v[i]
                            records.append(rec)
                        return records
        
        # If no columnar structure found, just return the flat dict
        return [data]
        
    return []

class Poller:
    def __init__(self):
        self.producer = StreamoKafkaProducer()
        self.running = True
        
    def fetch_sources(self):
        # Allow static source override for testing without CP
        if STATIC_SOURCE_NAME and STATIC_SOURCE_URL:
            return [{
                "name": STATIC_SOURCE_NAME,
                "url": STATIC_SOURCE_URL,
                "poll_interval": STATIC_POLL_INTERVAL
            }]
            
        try:
            response = httpx.get(f"{CONTROL_PLANE_URL}/api/v1/sources/", timeout=10.0)
            response.raise_for_status()
            sources = response.json()
            return [s for s in sources if s.get("status") == "active"]
        except Exception as e:
            log.error("Failed to fetch sources from control plane", error=str(e))
            return []

    def start(self):
        log.info("Starting ingestion poller")
        
        while self.running:
            sources = self.fetch_sources()
            if not sources:
                log.info("No sources configured. Sleeping...")
                time.sleep(10)
                continue
                
            for source in sources:
                client = APIClient(source["name"], source["url"])
                try:
                    payload = client.fetch_data()
                    log.info("API request successful", source=source["name"])
                    
                    records = normalize_payload(payload)
                    for rec in records:
                        envelope = EventEnvelope(
                            source=source["name"],
                            payload=json.dumps(rec)
                        )
                        self.producer.publish_event(envelope)
                except Exception as e:
                    # Failure is logged inside APIClient or Producer, we just swallow here to keep polling
                    pass
                finally:
                    client.close()
            
            # Simple sequential wait for now. 
            # In a real system, we'd use AsyncIO or APScheduler for concurrent source polling.
            min_interval = min((s.get("poll_interval", 60) for s in sources), default=60)
            time.sleep(min_interval)

    def stop(self):
        self.running = False
        self.producer.flush()
        log.info("Ingestion poller stopped")
