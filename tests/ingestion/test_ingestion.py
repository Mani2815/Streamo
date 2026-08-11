import pytest
from unittest.mock import patch, MagicMock
from app.api_client import APIClient, RateLimitError, APIError
from app.models import EventEnvelope
import httpx
import time

def test_event_envelope_generation():
    payload = {"id": 1, "temperature": 28.5, "humidity": 72}
    envelope = EventEnvelope(source="test", payload=payload)
    
    assert envelope.source == "test"
    assert envelope.payload == payload
    assert envelope.event_id is not None
    assert envelope.ingested_at is not None

@patch('httpx.Client.get')
def test_api_client_success(mock_get):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"success": True}
    mock_get.return_value = mock_response

    client = APIClient("test", "http://mock-api:8001/data")
    data = client.fetch_data()
    
    assert data == {"success": True}
    mock_get.assert_called_once()

@patch('httpx.Client.get')
def test_api_client_retry_behavior_429(mock_get):
    # Simulate two 429s then a 200
    resp_429 = MagicMock()
    resp_429.status_code = 429
    resp_429.headers = {"Retry-After": "1"}
    
    resp_200 = MagicMock()
    resp_200.status_code = 200
    resp_200.json.return_value = {"success": True}
    
    mock_get.side_effect = [resp_429, resp_429, resp_200]
    
    client = APIClient("test", "http://mock-api:8001/data")
    
    start_time = time.time()
    data = client.fetch_data()
    end_time = time.time()
    
    assert data == {"success": True}
    assert mock_get.call_count == 3
    # Exponential backoff min 1 sec per retry, so should take at least ~2-3 seconds total
    assert (end_time - start_time) > 1.0

@patch('httpx.Client.get')
def test_api_client_retry_behavior_500(mock_get):
    resp_500 = MagicMock()
    resp_500.status_code = 500
    
    # We need to raise HTTPStatusError for httpx to trigger our custom logic in the client
    error = httpx.HTTPStatusError("500", request=MagicMock(), response=resp_500)
    mock_get.side_effect = error
    
    client = APIClient("test", "http://mock-api:8001/data")
    
    with pytest.raises(APIError):
        client.fetch_data()
        
    # Since we max out retries, it should call multiple times (default MAX_RETRIES=5)
    assert mock_get.call_count > 1

@patch('app.kafka_producer.Producer')
def test_kafka_producer(mock_producer_class):
    mock_producer = mock_producer_class.return_value
    
    from app.kafka_producer import StreamoKafkaProducer
    producer = StreamoKafkaProducer()
    
    envelope = EventEnvelope(source="test", payload={"data": 1})
    producer.publish_event(envelope)
    
    mock_producer.produce.assert_called_once()
    kwargs = mock_producer.produce.call_args.kwargs
    assert kwargs['topic'] == 'streamo.raw.test'
    assert kwargs['key'] == b'test'
