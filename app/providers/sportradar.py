"""Thin authenticated HTTP transport for Sportradar Odds Comparison v2.

Feed paths are deliberately supplied by the integration layer so endpoint
selection follows the current official package documentation and entitlements.
This transport does not claim that any feed is enabled for a given API key.
"""
import os
from typing import Any

import httpx


class SportradarOddsClient:
    def __init__(self, base_url: str, api_key: str | None = None, timeout: float = 20.0):
        key = api_key or os.getenv("SPORTRADAR_ODDS_API_KEY")
        if not key:
            raise RuntimeError("SPORTRADAR_ODDS_API_KEY is not configured")
        self._base_url = base_url.rstrip("/")
        self._client = httpx.AsyncClient(
            base_url=self._base_url,
            headers={"x-api-key": key, "accept": "application/json"},
            timeout=timeout,
        )

    async def get_feed(self, feed_path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        """Fetch one documented feed path; never log or expose the API key."""
        if feed_path.startswith(("http://", "https://")) or ".." in feed_path.split("/"):
            raise ValueError("feed_path must be a relative path under the configured API base URL")
        response = await self._client.get(feed_path.lstrip("/"), params=params)
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, dict):
            raise ValueError("Expected a JSON object from the odds provider")
        return payload

    async def close(self) -> None:
        await self._client.aclose()
