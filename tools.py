"""
tools.py — Backlink data helpers using RapidAPI (SEO API - Get Backlinks).

Credentials read from environment variables:
  RAPIDAPI_KEY
"""

import os
from typing import Any

import httpx
from dotenv import load_dotenv

load_dotenv()

_RAPIDAPI_HOST = "seo-api-get-backlinks.p.rapidapi.com"
_BASE_URL = f"https://{_RAPIDAPI_HOST}"


def _get_headers() -> dict[str, str]:
    key = os.environ.get("RAPIDAPI_KEY")
    if not key:
        raise EnvironmentError("RAPIDAPI_KEY must be set in the environment.")
    return {
        "x-rapidapi-key": key,
        "x-rapidapi-host": _RAPIDAPI_HOST,
    }


def fetch_backlink_summary(domain: str) -> dict[str, Any]:
    """
    Fetch backlink summary stats for *domain* via RapidAPI.

    Returns a dict with keys:
      - domain        : the queried domain
      - da            : domain authority (latest)
      - ref_domains   : number of referring domains (latest)
      - total_backlinks: total backlink count (latest)
      - top_anchors   : list of top anchor text objects
      - monthly_trend : last 6 months of backlink/refdomain counts

    Raises:
      EnvironmentError: if RAPIDAPI_KEY is not set.
      httpx.HTTPStatusError: on non-2xx responses.
    """
    with httpx.Client(timeout=20.0) as client:
        response = client.get(
            f"{_BASE_URL}/backlinks.php",
            headers=_get_headers(),
            params={"domain": domain},
        )
        response.raise_for_status()

    data = response.json()
    overtime = data.get("overtime", [])
    latest = overtime[0] if overtime else {}

    return {
        "domain": domain,
        "da": latest.get("da", 0),
        "ref_domains": latest.get("refdomains", 0),
        "total_backlinks": latest.get("backlinks", 0),
        "top_anchors": data.get("anchors", [])[:10],
        "monthly_trend": overtime[:6],
    }
