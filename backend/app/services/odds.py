"""
EuroGoal Predictor — The Odds API Client
=========================================
Fetches betting odds from the-odds-api.com for value bet detection.

Free tier: 500 requests/month.
API key passed as query parameter per the-odds-api.com documentation.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Optional

import httpx

from app.config import (
    THE_ODDS_API_KEY,
    THE_ODDS_API_BASE_URL,
    THE_ODDS_API_RATE_LIMIT,
)

logger = logging.getLogger(__name__)


class _RateLimiter:
    """Simple token-bucket rate limiter (same pattern as FootballDataClient)."""

    def __init__(self, max_requests: int, period_seconds: float = 60.0) -> None:
        self._max = max_requests
        self._period = period_seconds
        self._timestamps: list[float] = []
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        async with self._lock:
            now = asyncio.get_event_loop().time()
            self._timestamps = [
                t for t in self._timestamps if now - t < self._period
            ]
            if len(self._timestamps) >= self._max:
                sleep_for = self._period - (now - self._timestamps[0])
                logger.debug("Odds API rate limit reached; sleeping %.1fs", sleep_for)
                await asyncio.sleep(sleep_for)
                now = asyncio.get_event_loop().time()
                self._timestamps = [
                    t for t in self._timestamps if now - t < self._period
                ]
            self._timestamps.append(asyncio.get_event_loop().time())


class OddsService:
    """Async client for The Odds API (the-odds-api.com).

    Parameters
    ----------
    api_key : str
        Defaults to THE_ODDS_API_KEY from config.
    base_url : str
        Defaults to THE_ODDS_API_BASE_URL.
    rate_limit : int
        Defaults to THE_ODDS_API_RATE_LIMIT.
    """

    def __init__(
        self,
        api_key: str = THE_ODDS_API_KEY,
        base_url: str = THE_ODDS_API_BASE_URL,
        rate_limit: int = THE_ODDS_API_RATE_LIMIT,
    ) -> None:
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._limiter = _RateLimiter(max_requests=rate_limit, period_seconds=60.0)
        self._client: Optional[httpx.AsyncClient] = None

    async def __aenter__(self) -> "OddsService":
        self._client = httpx.AsyncClient(
            base_url=self._base_url,
            params={"apiKey": self._api_key},
            headers={"Accept": "application/json"},
            follow_redirects=True,
            timeout=30.0,
        )
        return self

    async def __aexit__(self, *exc: Any) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    async def _get(self, endpoint: str, params: Optional[dict] = None) -> Any:
        if self._client is None:
            raise RuntimeError("OddsService must be used as async context manager")
        await self._limiter.acquire()
        response = await self._client.get(endpoint, params=params)
        response.raise_for_status()
        return response.json()

    @staticmethod
    def _normalize_odds(raw_event: dict[str, Any]) -> list[dict[str, Any]]:
        """Flatten one event's bookmaker odds into a flat list of dicts."""
        home_team = raw_event.get("home_team", "")
        away_team = raw_event.get("away_team", "")
        results = []

        for bookmaker in raw_event.get("bookmakers", []):
            bookmaker_name = bookmaker.get("key", "unknown")
            for market in bookmaker.get("markets", []):
                market_key = market.get("key", "")
                entry: dict[str, Any] = {
                    "home_team": home_team,
                    "away_team": away_team,
                    "bookmaker": bookmaker_name,
                    "market": market_key,
                    "home_odds": None,
                    "draw_odds": None,
                    "away_odds": None,
                    "spread_home": None,
                    "spread_away": None,
                    "total_line": None,
                    "over_odds": None,
                    "under_odds": None,
                }
                for outcome in market.get("outcomes", []):
                    name = outcome.get("name", "")
                    price = outcome.get("price")
                    point = outcome.get("point")
                    if market_key == "h2h":
                        if name == home_team:
                            entry["home_odds"] = price
                        elif name == "Draw":
                            entry["draw_odds"] = price
                        elif name == away_team:
                            entry["away_odds"] = price
                    elif market_key == "spreads":
                        if name == home_team:
                            entry["spread_home"] = point
                            entry["home_odds"] = price
                        elif name == away_team:
                            entry["spread_away"] = point
                            entry["away_odds"] = price
                    elif market_key == "totals":
                        entry["total_line"] = point
                        if name == "Over":
                            entry["over_odds"] = price
                        elif name == "Under":
                            entry["under_odds"] = price
                results.append(entry)
        return results

    async def get_odds(
        self,
        sport_key: str,
        regions: str = "eu,uk",
        markets: str = "h2h,spreads,totals",
    ) -> list[dict[str, Any]]:
        """Fetch odds for all upcoming matches in a sport."""
        data = await self._get(
            f"/sports/{sport_key}/odds",
            params={"regions": regions, "markets": markets},
        )
        all_odds: list[dict[str, Any]] = []
        for event in data:
            all_odds.extend(self._normalize_odds(event))
        logger.info("Fetched %d odds entries for %s", len(all_odds), sport_key)
        return all_odds

    async def get_odds_for_match(
        self,
        sport_key: str,
        home_team: str,
        away_team: str,
    ) -> list[dict[str, Any]]:
        """Fetch odds and filter to a specific match using fuzzy name matching."""
        all_odds = await self.get_odds(sport_key)
        matched = []
        for entry in all_odds:
            if (
                self._fuzzy_match(home_team, entry["home_team"])
                and self._fuzzy_match(away_team, entry["away_team"])
            ):
                matched.append(entry)
        return matched

    @staticmethod
    def _normalize_name(name: str) -> str:
        """Normalize team name for fuzzy matching."""
        import re
        name = name.lower().strip()
        # Remove common suffixes
        for suffix in [" fc", " cf", " sc", " sk", " fk", " bc"]:
            if name.endswith(suffix):
                name = name[: -len(suffix)]
        # Remove hyphens, dots, and extra spaces
        name = re.sub(r"[-._]", " ", name)
        name = re.sub(r"\s+", " ", name).strip()
        return name

    @classmethod
    def _fuzzy_match(cls, our_name: str, api_name: str) -> bool:
        """Fuzzy team name matching with normalization."""
        a = cls._normalize_name(our_name)
        b = cls._normalize_name(api_name)
        return a in b or b in a

    @property
    def is_configured(self) -> bool:
        return bool(self._api_key)
