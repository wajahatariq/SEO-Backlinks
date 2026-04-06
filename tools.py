"""
tools.py — Web intelligence helpers powered by Tavily.

Environment variables required:
  TAVILY_API_KEY
"""

import os
from typing import Any

from tavily import TavilyClient
from dotenv import load_dotenv

load_dotenv()


def _client() -> TavilyClient:
    key = os.environ.get("TAVILY_API_KEY")
    if not key:
        raise EnvironmentError("TAVILY_API_KEY must be set in the environment.")
    return TavilyClient(api_key=key)


def search_web(query: str, max_results: int = 5) -> list[dict[str, Any]]:
    """
    Run a real-time web search and return a list of result dicts.
    Each result has: title, url, content (snippet).
    """
    results = _client().search(query, max_results=max_results)
    return results.get("results", [])


def extract_website(url: str) -> str:
    """
    Extract and return the main text content from *url*.
    Returns an empty string if extraction fails.
    """
    try:
        result = _client().extract(urls=[url])
        pages = result.get("results", [])
        if pages:
            return pages[0].get("raw_content", "")[:3000]
    except Exception:
        pass
    return ""
