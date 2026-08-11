import os

KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092")
CONTROL_PLANE_URL = os.getenv("CONTROL_PLANE_URL", "http://control-plane:8000")
MAX_RETRIES = int(os.getenv("MAX_RETRIES", 5))
BACKOFF_BASE_SECONDS = int(os.getenv("BACKOFF_BASE_SECONDS", 1))
REQUEST_TIMEOUT = float(os.getenv("REQUEST_TIMEOUT", 10.0))
# Optional single source override for testing without control plane
STATIC_SOURCE_NAME = os.getenv("STATIC_SOURCE_NAME")
STATIC_SOURCE_URL = os.getenv("STATIC_SOURCE_URL")
STATIC_POLL_INTERVAL = int(os.getenv("STATIC_POLL_INTERVAL", 10))
