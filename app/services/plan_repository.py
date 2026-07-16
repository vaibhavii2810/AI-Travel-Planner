"""
Plan Repository — thin metadata store for immediate GET responses.

Risk 3 bypass:
- Writes plan metadata BEFORE launching background graph task
- GET /plan/{id} can return immediately (doesn't wait for checkpoint to exist)
- Uses in-memory dict for dev/test; replace with SQLAlchemy+Postgres for production

In production: replace _store with an async DB table (plans: id, status, created_at, error_message).
"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Optional

logger = logging.getLogger("app.services.plan_repository")


class PlanMeta:
    """Lightweight metadata record — NOT the full graph state."""
    __slots__ = ("plan_id", "status", "created_at", "updated_at", "error_message")

    def __init__(self, plan_id: str, status: str):
        now = datetime.utcnow()
        self.plan_id = plan_id
        self.status = status
        self.created_at = now
        self.updated_at = now
        self.error_message: Optional[str] = None

    def update(self, status: str, error_message: Optional[str] = None) -> None:
        self.status = status
        self.updated_at = datetime.utcnow()
        if error_message is not None:
            self.error_message = error_message


# In-memory store (dev/test). In production, replace with async DB layer.
_store: dict[str, PlanMeta] = {}


class PlanRepository:
    """
    Manages lightweight plan metadata records.
    Decoupled from LangGraph checkpointer — always responds instantly.
    """

    async def create(self, plan_id: str, status: str = "queued") -> PlanMeta:
        meta = PlanMeta(plan_id=plan_id, status=status)
        _store[plan_id] = meta
        logger.info(f"PlanRepository.create | plan_id={plan_id} | status={status}")
        return meta

    async def get(self, plan_id: str) -> Optional[PlanMeta]:
        return _store.get(plan_id)

    async def update(
        self,
        plan_id: str,
        status: str,
        error_message: Optional[str] = None,
    ) -> Optional[PlanMeta]:
        meta = _store.get(plan_id)
        if meta:
            meta.update(status=status, error_message=error_message)
            logger.info(f"PlanRepository.update | plan_id={plan_id} | status={status}")
        return meta

    async def exists(self, plan_id: str) -> bool:
        return plan_id in _store

    async def delete(self, plan_id: str) -> bool:
        return _store.pop(plan_id, None) is not None
