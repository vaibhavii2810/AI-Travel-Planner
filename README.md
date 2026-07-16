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
    *   `SERPER_API_KEY`: Required for web search tool (get it at serper.dev).
    *   `WEATHER_API_KEY`: Required for weather data (get it at openweathermap.org).

3.  **Run Locally (Dev Mode)**
    In `dev` mode, the app uses an SQLite checkpointer automatically.
    ```bash
    uvicorn app.main:app --reload
    ```

4.  **Run via Docker (Production Mode)**
    Docker Compose sets up the FastAPI app alongside a PostgreSQL database for persistent, production-grade checkpointing.
    ```bash
    docker-compose up --build
    ```

## API Endpoints

*   `POST /api/v1/plan`: Submit a travel request. Returns a `plan_id`.
*   `GET /api/v1/plan/{plan_id}`: Poll for status and view the draft itinerary when status is `awaiting_review`.
*   `POST /api/v1/plan/{plan_id}/review`: Submit a review decision (`approve`, `reject`, or `modify`).
*   `GET /api/v1/plan/{plan_id}/final`: View the finalized itinerary (only available after approval).

## Testing & Validation

### 1. Run Automated Test Suite
Unit and integration tests (including the HITL genuineness verification test) run asynchronously with `pytest`:
```bash
pytest
```
*(Configuration is defined in `pyproject.toml` with `asyncio_mode = "auto"`).*

### 2. Run End-to-End Smoke Test
To validate the entire path (`POST /plan` → poll → `POST /review` → `GET /final`) with real API calls:
1. Ensure your `.env` contains valid keys.
2. Start the FastAPI server:
   ```bash
   uvicorn app.main:app --reload
   ```
3. Run the smoke test script:
   ```bash
   python scripts/smoke_test.py
   ```

