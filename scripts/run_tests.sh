#!/bin/bash
set -e

echo "Setting up test environment..."
python3 -m venv .venv
source .venv/bin/activate

echo "Installing dependencies..."
pip install pytest httpx
pip install -r services/control_plane/requirements.txt
pip install -r services/ingestion/requirements.txt
pip install -r services/mock_api/requirements.txt

# Manually install pyspark and confluent_kafka for the standalone test scripts
pip install pyspark confluent_kafka

echo "Running tests..."
export PYTHONPATH=./services/ingestion:./services/control_plane:./services/processing:$PYTHONPATH
pytest tests/
pytest test_schema.py
# Note: scripts/load_test.py is a load testing script, not a pytest suite.

echo "Tests completed successfully."
