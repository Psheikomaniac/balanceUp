import logging
import json
from typing import Any, Dict
from pythonjsonlogger import jsonlogger
from app.config.settings import get_settings

settings = get_settings()

class CustomJsonFormatter(jsonlogger.JsonFormatter):
    def add_fields(self, log_record: Dict[str, Any], record: logging.LogRecord, message_dict: Dict[str, Any]) -> None:
        super().add_fields(log_record, record, message_dict)
        log_record['level'] = record.levelname
        log_record['logger'] = record.name
        log_record['timestamp'] = self.formatTime(record)

def setup_logging() -> None:
    """Configure structured logging with JSON format"""
    log_handler = logging.StreamHandler()
    formatter = CustomJsonFormatter('%(timestamp)s %(level)s %(name)s %(message)s')
    log_handler.setFormatter(formatter)

    # Configure file logging if LOG_FILE is set
    if settings.LOG_FILE:
        file_handler = logging.FileHandler(settings.LOG_FILE)
        file_handler.setFormatter(formatter)
        logging.getLogger().addHandler(file_handler)

    # Set root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(settings.LOG_LEVEL)
    root_logger.addHandler(log_handler)

    # Disable uvicorn access logger to avoid duplicate logs
    logging.getLogger("uvicorn.access").handlers = []