import logging.config
import logging
import os
import sys
from pythonjsonlogger.json import JsonFormatter
from app.config.settings import get_settings

settings = get_settings()

class CustomJsonFormatter(JsonFormatter):
    def add_fields(self, log_record, record, message_dict):
        super(CustomJsonFormatter, self).add_fields(log_record, record, message_dict)
        log_record['app'] = 'balance_up'
        log_record['environment'] = os.getenv('ENVIRONMENT', 'development')
        if record.exc_info:
            log_record['exception'] = self.formatException(record.exc_info)

def setup_logging() -> None:
    """Setup JSON logging configuration"""
    json_formatter = JsonFormatter(
        fmt='%(asctime)s %(levelname)s %(name)s %(message)s',
        timestamp=True
    )
    
    # Configure root logger
    root_logger = logging.getLogger()
    handler = logging.StreamHandler()
    handler.setFormatter(json_formatter)
    root_logger.addHandler(handler)
    root_logger.setLevel(logging.INFO)

def get_logger(name: str) -> logging.Logger:
    """Get a configured logger instance"""
    return logging.getLogger(name)
