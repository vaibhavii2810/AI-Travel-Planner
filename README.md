# AI Travel Planner

A multi-agent travel planning system built with LangGraph and FastAPI, featuring genuine Human-in-the-Loop (HITL) approval workflows.

## Features

- **Research Agent**: ReAct-style agent utilizing Serper API and Weather tools to fetch real-time destination data.
- **Itinerary Planner Agent**: Generates structured, budget-aware day-by-day itineraries.
- **Genuine HITL**: LangGraph's `interrupt()` genuinely pauses execution, saving state to a checkpointer until a human review decision is received via the API.
- **Intelligent Routing**: Rejection feedback dynamically routes back to either the Research Agent (for factual updates) or the Planner Agent (for scheduling/budget tweaks).
- **Asynchronous Execution**: Background execution of long-running LLM tasks with a polling mechanism.

## Setup

1.  **Clone & Install**
    ```bash
    pip install -r requirements.txt
    ```

2.  **Environment Variables**
    Copy `.env.example` to `.env` and fill in your API keys:
    ```bash
    cp .env.example .env
    ```
    *   `OPENAI_API_KEY`: Required for the LLM agents.
    *   `SERPER_API_KEY`: Required for web search tool.
    *   `WEATHER_API_KEY`: Required for weather data.

3.  **Run Locally (Dev Mode)**
    In `dev` mode, the app uses an SQLite checkpointer automatically.
    ```bash
    uvicorn app.main:app --reload
    ```

## API Endpoints

*   `POST /api/v1/plan`: Submit a travel request. Returns a `plan_id`.
*   `GET /api/v1/plan/{plan_id}`: Poll for status and view the draft itinerary when status is `awaiting_review`.
*   `POST /api/v1/plan/{plan_id}/review`: Submit a review decision (`approve`, `reject`, or `modify`).
*   `GET /api/v1/plan/{plan_id}/final`: View the finalized itinerary (only available after approval).

## Testing & Validation

Run the 97-test automated suite (includes HITL genuineness verification):
```bash
pytest
```

---

## 🛡️ Security and Production Review

This section outlines how production concerns are addressed in this take-home assignment, distinguishing between what is built today vs. what would be required for a Day-1 production launch.

### What is Implemented Now

*   **Secret Management**: All API keys are injected exclusively via environment variables (`pydantic-settings` `SecretStr`). Keys are never hardcoded.
*   **API Key Protection (Logging)**: A custom `SanitizingFilter` actively strips API keys, secrets, and bearer tokens from all log output.
*   **Input Validation & Request Size**: Pydantic schemas enforce strict field constraints (`min_length`, `max_length`, `gt=0`, etc.). A middleware cap (`100KB`) rejects oversized HTTP bodies with `413`. `RequestValidationError` is intercepted and sanitized so stack traces never leak to the client.
*   **Prompt Injection Guard**: The Research Agent system prompt explicitly marks web search snippets as **untrusted external data** and instructs the LLM to never follow instructions found inside search results.
*   **Structured Output Validation & LLM Failures**: `with_structured_output` is wrapped in an explicit retry loop. Parse errors are fed back to the LLM for self-correction before raising a graceful 500.
*   **External API Failures & Timeouts**: Serper (10s) and Weather (8s) tools use explicit HTTP timeouts. Auth errors (401/403), timeouts, and network errors degrade gracefully to a warning string passed to the LLM.
*   **CORS**: Configured narrowly to `localhost` by default. Override via `CORS_ORIGINS` env var in production.
*   **State Persistence**: Environment-aware checkpointer (`MemorySaver` → `SqliteSaver` → `AsyncPostgresSaver`).

### Tradeoffs / What I Would Implement in Production

If launching this system to production, I would address the following architectural gaps:

*   **Rate Limiting & Cost Controls**: 
    *   *Gap:* Currently, anyone can spam `POST /plan` and drain the OpenAI credits. 
    *   *Fix:* Add Redis-backed rate limiting (e.g., `slowapi`) at the FastAPI layer, restricting users to 5 requests per day. Add hard token usage caps via LangChain callbacks to abort runaway generation.
*   **PostgreSQL Migration Path**:
    *   *Gap:* The repository uses SQLite by default. 
    *   *Fix:* Deploy an Amazon RDS instance and pass the `DATABASE_URL` environment variable. LangGraph handles the raw state JSON, but we would also replace the in-memory `PlanRepository` dict with a dedicated SQLAlchemy asynchronous table (`plans`) for horizontal scaling.
*   **Multi-Worker Deployment & Concurrency**:
    *   *Gap:* `asyncio.create_task()` runs the LangGraph thread in the same process as the web server. If Uvicorn restarts, the task dies. 
    *   *Fix:* Move the graph execution to a dedicated distributed task queue (e.g., Celery + Redis or Temporal). The API simply queues the job, and background workers pick it up.
*   **Prompt Injection Considerations (Web Search)**:
    *   *Gap:* The web search tool reads raw snippets from the internet which are fed directly into the planner context. 
    *   *Fix:* Sanitize tool outputs by running a lightweight classification model or strict regex stripping over search snippets to prevent external web content from issuing "ignore previous instructions" commands to the Planner Agent.
*   **Authentication & Authorization**:
    *   *Gap:* No user concept. Any user knowing a `plan_id` can hit `POST /review`.
    *   *Fix:* Implement OAuth2 (JWT). `plan_id` ownership must be tied to a `user_id` inside the `PlanRepository`, and endpoints must verify ownership before exposing draft itineraries.
*   **Observability**:
    *   *Gap:* Local file logging is insufficient for distributed debugging.
    *   *Fix:* Wire up LangSmith (supported natively by setting `LANGCHAIN_TRACING_V2=true`) for tracing LLM latencies, and export FastAPI metrics to Prometheus/Grafana.
*   **Caching & Idempotency**:
    *   *Gap:* Identical travel requests (e.g., "Paris next week") will incur duplicate LLM and search costs. 
    *   *Fix:* Add semantic caching (e.g., Redis + embeddings) for research data, and generate an idempotency key upon request to prevent duplicate submissions from network retries.


