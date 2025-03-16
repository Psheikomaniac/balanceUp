import logging.config
import logging
import os
import sys
from pythonjsonlogger import jsonlogger
from app.config.settings import get_settings

settings = get_settings()

class CustomJsonFormatter(jsonlogger.JsonFormatter):
    def add_fields(self, log_record, record, message_dict):
        super(CustomJsonFormatter, self).add_fields(log_record, record, message_dict)
        log_record['app'] = 'balance_up'
        log_record['environment'] = os.getenv('ENVIRONMENT', 'development')
        if record.exc_info:
            log_record['exception'] = self.formatException(record.exc_info)

def setup_logging():
    """Configure logging for the application"""
    log_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)
    
    handlers = {
        "console": {
            "class": "logging.StreamHandler",
            "stream": sys.stdout,
            "formatter": "default" if settings.LOG_FORMAT.lower() != "json" else "json",
            "level": log_level,
        }
    }
    
    formatters = {
        "default": {
            "format": "[%(asctime)s] %(levelname)s in %(module)s: %(message)s",
            "datefmt": "%Y-%m-%d %H:%M:%S",
        },
        "json": {
            "()": CustomJsonFormatter,
            "format": "%(timestamp)s %(level)s %(name)s %(module)s %(funcName)s %(lineno)d %(message)s",
        }
    }
    
    # Add file handler if LOG_FILE is specified
    if settings.LOG_FILE:
        os.makedirs(os.path.dirname(settings.LOG_FILE), exist_ok=True)
        handlers["file"] = {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": settings.LOG_FILE,
            "maxBytes": 10485760,  # 10MB
            "backupCount": 5,
            "formatter": "default" if settings.LOG_FORMAT.lower() != "json" else "json",
            "level": log_level,
        }
    
    logging.config.dictConfig({
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": formatters,
        "handlers": handlers,
        "root": {
            "handlers": list(handlers.keys()),
            "level": log_level,
        },
        "loggers": {
            "uvicorn": {"level": log_level},
            "sqlalchemy.engine": {"level": "WARNING"},
            "fastapi": {"level": log_level},
        }
    })
    
    # Set log level for specific libraries
    if not settings.is_production:
        logging.getLogger("sqlalchemy.engine").setLevel(logging.INFO)

def get_logger(name):
    """Get a logger with the given name"""
    return logging.getLogger(name)
