"""
Checkpointer factory — ENV-gated, lifecycle-managed.

Risk 2 bypass:
- setup() runs during FastAPI lifespan (before any request)
- MemorySaver for test, SqliteSaver for dev, AsyncPostgresSaver for production
- Context manager ensures connection pool is properly closed on shutdown
"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from langgraph.checkpoint.memory import MemorySaver
from langgraph.checkpoint.base import BaseCheckpointSaver

from app.core.config import Environment, Settings
from app.core.exceptions import CheckpointerError

logger = logging.getLogger("app.core.checkpointer")


@asynccontextmanager
async def build_checkpointer(settings: Settings) -> AsyncGenerator[BaseCheckpointSaver, None]:
    """
    Async context manager that yields the appropriate checkpointer
    and guarantees cleanup on exit.

    Usage (in FastAPI lifespan):
        async with build_checkpointer(settings) as checkpointer:
            app.state.checkpointer = checkpointer
            yield
    """
    env = settings.ENV

    if env == Environment.TEST:
        logger.info("Checkpointer: MemorySaver (test mode)")
        yield MemorySaver()
        return

    if env == Environment.DEV:
        try:
            from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver  # type: ignore[import]
            db_path = settings.DATABASE_URL.replace("sqlite:///", "")
            logger.info(f"Checkpointer: AsyncSqliteSaver (dev) | path={db_path}")
            async with AsyncSqliteSaver.from_conn_string(db_path) as saver:
                await saver.setup()
                logger.info("Checkpointer: SQLite schema ready")
                yield saver
            return
        except ImportError:
            logger.warning(
                "AsyncSqliteSaver not available — falling back to MemorySaver. "
                "Install langgraph-checkpoint-sqlite for persistent dev storage."
            )
            yield MemorySaver()
            return

    # Production: AsyncPostgresSaver
    if env == Environment.PRODUCTION:
        try:
            from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver  # type: ignore[import]
            db_url = settings.DATABASE_URL
            logger.info("Checkpointer: AsyncPostgresSaver (production)")
            async with AsyncPostgresSaver.from_conn_string(db_url) as saver:
                await saver.setup()  # CREATE TABLE IF NOT EXISTS — idempotent
                logger.info("Checkpointer: Postgres schema ready")
                yield saver
            return
        except ImportError as exc:
            raise CheckpointerError(
                "AsyncPostgresSaver not installed. "
                "Run: pip install langgraph-checkpoint-postgres"
            ) from exc
        except Exception as exc:
            raise CheckpointerError(f"Failed to connect to Postgres: {exc}") from exc

    raise CheckpointerError(f"Unknown environment: {env}")
