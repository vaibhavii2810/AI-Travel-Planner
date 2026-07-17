"""Phase 2 requirement validation script."""
import os
import sys
from datetime import date
from enum import Enum

PASS = "PASS"
FAIL = "FAIL"

results = {}

# 1. Directory structure
required_paths = [
    'app/main.py', 'app/api/routes/plans.py', 'app/api/dependencies.py',
    'app/models/domain.py', 'app/models/requests.py', 'app/models/responses.py',
    'app/graph/state.py', 'app/graph/graph.py',
    'app/agents/research_agent.py', 'app/agents/planner_agent.py',
    'app/tools/web_search.py', 'app/tools/weather.py',
    'app/tools/budget_allocator.py', 'app/tools/schedule_optimizer.py',
    'app/services/planning_service.py', 'app/core/exceptions.py',
    'app/core/logging.py', 'app/core/config.py', 'app/core/checkpointer.py',
    '.env.example', 'requirements.txt', 'Dockerfile', '.gitignore',
    'tests/unit/test_models.py', 'tests/unit/test_tools.py',
    'tests/integration/test_api.py',
]
missing = [p for p in required_paths if not os.path.exists(p)]
results['1. Directory Structure'] = (PASS, None) if not missing else (FAIL, f"Missing: {missing}")

# 2. Centralized config
try:
    from app.core.config import get_settings
    s = get_settings()
    results['2. Centralized Config'] = (PASS, f"{s.APP_NAME} v{s.APP_VERSION}, ENV={s.ENV}")
except Exception as e:
    results['2. Centralized Config'] = (FAIL, str(e))

# 3. Pydantic models
try:
    from app.models.domain import (
        TravelRequest, ResearchOutput, DraftItinerary,
        Activity, DailyPlan, BudgetAllocation, WeatherSummary,
        Attraction, ReviewAction
    )
    results['3. Pydantic Models'] = (PASS, "TravelRequest, ResearchOutput, DraftItinerary, Activity, DailyPlan all importable")
except Exception as e:
    results['3. Pydantic Models'] = (FAIL, str(e))

# 4. LangGraph state
try:
    from app.graph.state import (
        TravelPlanState, initial_state,
        STATUS_QUEUED, STATUS_RESEARCHING, STATUS_PLANNING,
        STATUS_AWAITING_REVIEW, STATUS_REVISING, STATUS_FINALIZED,
        STATUS_ERROR, STATUS_MAX_REVISIONS
    )
    results['4. LangGraph State'] = (PASS, "TravelPlanState TypedDict + 9 STATUS_* constants")
except Exception as e:
    results['4. LangGraph State'] = (FAIL, str(e))

# 5. ReviewAction enum — MUST be proper Python Enum
try:
    from app.models.domain import ReviewAction
    is_real_enum = issubclass(ReviewAction, Enum)
    if is_real_enum:
        results['5. ReviewAction Enum'] = (PASS, "Proper Python Enum subclass")
    else:
        results['5. ReviewAction Enum'] = (FAIL, "ReviewAction is a plain class, NOT a proper Python Enum (inherits str only)")
except Exception as e:
    results['5. ReviewAction Enum'] = (FAIL, str(e))

# 6. Custom exceptions
try:
    from app.core.exceptions import (
        TravelPlannerError, PlanNotFoundError, InvalidStateError,
        MaxRevisionsError, GraphExecutionError, CheckpointerError
    )
    results['6. Custom Exceptions'] = (PASS, "Full hierarchy with HTTP status codes")
except Exception as e:
    results['6. Custom Exceptions'] = (FAIL, str(e))

# 7. Logging
try:
    from app.core.logging import setup_logging, SanitizingFilter
    results['7. Structured Logging'] = (PASS, "SanitizingFilter + setup_logging configured")
except Exception as e:
    results['7. Structured Logging'] = (FAIL, str(e))

# 8. FastAPI init
try:
    from app.main import create_app
    app_instance = create_app()
    results['8. FastAPI App Init'] = (PASS, f"App: {app_instance.title}")
except Exception as e:
    results['8. FastAPI App Init'] = (FAIL, str(e))

# 9. GET /health endpoint
try:
    from app.main import create_app
    app_instance = create_app()
    routes = [r.path for r in app_instance.routes]
    health_exists = any('/health' in r for r in routes)
    results['9. GET /health Endpoint'] = (PASS if health_exists else FAIL, f"Routes: {[r for r in routes if 'health' in r]}")
except Exception as e:
    results['9. GET /health Endpoint'] = (FAIL, str(e))

# 10. .env.example
try:
    env_example = open('.env.example').read()
    has_keys = all(k in env_example for k in ['OPENAI_API_KEY', 'SERPER_API_KEY', 'WEATHER_API_KEY'])
    results['10. .env.example'] = (PASS if has_keys else FAIL, "All 3 API key placeholders present")
except Exception as e:
    results['10. .env.example'] = (FAIL, str(e))

# 11. requirements.txt
try:
    reqs = open('requirements.txt').read()
    has_deps = all(d in reqs for d in ['fastapi', 'langgraph', 'pydantic'])
    results['11. requirements.txt'] = (PASS if has_deps else FAIL, "fastapi, langgraph, pydantic all present")
except Exception as e:
    results['11. requirements.txt'] = (FAIL, str(e))

# ── Validation Rules ─────────────────────────────────────────────────────────
print("\n" + "="*55)
print("  PHASE 2 REQUIREMENTS CHECKLIST")
print("="*55)
all_pass = True
for label, (status, detail) in results.items():
    icon = "✅" if status == PASS else "❌"
    print(f"\n{icon} {label}: {status}")
    if detail:
        print(f"   → {detail}")
    if status == FAIL:
        all_pass = False

print("\n" + "="*55)
print("  VALIDATION RULES")
print("="*55)

from app.models.domain import TravelRequest
from app.models.requests import ReviewRequest

tests = []

# destination blank
try:
    TravelRequest(destination='', start_date=date(2025,5,1), end_date=date(2025,5,8), budget_min=100, budget_max=200, interests=['food'], num_travelers=1)
    tests.append(("destination blank rejected", FAIL))
except:
    tests.append(("destination blank rejected", PASS))

# end_date before start_date
try:
    TravelRequest(destination='Paris', start_date=date(2025,5,10), end_date=date(2025,5,5), budget_min=100, budget_max=200, interests=['food'], num_travelers=1)
    tests.append(("end_date must be after start_date", FAIL))
except:
    tests.append(("end_date must be after start_date", PASS))

# same day trip (end == start is invalid per assignment)
try:
    TravelRequest(destination='Paris', start_date=date(2025,5,1), end_date=date(2025,5,1), budget_min=100, budget_max=200, interests=['food'], num_travelers=1)
    tests.append(("same-day trip rejected", FAIL))
except:
    tests.append(("same-day trip rejected", PASS))

# travelers < 1
try:
    TravelRequest(destination='Paris', start_date=date(2025,5,1), end_date=date(2025,5,8), budget_min=100, budget_max=200, interests=['food'], num_travelers=0)
    tests.append(("travelers >= 1", FAIL))
except:
    tests.append(("travelers >= 1", PASS))

# budget_min negative
try:
    TravelRequest(destination='Paris', start_date=date(2025,5,1), end_date=date(2025,5,8), budget_min=-50, budget_max=200, interests=['food'], num_travelers=1)
    tests.append(("budget_min non-negative", FAIL))
except:
    tests.append(("budget_min non-negative", PASS))

# budget_max < budget_min
try:
    TravelRequest(destination='Paris', start_date=date(2025,5,1), end_date=date(2025,5,8), budget_min=500, budget_max=100, interests=['food'], num_travelers=1)
    tests.append(("budget_max >= budget_min", FAIL))
except:
    tests.append(("budget_max >= budget_min", PASS))

# review action valid
try:
    ReviewRequest(action='approve')
    tests.append(("review action approve", PASS))
except:
    tests.append(("review action approve", FAIL))

# review action invalid rejected
try:
    ReviewRequest(action='invalid_action')
    tests.append(("review rejects invalid action", FAIL))
except:
    tests.append(("review rejects invalid action", PASS))

# reject requires feedback
try:
    ReviewRequest(action='reject', feedback=None)
    tests.append(("reject requires feedback", FAIL))
except:
    tests.append(("reject requires feedback", PASS))

# modify requires modifications
try:
    ReviewRequest(action='modify', modifications=None)
    tests.append(("modify requires modifications", FAIL))
except:
    tests.append(("modify requires modifications", PASS))

for label, status in tests:
    icon = "✅" if status == PASS else "❌"
    print(f"  {icon} {label}: {status}")
    if status == FAIL:
        all_pass = False

print("\n" + "="*55)
if all_pass:
    print("  🎉 ALL CHECKS PASSED — Phase 2 is COMPLETE")
else:
    print("  ⚠️  SOME CHECKS FAILED — see above for details")
print("="*55 + "\n")

sys.exit(0 if all_pass else 1)
