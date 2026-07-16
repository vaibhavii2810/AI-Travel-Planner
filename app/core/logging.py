"""
Structured logging configuration.
Uses Python's standard logging with a JSON-friendly formatter for production.
Secrets are never logged — plan_id is the primary identifier in log lines.
"""
from __future__ import annotations

import logging
import sys
from typing import Any


class SanitizingFilter(logging.Filter):
    """Strip any field that might contain an API key before emission."""

    _SENSITIVE_SUBSTRINGS = ("api_key", "secret", "password", "token", "authorization")

    def filter(self, record: logging.LogRecord) -> bool:  # noqa: A003
        msg = str(record.getMessage()).lower()
        for substr in self._SENSITIVE_SUBSTRINGS:
            if substr in msg:
                record.msg = "[REDACTED — possible sensitive data in log message]"
                record.args = ()
                break
        return True


def setup_logging(log_level: str = "INFO") -> None:
    """
    Configure root logger.
    Call once at application startup (FastAPI lifespan).
    """
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)

    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(numeric_level)

    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )
    handler.setFormatter(formatter)
    handler.addFilter(SanitizingFilter())

    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)
    root_logger.handlers.clear()
    root_logger.addHandler(handler)

    # Suppress noisy third-party loggers
    for noisy in ("httpx", "httpcore", "openai", "langchain", "urllib3"):
        logging.getLogger(noisy).setLevel(logging.WARNING)

    logging.getLogger("app").setLevel(numeric_level)


def get_logger(name: str) -> logging.Logger:
    """Convenience wrapper — use this in every module."""
    return logging.getLogger(f"app.{name}")


def log_node_entry(logger: logging.Logger, node_name: str, plan_id: str, extra: dict[str, Any] | None = None) -> None:
    """Standardized node entry log line."""
    msg = f"[NODE:{node_name}] Entering | plan_id={plan_id}"
    if extra:
        extras = " | ".join(f"{k}={v}" for k, v in extra.items())
        msg += f" | {extras}"
    logger.info(msg)


def log_node_exit(logger: logging.Logger, node_name: str, plan_id: str, status: str) -> None:
    """Standardized node exit log line."""
    logger.info(f"[NODE:{node_name}] Exiting  | plan_id={plan_id} | status={status}")
