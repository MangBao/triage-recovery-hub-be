"""Centralized logging configuration with file rotation."""

import logging
import os
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path

from app.config import settings


def setup_logging(log_dir: str = "logs") -> None:
    """
    Configure application-wide logging with console and rotating file handlers.
    
    Features:
    - Console output (stdout) for Docker logs
    - Daily rotating file logs (7 days retention)
    - Separate error log file
    - Consistent format across handlers
    
    Args:
        log_dir: Directory for log files (default: ./logs)
    """
    # Create logs directory
    log_path = Path(log_dir)
    log_path.mkdir(exist_ok=True)
    
    # Log format
    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    date_format = "%Y-%m-%d %H:%M:%S"
    formatter = logging.Formatter(log_format, datefmt=date_format)
    
    # Root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG if settings.DEBUG else logging.INFO)
    
    # Clear existing handlers to avoid duplicates on reload
    root_logger.handlers.clear()
    
    # 1. Console Handler (stdout - for Docker)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG if settings.DEBUG else logging.INFO)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # 2. Rotating File Handler (all logs)
    app_log_file = log_path / "app.log"
    file_handler = TimedRotatingFileHandler(
        filename=str(app_log_file),
        when="midnight",      # Rotate at midnight
        interval=1,           # Every day
        backupCount=7,        # Keep 7 days
        encoding="utf-8"
    )
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(formatter)
    file_handler.suffix = "%Y-%m-%d"  # app.log.2026-01-31
    root_logger.addHandler(file_handler)
    
    # 3. Error-only File Handler (for quick error review)
    error_log_file = log_path / "error.log"
    error_handler = TimedRotatingFileHandler(
        filename=str(error_log_file),
        when="midnight",
        interval=1,
        backupCount=14,       # Keep 14 days of errors
        encoding="utf-8"
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(formatter)
    error_handler.suffix = "%Y-%m-%d"
    root_logger.addHandler(error_handler)
    
    # Silence noisy third-party loggers
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    
    logging.info(f"📋 Logging initialized: console + file rotation ({log_dir}/)")
