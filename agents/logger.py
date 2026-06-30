"""
Structured JSON Logging with Correlation ID

Provides:
- JSON-formatted logs for production parsing (Datadog, Papertrail, etc.)
- Correlation ID per request/session for end-to-end tracing
- Context-aware logging (user_id, task, session_id)
"""
import json
import logging
import uuid
import sys
from datetime import datetime
from typing import Optional, Dict, Any


class CorrelationIDFilter(logging.Filter):
    """Inject correlation_id into every log record."""
    
    def __init__(self, correlation_id: Optional[str] = None):
        super().__init__()
        self.correlation_id = correlation_id or str(uuid.uuid4())
    
    def filter(self, record: logging.LogRecord) -> bool:
        record.correlation_id = self.correlation_id
        return True


class StructuredFormatter(logging.Formatter):
    """Format logs as JSON with structured fields."""
    
    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "correlation_id": getattr(record, "correlation_id", None),
        }
        
        # Add optional context fields
        if hasattr(record, "user_id"):
            log_entry["user_id"] = record.user_id
        if hasattr(record, "session_id"):
            log_entry["session_id"] = record.session_id
        if hasattr(record, "task"):
            log_entry["task"] = record.task
        
        # Add exception info if present
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)
        
        # Add extra fields from record.__dict__
        for key, value in record.__dict__.items():
            if key not in {"msg", "args", "levelname", "levelno", "pathname", 
                          "filename", "module", "lineno", "funcName", "created",
                          "msecs", "relativeCreated", "thread", "threadName",
                          "processName", "process", "message", "exc_info",
                          "exc_text", "stack_info", "name", "correlation_id",
                          "user_id", "session_id", "task"}:
                try:
                    json.dumps(value)  # Check if serializable
                    log_entry[key] = value
                except (TypeError, ValueError):
                    log_entry[key] = str(value)
        
        return json.dumps(log_entry, ensure_ascii=False)


def get_correlation_id() -> str:
    """Generate or retrieve current correlation ID."""
    # In a real async app, you'd use contextvars here
    return str(uuid.uuid4())


def create_logger(
    name: str,
    level: int = logging.INFO,
    correlation_id: Optional[str] = None,
) -> logging.Logger:
    """
    Create a structured logger with correlation ID support.
    
    Args:
        name: Logger name (usually __name__)
        level: Logging level (default: INFO)
        correlation_id: Optional correlation ID for tracing
    
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # Remove existing handlers to avoid duplicates
    if logger.handlers:
        logger.handlers.clear()
    
    # Create console handler
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(level)
    
    # Add correlation ID filter
    corr_filter = CorrelationIDFilter(correlation_id)
    handler.addFilter(corr_filter)
    
    # Set JSON formatter
    formatter = StructuredFormatter()
    handler.setFormatter(formatter)
    
    logger.addHandler(handler)
    
    return logger


def log_with_context(
    logger: logging.Logger,
    level: int,
    message: str,
    user_id: Optional[str] = None,
    session_id: Optional[str] = None,
    task: Optional[str] = None,
    **extra: Any,
):
    """
    Log a message with contextual information.
    
    Usage:
        log_with_context(logger, logging.INFO, "Task started", 
                        user_id="123", task="content_generator")
    """
    # Create a copy of the record with extra fields
    extra_fields = {"user_id": user_id, "session_id": session_id, "task": task}
    extra_fields.update(extra)
    
    # Use logger's built-in extra parameter
    logger.log(level, message, extra=extra_fields)


# Convenience functions for common patterns
def debug(logger: logging.Logger, msg: str, **ctx):
    log_with_context(logger, logging.DEBUG, msg, **ctx)


def info(logger: logging.Logger, msg: str, **ctx):
    log_with_context(logger, logging.INFO, msg, **ctx)


def warning(logger: logging.Logger, msg: str, **ctx):
    log_with_context(logger, logging.WARNING, msg, **ctx)


def error(logger: logging.Logger, msg: str, exc_info: bool = False, **ctx):
    """Log error with optional stack trace."""
    if exc_info:
        logger.error(msg, exc_info=True, extra=ctx)
    else:
        log_with_context(logger, logging.ERROR, msg, **ctx)


def critical(logger: logging.Logger, msg: str, exc_info: bool = True, **ctx):
    """Log critical error with stack trace by default."""
    logger.critical(msg, exc_info=exc_info, extra=ctx)


def get_logger(name: str, level: int = logging.INFO) -> logging.Logger:
    """Alias for create_logger with simpler API for webapp usage."""
    return create_logger(name, level)
