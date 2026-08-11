import logging
import sys

class DefaultAttributesFilter(logging.Filter):
    def filter(self, record):
        if not hasattr(record, 'source'):
            record.source = '-'
        if not hasattr(record, 'event_id'):
            record.event_id = '-'
        if not hasattr(record, 'extra_info'):
            record.extra_info = ''
        return True

def setup_logging():
    handler = logging.StreamHandler(sys.stdout)
    handler.addFilter(DefaultAttributesFilter())
    logging.basicConfig(
        level=logging.INFO,
        format='%(levelname)s source=%(source)s event_id=%(event_id)s message="%(message)s" %(extra_info)s',
        handlers=[handler]
    )

def get_logger(name="ingestion"):
    return logging.getLogger(name)

class StructuredLogger:
    def __init__(self, logger):
        self.logger = logger
    
    def _log(self, level, message, source="-", event_id="-", **kwargs):
        extra_str = " ".join(f"{k}={v}" for k, v in kwargs.items())
        extra = {
            "source": source,
            "event_id": event_id,
            "extra_info": extra_str
        }
        if level == "info":
            self.logger.info(message, extra=extra)
        elif level == "warning":
            self.logger.warning(message, extra=extra)
        elif level == "error":
            self.logger.error(message, extra=extra)

    def info(self, message, source="-", event_id="-", **kwargs):
        self._log("info", message, source, event_id, **kwargs)
        
    def warning(self, message, source="-", event_id="-", **kwargs):
        self._log("warning", message, source, event_id, **kwargs)
        
    def error(self, message, source="-", event_id="-", **kwargs):
        self._log("error", message, source, event_id, **kwargs)
