#!/usr/bin/env python3
"""
Phase 1 Smoke Test — End-to-end manual validation.

Prerequisites:
  1. Fill in .env with real API keys (OPENAI_API_KEY, SERPER_API_KEY, WEATHER_API_KEY)
  2. Run: uvicorn app.main:app --reload  (in a separate terminal)
  3. Run: python scripts/smoke_test.py

This script walks through the full workflow:
  POST /plan → poll until awaiting_review → POST /review (approve) → GET /final
"""
from __future__ import annotations

import sys
import time

import httpx

BASE_URL = "http://127.0.0.1:8000/api/v1"
POLL_INTERVAL_SECONDS = 10
MAX_POLL_ATTEMPTS = 60  # 10 minutes maximum wait

TRAVEL_REQUEST = {
    "destination": "Kyoto, Japan",
    "start_date": "2025-10-10",
    "end_date": "2025-10-15",
    "budget_min": 2000,
    "budget_max": 3500,
    "budget_currency": "USD",
    "interests": ["temples", "food", "culture"],
    "num_travelers": 2,
}


def log(msg: str) -> None:
    print(f"[smoke_test] {msg}", flush=True)


def check_health(client: httpx.Client) -> None:
    log("Checking server health...")
    resp = client.get(f"{BASE_URL}/health")
    resp.raise_for_status()
    data = resp.json()
    assert data["status"] == "healthy", f"Health check failed: {data}"
    log(f"  ✓ Server healthy | checkpointer={data['checkpointer']} | env={data['environment']}")


def create_plan(client: httpx.Client) -> str:
    log(f"Creating travel plan for: {TRAVEL_REQUEST['destination']}...")
    resp = client.post(f"{BASE_URL}/plan", json=TRAVEL_REQUEST)
    if resp.status_code not in (201, 202):
        log(f"  ✗ Create failed: {resp.status_code} {resp.text}")
        sys.exit(1)
    plan_id = resp.json()["plan_id"]
    log(f"  ✓ Plan created | plan_id={plan_id}")
    return plan_id


def poll_until_ready(client: httpx.Client, plan_id: str) -> dict:
    log(f"Polling plan status (up to {MAX_POLL_ATTEMPTS * POLL_INTERVAL_SECONDS}s)...")
    for attempt in range(MAX_POLL_ATTEMPTS):
        resp = client.get(f"{BASE_URL}/plan/{plan_id}")
        resp.raise_for_status()
        data = resp.json()
        status = data["status"]
        log(f"  [attempt {attempt+1}/{MAX_POLL_ATTEMPTS}] status={status}")

        if status == "awaiting_review":
            log("  ✓ Draft itinerary ready for review!")
            return data
        elif status in ("error", "max_revisions_exceeded"):
            log(f"  ✗ Plan failed with status={status} | error={data.get('error_message')}")
            sys.exit(1)
        elif status == "finalized":
            log("  ✓ Plan already finalized (unexpected at this stage)")
            return data

        time.sleep(POLL_INTERVAL_SECONDS)

    log(f"  ✗ Timeout: plan did not reach 'awaiting_review' after {MAX_POLL_ATTEMPTS} polls")
    sys.exit(1)


def print_draft_summary(data: dict) -> None:
    draft = data.get("draft_itinerary")
    if not draft:
        log("  (no draft itinerary in response)")
        return
    days = len(draft.get("daily_plans", []))
    budget = draft.get("budget_allocation", {})
    log(f"  Draft summary: {days} days | total=${budget.get('grand_total', 'N/A')} {budget.get('currency', '')}")
    log(f"  Revision version: {draft.get('version', 1)}")


def approve_plan(client: httpx.Client, plan_id: str) -> None:
    log(f"Submitting APPROVE decision for plan_id={plan_id}...")
    review_payload = {"action": "approve"}
    resp = client.post(f"{BASE_URL}/plan/{plan_id}/review", json=review_payload)
    if resp.status_code != 200:
        log(f"  ✗ Review failed: {resp.status_code} {resp.text}")
        sys.exit(1)
    log(f"  ✓ Approval submitted | {resp.json().get('message')}")


def get_final_plan(client: httpx.Client, plan_id: str) -> None:
    log(f"Fetching finalized plan for plan_id={plan_id}...")
    # Poll until finalized
    for attempt in range(10):
        resp = client.get(f"{BASE_URL}/plan/{plan_id}/final")
        if resp.status_code == 200:
            data = resp.json()
            final = data.get("final_itinerary", {})
            days = len(final.get("daily_plans", []))
            log(f"  ✓ Final plan retrieved! Days: {days} | approved_at={data.get('approved_at')}")
            return
        elif resp.status_code == 409:
            log(f"  [attempt {attempt+1}/10] Still finalizing... waiting {POLL_INTERVAL_SECONDS}s")
            time.sleep(POLL_INTERVAL_SECONDS)
        else:
            log(f"  ✗ Unexpected status {resp.status_code}: {resp.text}")
            sys.exit(1)
    log("  ✗ Timeout waiting for finalized plan")
    sys.exit(1)


def main() -> None:
    print("=" * 60)
    print("  AI Travel Planner — Phase 1 Smoke Test")
    print("=" * 60)

    with httpx.Client(timeout=30) as client:
        try:
            check_health(client)
        except Exception as e:
            log(f"✗ Server not running or not healthy: {e}")
            log("  Start the server first: uvicorn app.main:app --reload")
            sys.exit(1)

        plan_id = create_plan(client)
        status_data = poll_until_ready(client, plan_id)
        print_draft_summary(status_data)
        approve_plan(client, plan_id)
        get_final_plan(client, plan_id)

    print()
    print("=" * 60)
    print("  ✅ SMOKE TEST PASSED — Phase 1 is fully operational!")
    print("=" * 60)


if __name__ == "__main__":
    main()
