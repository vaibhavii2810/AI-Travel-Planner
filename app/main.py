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
        
        # ── Interest/destination catalogue for mock personalization ──────────────
        _ATTRACTION_CATALOGUE = {
            "food": [
                ("Local Food Market", "Browse fresh produce, street food stalls and artisan vendors at the city's bustling central market", 12.0, 1.5),
                ("Cooking Class & Tasting", "Join a hands-on cooking class led by a local chef — learn signature dishes and enjoy a full tasting meal", 55.0, 3.0),
                ("Rooftop Restaurant", "Dine at a celebrated rooftop restaurant offering panoramic views and a curated tasting menu", 45.0, 2.0),
                ("Street Food Night Tour", "Guided evening walk through the city's best street food lanes — sample 8–10 local specialties", 30.0, 2.5),
            ],
            "shopping": [
                ("Artisan Bazaar", "Wander through narrow lanes packed with handmade crafts, textiles, and local souvenirs", 0.0, 2.0),
                ("Designer Shopping District", "Explore the upscale shopping boulevard lined with flagship stores and boutique brands", 0.0, 2.5),
                ("Vintage & Antique Market", "Hunt for unique finds at the weekend flea market — vintage clothing, art prints, and collectibles", 0.0, 1.5),
                ("Night Market", "A lively night market offering fashion, homeware, electronics, and local snacks under string lights", 15.0, 2.0),
            ],
            "nightlife": [
                ("Rooftop Cocktail Bar", "Sip craft cocktails with skyline views at the city's most iconic rooftop bar — reservations recommended", 25.0, 2.0),
                ("Live Jazz Lounge", "Unwind at a dimly lit jazz lounge featuring live performances from local musicians", 20.0, 2.5),
                ("Underground Club Night", "Dance the night away at a renowned underground electronic music club", 30.0, 4.0),
                ("Riverside Evening Cruise", "Board a night cruise along the river — live music, cocktails, and illuminated city skyline", 40.0, 2.0),
            ],
            "culture": [
                ("National History Museum", "Explore galleries spanning thousands of years of local history, art, and artefacts", 18.0, 2.5),
                ("Heritage Old Town Walk", "Guided walking tour through the UNESCO-listed old town — cobblestone streets, colonial architecture, and hidden courtyards", 22.0, 2.0),
                ("Traditional Performing Arts Show", "Witness a live performance of the region's classical dance, music, or theatre tradition", 35.0, 2.0),
                ("Local Temple or Sacred Site", "Visit a centuries-old temple or sacred monument — guided commentary on local spiritual traditions", 10.0, 1.5),
            ],
            "nature": [
                ("National Park Day Hike", "Trek through scenic trails in the nearby national park — lush forests, waterfalls, and panoramic viewpoints", 20.0, 5.0),
                ("Botanical Gardens", "Stroll through manicured botanical gardens featuring rare tropical and endemic plant species", 8.0, 1.5),
                ("Sunrise Viewpoint", "Rise early for a breathtaking sunrise at the city's most famous hilltop or coastal viewpoint", 0.0, 1.5),
                ("River Kayaking / Boat Tour", "Paddle through scenic waterways or take a guided boat tour through mangroves and wildlife habitats", 35.0, 3.0),
            ],
            "adventure": [
                ("Rock Climbing Session", "Beginner-to-intermediate rock climbing at a local crag with certified instructors", 45.0, 3.0),
                ("Zip-line Canopy Tour", "Soar through forest canopies on a multi-platform zip-line adventure course", 60.0, 2.5),
                ("White Water Rafting", "Navigate Grade 3–4 rapids on a guided white-water rafting expedition", 70.0, 4.0),
                ("Mountain Biking Trail", "Ride curated mountain bike trails ranging from scenic countryside to technical singletrack", 30.0, 3.0),
            ],
            "art": [
                ("Contemporary Art Gallery", "Tour a world-class contemporary art gallery — rotating exhibitions from local and international artists", 15.0, 2.0),
                ("Street Art District Walk", "Discover vibrant murals and installations in the city's famous street art neighbourhood", 0.0, 1.5),
                ("Pottery or Craft Workshop", "Join a hands-on workshop and create your own piece of local pottery or traditional craft", 40.0, 2.5),
                ("Photography Walk", "Join a guided photography walk through photogenic city streets and markets", 25.0, 2.0),
            ],
            "sightseeing": [
                ("Iconic City Landmark", "Visit the city's most famous landmark — a must-see for every visitor", 20.0, 1.5),
                ("Panoramic Observation Deck", "Ride to the top of the city's tallest tower for 360° views of the skyline and beyond", 25.0, 1.0),
                ("Historic Neighbourhood Tour", "Explore charming old neighbourhoods packed with character, cafés, and local life", 10.0, 2.0),
                ("Waterfront Promenade", "Stroll along the scenic waterfront promenade — ideal at golden hour", 0.0, 1.0),
            ],
        }

        _WEATHER_BY_REGION = [
            (["japan", "korea", "china", "taiwan"],          (22.0, 71.6, "Partly Cloudy", 25.0, 60.0)),
            (["iceland", "norway", "sweden", "finland",
              "denmark", "scotland", "alaska"],              (7.0,  44.6, "Cold & Overcast", 55.0, 75.0)),
            (["thailand", "bali", "indonesia", "vietnam",
              "singapore", "malaysia", "philippines"],        (32.0, 89.6, "Hot & Humid",  60.0, 85.0)),
            (["india", "dubai", "egypt", "morocco",
              "saudi", "uae", "rajasthan"],                   (35.0, 95.0, "Sunny & Hot",   5.0,  30.0)),
            (["italy", "france", "spain", "portugal",
              "greece", "croatia"],                          (24.0, 75.2, "Warm & Sunny",  15.0, 55.0)),
            (["uk", "london", "england", "ireland"],          (14.0, 57.2, "Cloudy with light rain", 45.0, 70.0)),
            (["australia", "new zealand"],                   (26.0, 78.8, "Sunny",          20.0, 50.0)),
            (["brazil", "argentina", "colombia", "peru"],    (28.0, 82.4, "Warm & Partly Cloudy", 40.0, 65.0)),
            (["canada", "usa"],                              (18.0, 64.4, "Clear",           20.0, 55.0)),
        ]

        def _get_weather(destination: str):
            dest_lower = destination.lower()
            for keywords, data in _WEATHER_BY_REGION:
                if any(k in dest_lower for k in keywords):
                    return data
            return (20.0, 68.0, "Sunny", 10.0, 55.0)  # default

        def _get_interest_attractions(interests: list[str], destination: str) -> list[Attraction]:
            """Build a rich, interest-tailored attraction list."""
            results = []
            seen_names = set()
            # Map aliases
            alias_map = {"history": "culture", "outdoors": "nature", "music": "nightlife"}
            normalised = [alias_map.get(i, i) for i in interests]

            for interest in normalised:
                pool = _ATTRACTION_CATALOGUE.get(interest, [])
                for (name, desc, cost, hours) in pool:
                    # Make names destination-specific
                    specific_name = f"{destination.split(',')[0].strip()} — {name}"
                    if specific_name in seen_names:
                        continue
                    seen_names.add(specific_name)
                    results.append(Attraction(
                        name=specific_name,
                        description=desc,
                        category=interest,
                        estimated_visit_duration_hours=hours,
                        approximate_cost_per_person=cost,
                    ))

            # If nothing matched, fall back to sightseeing
            if not results:
                for (name, desc, cost, hours) in _ATTRACTION_CATALOGUE["sightseeing"]:
                    specific_name = f"{destination.split(',')[0].strip()} — {name}"
                    results.append(Attraction(
                        name=specific_name,
                        description=desc,
                        category="sightseeing",
                        estimated_visit_duration_hours=hours,
                        approximate_cost_per_person=cost,
                    ))
            return results

        def _interest_tips_and_packing(interests: list[str]) -> tuple[list[str], list[str]]:
            tips_map = {
                "food":      ["Ask locals for off-menu recommendations", "Book popular restaurants 2–3 days in advance", "Carry antacids for adventurous street food tasting"],
                "shopping":  ["Bargain politely at markets — start at 60% of the asking price", "Keep receipts for tax-free refunds at the airport", "Bring an extra foldable bag for purchases"],
                "nightlife": ["Carry government-issued ID — many venues require it", "Use licensed taxis or ride-share apps late at night", "Pre-book tables at rooftop bars for weekend nights"],
                "culture":   ["Dress modestly when visiting religious sites", "Download the museum app for audio guides", "Visit popular sites early morning to avoid crowds"],
                "nature":    ["Book guided hikes in advance during peak season", "Check weather forecasts the evening before outdoor activities", "Leave no trace — take rubbish back with you"],
                "adventure": ["Ensure your travel insurance covers adventure activities", "Listen carefully to safety briefings before each activity", "Stay hydrated and wear sunscreen for outdoor sessions"],
                "art":       ["Check gallery websites for free entry days", "Photography rules vary — always ask before shooting", "Visit on weekday mornings for the quietest experience"],
            }
            packing_map = {
                "food":      ["Appetite and an open mind", "Small notebook to jot restaurant names"],
                "shopping":  ["A tote bag or daypack", "Padlock for hostel/hotel storage"],
                "nightlife": ["Smart-casual outfit for venues", "Portable charger"],
                "culture":   ["Respectful clothing (shoulders + knees covered)", "Pocket notebook for sketching"],
                "nature":    ["Sturdy walking/hiking shoes", "Sunscreen SPF 50+", "Reusable water bottle"],
                "adventure": ["Quick-dry activewear", "First aid kit basics", "GoPro or action camera"],
                "art":       ["Sketchbook or journal", "Comfortable walking shoes"],
            }
            alias_map = {"history": "culture", "outdoors": "nature", "music": "nightlife"}
            normalised = [alias_map.get(i, i) for i in interests]

            tips, packing = [], ["Passport and travel documents", "Travel adapter", "Comfortable walking shoes"]
            seen_tips, seen_packing = set(), set(packing)
            for interest in normalised:
                for t in tips_map.get(interest, []):
                    if t not in seen_tips:
                        tips.append(t)
                        seen_tips.add(t)
                for p in packing_map.get(interest, []):
                    if p not in seen_packing:
                        packing.append(p)
                        seen_packing.add(p)
            if not tips:
                tips = ["Have local cash handy", "Keep digital copies of your documents"]
            return tips, packing

        def _build_day_plan(
            day_num: int,
            date,
            destination: str,
            morning_slot: tuple,
            afternoon_slot: tuple,
            evening_slot: tuple,
        ) -> DailyPlan:
            """Build a daily plan from pre-assigned unique activity slots.

            Each slot is (name, desc, cost, duration_hours, interest_category).
            Activities are pre-assigned by mock_invoke_planner_agent from a
            deduplicated flat pool — so no activity ever repeats across days.
            """
            city = destination.split(",")[0].strip()

            theme_labels = {
                "food": "Food & Flavours",
                "shopping": "Retail Therapy",
                "nightlife": "Nightlife & Entertainment",
                "culture": "Culture & Heritage",
                "nature": "Into the Wild",
                "adventure": "Thrill & Adventure",
                "art": "Art & Expression",
                "sightseeing": "City Sights",
            }

            m_name, m_desc, m_cost, m_dur_h, m_cat = morning_slot
            a_name, a_desc, a_cost, a_dur_h, a_cat = afternoon_slot
            e_name, e_desc, e_cost, e_dur_h, e_cat = evening_slot

            # Day theme is driven by the morning interest
            theme = theme_labels.get(m_cat, "Explore & Enjoy")

            morning_tips = [
                "Best visited early — beat the queues and enjoy at your own pace.",
                "Arrive 15 minutes before opening for a calm start to the day.",
                "Morning light makes for great photos at this spot!",
                "Grab breakfast nearby before you head in.",
            ]
            afternoon_tips = [
                "Afternoons here are lively — embrace the local energy.",
                "Grab a coffee or snack first to keep your energy up.",
                "Weekday afternoons are quieter — perfect timing.",
                "Ask staff for their personal recommendation — it's usually worth it.",
            ]
            evening_tips = [
                "Book ahead — this spot fills up quickly, especially on weekends.",
                "Arrive a little early to grab the best seat.",
                "Dress smart-casual — the atmosphere is relaxed but stylish.",
                "End the night here and let the vibe carry you.",
            ]

            daily_cost = round(m_cost + a_cost + e_cost + 45.0, 2)  # 45 flat for transport + misc

            return DailyPlan(
                day_number=day_num,
                date=date,
                theme=theme,
                morning=[
                    Activity(
                        name=f"{city} — {m_name}",
                        description=m_desc,
                        location=destination,
                        duration_minutes=int(m_dur_h * 60),
                        estimated_cost_per_person=m_cost,
                        booking_required=m_cost > 30,
                        tips=morning_tips[day_num % len(morning_tips)],
                    )
                ],
                afternoon=[
                    Activity(
                        name=f"{city} — {a_name}",
                        description=a_desc,
                        location=destination,
                        duration_minutes=int(a_dur_h * 60),
                        estimated_cost_per_person=a_cost,
                        booking_required=a_cost > 40,
                        tips=afternoon_tips[day_num % len(afternoon_tips)],
                    )
                ],
                evening=[
                    Activity(
                        name=f"{city} — {e_name}",
                        description=e_desc,
                        location=destination,
                        duration_minutes=int(e_dur_h * 60),
                        estimated_cost_per_person=e_cost,
                        booking_required=e_cost > 25,
                        tips=evening_tips[day_num % len(evening_tips)],
                    )
                ],
                accommodation="Centrally located boutique hotel",
                estimated_daily_cost_per_person=daily_cost,
                travel_notes=f"Day {day_num}: {theme}. Use public transport or ride-share for easy city navigation.",
            )


        async def mock_invoke_research_agent(*args, **kwargs):
            destination = kwargs.get("destination", args[0] if args else "Kyoto, Japan")
            interests = kwargs.get("interests", [])
            logger.info(f"[MOCK] invoke_research_agent called for destination={destination} interests={interests}")

            temp_c, temp_f, conditions, precip, humidity = _get_weather(destination)
            attractions = _get_interest_attractions(interests, destination)

            interest_tips = {
                "food":      "Try eating where locals eat — avoid overly touristy restaurants near major attractions.",
                "shopping":  "Most markets open late morning — arrive fresh at 10am for the best selection.",
                "nightlife": "Pre-drink at the hotel to save on venue prices. Many clubs open after midnight.",
                "culture":   "Purchase museum combo passes for significant savings on multi-site visits.",
                "nature":    "Start hikes and outdoor activities early to beat heat and crowds.",
                "adventure": "Confirm operator certifications before booking any adventure activity.",
                "art":       "Follow local art accounts on social media to discover pop-up exhibitions.",
            }
            local_tips = ["Download an offline city map before you land", "Carry the local emergency number saved in your phone"]
            for i in interests:
                tip = interest_tips.get(i)
                if tip:
                    local_tips.append(tip)

            return ResearchOutput(
                attractions=attractions,
                local_tips=local_tips,
                safety_considerations=["Stay aware in crowded tourist areas", "Use ATMs inside banks rather than street kiosks"],
                weather_summary=WeatherSummary(
                    avg_temp_celsius=temp_c,
                    avg_temp_fahrenheit=temp_f,
                    conditions=conditions,
                    precipitation_chance_percent=precip,
                    humidity_percent=humidity,
                    warnings=(["Pack a light rain jacket"] if precip > 40 else []),
                    data_available=True,
                ),
                seasonal_notes=f"Current conditions in {destination}: {conditions}. {'Expect warm days — stay hydrated.' if temp_c > 28 else 'Comfortable travel weather — great time to visit.' if temp_c > 15 else 'Pack warm layers — temperatures can drop significantly.'}",
                general_destination_info=f"{destination} is a vibrant destination perfect for {', '.join(interests) if interests else 'all types of travellers'}. The city blends modern energy with deep cultural roots, offering something unique at every turn.",
                research_sources=["https://wikipedia.org", "https://tripadvisor.com", "https://lonelyplanet.com"],
                researched_at=datetime.now(timezone.utc),
            )

        async def mock_invoke_planner_agent(*args, **kwargs):
            req = kwargs.get("travel_request", args[0] if args else None)
            revision_count = kwargs.get("revision_count", args[2] if len(args) > 2 else 0)
            logger.info(f"[MOCK] invoke_planner_agent | destination={req.destination} | interests={req.interests} | v={revision_count + 1}")

            alias_map = {"history": "culture", "outdoors": "nature", "music": "nightlife"}
            interests = [alias_map.get(i, i) for i in (req.interests or ["sightseeing"])]

            # Build a flat, deduplicated activity pool across all selected interests.
            # Each entry: (name, desc, cost, duration_hours, category)
            flat_pool: list[tuple] = []
            seen_names: set[str] = set()
            for cat in interests:
                for (name, desc, cost, hours) in _ATTRACTION_CATALOGUE.get(cat, []):
                    if name not in seen_names:
                        flat_pool.append((name, desc, cost, hours, cat))
                        seen_names.add(name)
            # Fall back to sightseeing if pool is empty
            if not flat_pool:
                for (name, desc, cost, hours) in _ATTRACTION_CATALOGUE["sightseeing"]:
                    flat_pool.append((name, desc, cost, hours, "sightseeing"))

            # If the trip is longer than the pool, cycle back but ensure each day
            # still has 3 distinct activities (morning ≠ afternoon ≠ evening).
            # We achieve this by extending the pool with shuffled copies.
            import itertools
            num_days = (req.end_date - req.start_date).days + 1
            needed = num_days * 3
            while len(flat_pool) < needed:
                flat_pool = flat_pool + flat_pool  # double it until large enough
            # Assign slots sequentially — no activity shares a day slot
            slot_cursor = 0

            daily_plans = []
            current_date = req.start_date
            day_num = 1
            while current_date <= req.end_date:
                morning_slot   = flat_pool[slot_cursor % len(flat_pool)]; slot_cursor += 1
                afternoon_slot = flat_pool[slot_cursor % len(flat_pool)]; slot_cursor += 1
                evening_slot   = flat_pool[slot_cursor % len(flat_pool)]; slot_cursor += 1
                daily_plans.append(
                    _build_day_plan(day_num, current_date, req.destination, morning_slot, afternoon_slot, evening_slot)
                )
                current_date += timedelta(days=1)
                day_num += 1

            total_days = len(daily_plans)
            total_cost = sum(p.estimated_daily_cost_per_person for p in daily_plans) * req.num_travelers

            food_weight         = 0.30 if "food"      in interests else 0.22
            nightlife_weight    = 0.12 if "nightlife" in interests else 0.05
            activities_weight   = 0.15 if any(i in interests for i in ["adventure", "culture", "art"]) else 0.10
            accommodation_weight = 0.35
            transport_weight    = 0.10
            contingency_weight  = max(0.03, 1.0 - food_weight - nightlife_weight - activities_weight - accommodation_weight - transport_weight)

            overall_tips, packing = _interest_tips_and_packing(req.interests or [])

            return DraftItinerary(
                version=revision_count + 1,
                daily_plans=daily_plans,
                budget_allocation=BudgetAllocation(
                    accommodation_total=round(total_cost * accommodation_weight, 2),
                    transport_total=round(total_cost * transport_weight, 2),
                    food_total=round(total_cost * food_weight, 2),
                    activities_total=round(total_cost * (activities_weight + nightlife_weight), 2),
                    contingency_total=round(total_cost * contingency_weight, 2),
                    grand_total=round(total_cost, 2),
                    per_person_total=round(total_cost / max(req.num_travelers, 1), 2),
                    currency=req.budget_currency,
                    within_budget=total_cost <= req.budget_max,
                    notes=f"Budget optimised for {', '.join(interests)} preferences over {total_days} days.",
                ),
                overall_tips=overall_tips,
                packing_suggestions=packing,
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
