"""
Dependency injection for FastAPI routes.
Provides PlanningService via app.state (set in lifespan).
"""
from __future__ import annotations

from fastapi import Depends, Request

from app.services.plan_repository import PlanRepository
from app.services.planning_service import PlanningService


def get_planning_service(request: Request) -> PlanningService:
    """Inject PlanningService from app.state (wired in lifespan)."""
    return request.app.state.planning_service


def get_plan_repo(request: Request) -> PlanRepository:
    """Inject PlanRepository from app.state."""
    return request.app.state.plan_repo
