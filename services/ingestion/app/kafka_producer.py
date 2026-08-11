from confluent_kafka import Producer
import json
from .config import KAFKA_BOOTSTRAP_SERVERS
from .models import EventEnvelope
from .logging_config import get_logger, StructuredLogger

base_logger = get_logger()
log = StructuredLogger(base_logger)

class StreamoKafkaProducer:
    def __init__(self):
        conf = {
            'bootstrap.servers': KAFKA_BOOTSTRAP_SERVERS,
            'client.id': 'streamo-ingestion'
        }
        self.producer = Producer(conf)

    def _delivery_report(self, err, msg):
        if err is not None:
            log.error("Kafka delivery failed", error=str(err))
        else:
            # We don't log every success to avoid spam, but useful for debug
            pass

    def publish_event(self, envelope: EventEnvelope):
        topic = f"streamo.raw.{envelope.source}"
        try:
            # Trigger any available delivery report callbacks
            self.producer.poll(0)
            
            self.producer.produce(
                topic=topic,
                key=envelope.source.encode('utf-8'),
                value=envelope.model_dump_json().encode('utf-8'),
                callback=self._delivery_report
            )
            log.info("Kafka publish successful", source=envelope.source, event_id=envelope.event_id)
        except Exception as e:
            log.error("Kafka publish failed", source=envelope.source, event_id=envelope.event_id, error=str(e))
            raise e

    def flush(self):
        self.producer.flush()
