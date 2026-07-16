"""
FastAPI application factory with lifespan, CORS, and exception handlers.

Risk 2 bypass: checkpointer setup() happens in lifespan BEFORE any request is served.
"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes.plans import router as plans_router
from app.core.checkpointer import build_checkpointer
from app.core.config import get_settings
from app.core.exceptions import TravelPlannerError
from app.core.logging import setup_logging
from app.graph.graph import build_graph
from app.models.responses import ErrorResponse, HealthResponse
from app.services.plan_repository import PlanRepository
from app.services.planning_service import PlanningService

logger = logging.getLogger("app.main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.
    Startup: Configure logging → Build checkpointer (setup DB schema) → Build graph → Wire service.
    Shutdown: Checkpointer connection pool closed automatically.
    """
    settings = get_settings()

    # ① Logging first — everything after needs logging
    setup_logging(settings.LOG_LEVEL)
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION} | env={settings.ENV}")

    # ② Checkpointer — setup() runs here, tables created before first request (Risk 2 bypass)
    async with build_checkpointer(settings) as checkpointer:
        logger.info(f"Checkpointer ready: {type(checkpointer).__name__}")

        # ③ Compile graph (fails fast if checkpointer is None)
        graph = build_graph(checkpointer=checkpointer)
        logger.info("TravelPlannerGraph compiled and ready")

        # ④ Wire service layer
        plan_repo = PlanRepository()
        planning_service = PlanningService(graph=graph, plan_repo=plan_repo)

        # ⑤ Attach to app.state for dependency injection
        app.state.checkpointer = checkpointer
        app.state.graph = graph
        app.state.plan_repo = plan_repo
        app.state.planning_service = planning_service

        logger.info(f"{settings.APP_NAME} ready — listening on {settings.API_PREFIX}")
        yield

    # ⑥ Cleanup: checkpointer context manager handles pool closure
    logger.info(f"{settings.APP_NAME} shutting down")


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description=(
            "AI-powered multi-agent travel planning system with Human-in-the-Loop approval. "
            "Powered by LangGraph + FastAPI."
        ),
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    # ── CORS ──────────────────────────────────────────────────────────────────
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Exception Handlers ────────────────────────────────────────────────────

    @app.exception_handler(TravelPlannerError)
    async def travel_planner_error_handler(request: Request, exc: TravelPlannerError):
        logger.warning(f"TravelPlannerError | {exc.error_code} | {exc.message}")
        return JSONResponse(
            status_code=exc.http_status,
            content=exc.to_dict(),
        )

    @app.exception_handler(Exception)
    async def generic_error_handler(request: Request, exc: Exception):
        logger.exception(f"Unhandled exception on {request.method} {request.url}: {exc}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"error": "INTERNAL_ERROR", "message": "An unexpected error occurred."},
        )

    # ── Routes ────────────────────────────────────────────────────────────────
    app.include_router(plans_router, prefix=settings.API_PREFIX)

    # ── Health endpoint ────────────────────────────────────────────────────────
    @app.get(
        settings.API_PREFIX + "/health",
        response_model=HealthResponse,
        tags=["Health"],
        summary="Application health check",
    )
    async def health_check(request: Request) -> HealthResponse:
        checkpointer = getattr(request.app.state, "checkpointer", None)
        return HealthResponse(
            status="healthy",
            app_name=settings.APP_NAME,
            version=settings.APP_VERSION,
            environment=settings.ENV.value,
            checkpointer=type(checkpointer).__name__ if checkpointer else "not_initialized",
        )

    @app.get("/", include_in_schema=False)
    async def root():
        return {
            "app": settings.APP_NAME,
            "version": settings.APP_VERSION,
            "docs": "/docs",
            "health": "/health",
        }

    return app


# ── Entry point ───────────────────────────────────────────────────────────────
app = create_app()
