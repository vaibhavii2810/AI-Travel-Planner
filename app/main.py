"""
FastAPI application factory with lifespan, CORS, and exception handlers.

Risk 2 bypass: checkpointer setup() happens in lifespan BEFORE any request is served.
"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request as StarletteRequest
from starlette.responses import Response as StarletteResponse

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
    # Check if we are running with default placeholder API keys and patch agents for easy local manual testing/demos
    if settings.OPENAI_API_KEY.get_secret_value() == "sk-..." or "placeholder" in settings.OPENAI_API_KEY.get_secret_value():
        logger.warning("Default/placeholder OpenAI API key detected. Patching agents with mock implementations for local testing.")
        
        import app.agents.research_agent as ra_mod
        import app.agents.planner_agent as pa_mod
        import app.graph.nodes.research_node as rn_mod
        import app.graph.nodes.planner_node as pn_mod
        from app.models.domain import ResearchOutput, Attraction, WeatherSummary, DraftItinerary, DailyPlan, Activity, BudgetAllocation
        from datetime import datetime, timezone, timedelta
        
        async def mock_invoke_research_agent(*args, **kwargs):
            destination = kwargs.get("destination", args[0] if args else "Kyoto, Japan")
            logger.info(f"[MOCK] invoke_research_agent called for destination={destination}")
            return ResearchOutput(
                attractions=[
                    Attraction(
                        name="Popular Attraction 1",
                        description=f"Must-visit landmark in {destination}",
                        category="sightseeing",
                        estimated_visit_duration_hours=2.0,
                        approximate_cost_per_person=15.0,
                    ),
                    Attraction(
                        name="Popular Attraction 2",
                        description="Beautiful natural park or scenic view",
                        category="nature",
                        estimated_visit_duration_hours=1.5,
                        approximate_cost_per_person=0.0,
                    ),
                ],
                local_tips=["Use local public transit", "Respect local customs"],
                safety_considerations=["Stay aware in crowded areas"],
                weather_summary=WeatherSummary(
                    avg_temp_celsius=20.0,
                    avg_temp_fahrenheit=68.0,
                    conditions="Sunny",
                    precipitation_chance_percent=10.0,
                    humidity_percent=55.0,
                    warnings=[],
                    data_available=True,
                ),
                seasonal_notes="Great season to travel here.",
                general_destination_info=f"Fascinating historic details about {destination}.",
                research_sources=["https://wikipedia.org"],
                researched_at=datetime.now(timezone.utc),
            )
            
        async def mock_invoke_planner_agent(*args, **kwargs):
            req = kwargs.get("travel_request", args[0] if args else None)
            revision_count = kwargs.get("revision_count", args[2] if len(args) > 2 else 0)
            
            logger.info(f"[MOCK] invoke_planner_agent called for version {revision_count + 1}")
            
            daily_plans = []
            current_date = req.start_date
            day_num = 1
            while current_date <= req.end_date:
                daily_plans.append(
                    DailyPlan(
                        day_number=day_num,
                        date=current_date,
                        theme="Explore & Enjoy",
                        morning=[
                            Activity(
                                name="Morning Exploration",
                                description="Start the day visiting key landmarks",
                                location=req.destination,
                                duration_minutes=120,
                                estimated_cost_per_person=10.0,
                            )
                        ],
                        afternoon=[
                            Activity(
                                name="Local Dining & Shopping",
                                description="Taste local food and check out market stalls",
                                location=req.destination,
                                duration_minutes=90,
                                estimated_cost_per_person=20.0,
                            )
                        ],
                        evening=[
                            Activity(
                                name="Relaxing Evening Stroll",
                                description="Unwind at a local park or cafe",
                                location=req.destination,
                                duration_minutes=90,
                                estimated_cost_per_person=0.0,
                            )
                        ],
                        accommodation="Recommended Local Hotel",
                        estimated_daily_cost_per_person=120.0,
                        travel_notes="Walk or take short taxi rides",
                    )
                )
                current_date += timedelta(days=1)
                day_num += 1
                
            total_cost = len(daily_plans) * 150.0
            
            return DraftItinerary(
                version=revision_count + 1,
                daily_plans=daily_plans,
                budget_allocation=BudgetAllocation(
                    accommodation_total=total_cost * 0.4,
                    transport_total=total_cost * 0.2,
                    food_total=total_cost * 0.25,
                    activities_total=total_cost * 0.1,
                    contingency_total=total_cost * 0.05,
                    grand_total=total_cost,
                    per_person_total=total_cost / max(req.num_travelers, 1),
                    currency=req.budget_currency,
                    within_budget=total_cost <= req.budget_max,
                ),
                overall_tips=["Have local cash handy"],
                packing_suggestions=["Comfortable shoes", "Adapters for electronics"],
                generated_at=datetime.now(timezone.utc),
            )
            
        ra_mod.invoke_research_agent = mock_invoke_research_agent
        rn_mod.invoke_research_agent = mock_invoke_research_agent
        pa_mod.invoke_planner_agent = mock_invoke_planner_agent
        pn_mod.invoke_planner_agent = mock_invoke_planner_agent

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

    # ── Request body size limit (100 KB) ──────────────────────────────────────
    # Prevents oversized payloads from overwhelming the application.
    # In production, also configure this at the reverse proxy (nginx/ALB) layer.
    MAX_BODY_SIZE = 100_000  # 100 KB

    @app.middleware("http")
    async def limit_request_size(request: Request, call_next):
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > MAX_BODY_SIZE:
            return JSONResponse(
                status_code=413,
                content={"error": "REQUEST_TOO_LARGE", "message": f"Request body exceeds {MAX_BODY_SIZE} bytes."},
            )
        return await call_next(request)

    # ── Exception Handlers ────────────────────────────────────────────────────

    @app.exception_handler(TravelPlannerError)
    async def travel_planner_error_handler(request: Request, exc: TravelPlannerError):
        logger.warning(f"TravelPlannerError | {exc.error_code} | {exc.message}")
        return JSONResponse(
            status_code=exc.http_status,
            content=exc.to_dict(),
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(request: Request, exc: RequestValidationError):
        """Normalize Pydantic/FastAPI validation errors into our consistent ErrorResponse schema."""
        errors = exc.errors()
        logger.warning(f"RequestValidationError on {request.method} {request.url.path}: {errors}")

        # Pydantic v2 ctx values may contain non-serializable objects (e.g. ValueError).
        # Sanitize them to strings so JSONResponse can serialize the payload.
        safe_errors = []
        for err in errors:
            safe_err = dict(err)
            if "ctx" in safe_err:
                safe_err["ctx"] = {k: str(v) for k, v in safe_err["ctx"].items()}
            safe_errors.append(safe_err)

        first = safe_errors[0] if safe_errors else {}
        field = ".".join(str(loc) for loc in first.get("loc", []) if loc != "body")
        msg = first.get("msg", "Validation error")
        detail = f"{field}: {msg}" if field else msg

        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "error": "VALIDATION_ERROR",
                "message": detail,
                "detail": safe_errors,  # Full errors included for client debugging; no stack traces
            },
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
