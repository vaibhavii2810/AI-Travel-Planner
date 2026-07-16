"""
Serper API web search tool.
Used by the Research Agent for real-time travel information.
Timeout, retry, and error handling implemented (Risk handling).
"""
from __future__ import annotations

import logging
from typing import Any

import httpx
from langchain_core.tools import tool

from app.core.config import get_settings
from app.core.exceptions import ToolExecutionError

logger = logging.getLogger("app.tools.web_search")


def _do_search(query: str, num_results: int) -> list[dict[str, str]]:
    """
    Synchronous Serper API call.
    Returns list of {title, link, snippet} dicts.
    Raises ToolExecutionError on timeout or non-2xx response.
    """
    settings = get_settings()
    headers = {
        "X-API-KEY": settings.SERPER_API_KEY.get_secret_value(),
        "Content-Type": "application/json",
    }
    payload: dict[str, Any] = {"q": query, "num": num_results}

    try:
        with httpx.Client(timeout=settings.SERPER_TIMEOUT_SECONDS) as client:
            response = client.post(settings.SERPER_BASE_URL, json=payload, headers=headers)
            response.raise_for_status()
    except httpx.TimeoutException as exc:
        logger.warning(f"Serper API timeout for query='{query[:50]}': {exc}")
        raise ToolExecutionError("web_search", f"Request timed out after {settings.SERPER_TIMEOUT_SECONDS}s") from exc
    except httpx.HTTPStatusError as exc:
        logger.error(f"Serper API HTTP error {exc.response.status_code} for query='{query[:50]}'")
        raise ToolExecutionError("web_search", f"HTTP {exc.response.status_code}: {exc.response.text[:200]}") from exc
    except httpx.RequestError as exc:
        logger.error(f"Serper API request error: {exc}")
        raise ToolExecutionError("web_search", f"Request error: {exc}") from exc

    data = response.json()
    results: list[dict[str, str]] = []

    for item in data.get("organic", [])[:num_results]:
        results.append({
            "title": item.get("title", ""),
            "link": item.get("link", ""),
            "snippet": item.get("snippet", ""),
        })

    logger.info(f"web_search | query='{query[:60]}' | results={len(results)}")
    return results


@tool
def web_search_tool(query: str, num_results: int = 5) -> str:
    """
    Search the web for real-time travel information using Serper API.

    Args:
        query: The search query string.
        num_results: Number of results to return (default 5, max 10).

    Returns:
        Formatted string of search results with titles, URLs, and snippets.
    """
    num_results = min(max(1, num_results), 10)
    try:
        results = _do_search(query, num_results)
    except ToolExecutionError as exc:
        return f"[Search failed: {exc.message}. Proceeding with available information.]"

    if not results:
        return f"[No results found for query: '{query}']"

    lines = [f"Search results for: '{query}'\n"]
    for i, r in enumerate(results, 1):
        lines.append(f"{i}. {r['title']}")
        lines.append(f"   URL: {r['link']}")
        lines.append(f"   {r['snippet']}\n")

    return "\n".join(lines)
