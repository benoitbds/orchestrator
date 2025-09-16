"""Utilities for retrieving external information for user queries."""
from __future__ import annotations

import logging
from typing import Final
from urllib.parse import quote

import httpx

logger = logging.getLogger(__name__)

_WIKIPEDIA_SUMMARY_URL: Final[str] = (
    "https://en.wikipedia.org/api/rest_v1/page/summary/{}"
)
_MAX_SUMMARY_LENGTH: Final[int] = 1000


def retrieve_external_info(query: str, *, timeout: float = 5.0) -> str:
    """Return a short summary for *query* using the Wikipedia API.

    Args:
        query: Topic or phrase to look up.
        timeout: Maximum seconds to wait for the HTTP request.

    Returns:
        A summary string when available, or an empty string if nothing relevant
        is found or the lookup fails.

    Raises:
        ValueError: If *query* is not a non-empty string or timeout is invalid.
    """

    if not isinstance(query, str):
        raise ValueError("query must be a non-empty string")

    normalised_query = query.strip()
    if not normalised_query:
        raise ValueError("query must be a non-empty string")

    if not isinstance(timeout, (int, float)) or timeout <= 0:
        raise ValueError("timeout must be a positive number")

    encoded_query = quote(normalised_query, safe="")
    url = _WIKIPEDIA_SUMMARY_URL.format(encoded_query)

    try:
        response = httpx.get(url, timeout=timeout)
        response.raise_for_status()
    except httpx.HTTPStatusError:
        logger.debug("No summary available for query '%s'", normalised_query)
        return ""
    except httpx.RequestError as exc:
        logger.warning("Failed to retrieve external info: %s", exc)
        return ""

    try:
        data = response.json()
    except ValueError:
        logger.warning(
            "Wikipedia response could not be decoded as JSON for query '%s'",
            normalised_query,
        )
        return ""

    extract = data.get("extract") if isinstance(data, dict) else None
    if not isinstance(extract, str):
        return ""

    if len(extract) > _MAX_SUMMARY_LENGTH:
        return extract[:_MAX_SUMMARY_LENGTH]

    return extract
