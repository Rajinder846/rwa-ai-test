import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

import structlog

from app.config.settings import settings


def configure_logging() -> None:
    """
    Configure application-wide structured logging.
    """

    log_directory = Path("logs")
    log_directory.mkdir(parents=True, exist_ok=True)

    log_level = getattr(
        logging,
        settings.log_level.upper(),
        logging.INFO,
    )

    timestamper = structlog.processors.TimeStamper(
        fmt="iso",
        utc=True,
    )

    shared_processors = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        timestamper,
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]

    formatter = structlog.stdlib.ProcessorFormatter(
        processor=structlog.processors.JSONRenderer(),
        foreign_pre_chain=shared_processors,
    )

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)

    file_handler = RotatingFileHandler(
        filename=log_directory / "app.log",
        maxBytes=10 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8",
    )

    file_handler.setFormatter(formatter)

    logging.basicConfig(
        level=log_level,
        handlers=[
            console_handler,
            file_handler,
        ],
        force=True,
    )

    structlog.configure(
        processors=[
            *shared_processors,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str = "ai-platform"):
    return structlog.get_logger(name)