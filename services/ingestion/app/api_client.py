import httpx
from tenacity import retry, wait_exponential, stop_after_attempt, retry_if_exception_type, before_sleep_log
import logging
from .config import MAX_RETRIES, BACKOFF_BASE_SECONDS, REQUEST_TIMEOUT
from .logging_config import get_logger, StructuredLogger

base_logger = get_logger()
log = StructuredLogger(base_logger)

class APIError(Exception):
    pass

class RateLimitError(Exception):
    def __init__(self, retry_after=None):
        self.retry_after = retry_after
        super().__init__("Rate limited")

def log_retry(retry_state):
    log.warning("Retrying request", attempt=retry_state.attempt_number)

class APIClient:
    def __init__(self, source_name: str, url: str):
        self.source_name = source_name
        self.url = url
        self.client = httpx.Client(timeout=REQUEST_TIMEOUT)
    
    @retry(
        retry=(retry_if_exception_type((httpx.RequestError, httpx.TimeoutException, APIError, RateLimitError))),
        wait=wait_exponential(multiplier=BACKOFF_BASE_SECONDS, min=1, max=60),
        stop=stop_after_attempt(MAX_RETRIES),
        before_sleep=log_retry,
        reraise=True
    )
    def fetch_data(self) -> dict:
        try:
            response = self.client.get(self.url)
            
            if response.status_code == 429:
                retry_after = response.headers.get("Retry-After")
                log.warning("Rate limited", source=self.source_name, status_code=429)
                raise RateLimitError(retry_after)
                
            response.raise_for_status()
            
            return response.json()
            
        except httpx.HTTPStatusError as e:
            if e.response.status_code in [408, 500, 502, 503, 504]:
                raise APIError(f"Transient HTTP error: {e.response.status_code}")
            log.error("API request failed", source=self.source_name, status_code=e.response.status_code)
            raise e # Non-transient errors (e.g. 404, 401) will fail fast
            
        except (httpx.RequestError, httpx.TimeoutException) as e:
            raise e
            
    def close(self):
        self.client.close()
