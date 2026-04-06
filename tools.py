"""
tools.py — DataForSEO API helpers.

All credentials are read from environment variables:
  DATAFORSEO_LOGIN
  DATAFORSEO_PASSWORD
"""

import os
from typing import Any

import httpx
from dotenv import load_dotenv

load_dotenv()

DATAFORSEO_BASE_URL = "https://api.dataforseo.com/v3"


def _get_auth() -> tuple[str, str]:
    """Return (login, password) from env vars. Raises if either is missing."""
    login = os.environ.get("DATAFORSEO_LOGIN")
    password = os.environ.get("DATAFORSEO_PASSWORD")
    if not login or not password:
        raise EnvironmentError(
            "DATAFORSEO_LOGIN and DATAFORSEO_PASSWORD must be set in the environment."
        )
    return login, password


def fetch_referring_domains(target: str, limit: int = 100) -> dict[str, Any]:
    """
    Query the DataForSEO Backlinks — Referring Domains endpoint for *target*.

    Args:
        target: The domain to analyse (e.g. "example.com").
        limit:  Max number of referring domains to return (default 100).

    Returns:
        The parsed JSON response from the DataForSEO API.

    Raises:
        EnvironmentError: If credentials are not configured.
        httpx.HTTPStatusError: On non-2xx responses.
    """
    auth = _get_auth()

    payload = [
        {
            "target": target,
            "limit": limit,
            "order_by": ["rank,desc"],
            "filters": [
                ["broken_pages", "=", 0],  # Only domains that aren't broken
            ],
        }
    ]

    with httpx.Client() as client:
        response = client.post(
            f"{DATAFORSEO_BASE_URL}/backlinks/referring_domains/live",
            auth=auth,  # httpx handles HTTP Basic Auth automatically
            json=payload,
            timeout=30.0,
        )
        response.raise_for_status()

    return response.json()
