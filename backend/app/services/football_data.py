"""
EuroGoal Predictor — Football-Data.org API Client
==================================================

Async wrapper around the `football-data.org v4 REST API
<https://www.football-data.org/documentation/api>`_.

Features:
  • Token-based authentication via ``X-Auth-Token`` header.
  • Token-bucket rate limiter (defaults to 10 req/min on the free tier).
  • Response normalisation into consistent flat dicts.

Usage::

    from app.services.football_data import FootballDataClient

    async with FootballDataClient() as client:
        matches = await client.get_matches("PL", season="2024")
        standings = await client.get_standings("PL")
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

import httpx

from app.config import (
    FOOTBALL_DATA_API_KEY,
    FOOTBALL_DATA_BASE_URL,
    FOOTBALL_DATA_RATE_LIMIT,
)

logger = logging.getLogger(__name__)


class _RateLimiter:
    """Simple token-bucket rate limiter.

    Allows at most *max_requests* calls in a rolling window of
    *period_seconds* seconds.  When the limit is reached, callers
    are blocked until a slot becomes available.

    Parameters
    ----------
    max_requests : int
        Maximum number of requests allowed per period.
    period_seconds : float
        Length of the rolling window in seconds.
    """

    def __init__(self, max_requests: int, period_seconds: float = 60.0) -> None:
        self._max = max_requests
        self._period = period_seconds
        self._timestamps: list[float] = []
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        """Wait until a request slot is available, then consume it."""
        async with self._lock:
            now = asyncio.get_event_loop().time()
            # Drop timestamps outside the rolling window.
            self._timestamps = [
                t for t in self._timestamps if now - t < self._period
            ]
            if len(self._timestamps) >= self._max:
                # Wait until the oldest timestamp leaves the window.
                sleep_for = self._period - (now - self._timestamps[0])
                logger.debug("Rate limit reached; sleeping %.1fs", sleep_for)
                await asyncio.sleep(sleep_for)
                # Refresh after sleeping.
                now = asyncio.get_event_loop().time()
                self._timestamps = [
                    t for t in self._timestamps if now - t < self._period
                ]
            self._timestamps.append(asyncio.get_event_loop().time())


class FootballDataClient:
    """Async client for the football-data.org REST API (v4).

    Parameters
    ----------
    api_key : str, optional
        Your football-data.org API token.  Defaults to the value of
        ``app.config.FOOTBALL_DATA_API_KEY``.
    base_url : str, optional
        API base URL.  Override for testing.
    rate_limit : int, optional
        Max requests per minute.  Defaults to
        ``app.config.FOOTBALL_DATA_RATE_LIMIT``.
    """

    def __init__(
        self,
        api_key: str = FOOTBALL_DATA_API_KEY,
        base_url: str = FOOTBALL_DATA_BASE_URL,
        rate_limit: int = FOOTBALL_DATA_RATE_LIMIT,
    ) -> None:
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._limiter = _RateLimiter(max_requests=rate_limit, period_seconds=60.0)
        self._client: Optional[httpx.AsyncClient] = None

    # ------------------------------------------------------------------
    # Async context manager
    # ------------------------------------------------------------------

    async def __aenter__(self) -> "FootballDataClient":
        self._client = httpx.AsyncClient(
            base_url=self._base_url,
            headers={
                "X-Auth-Token": self._api_key,
                "Accept": "application/json",
            },
            follow_redirects=True,
            timeout=30.0,
        )
        return self

    async def __aexit__(self, *exc: Any) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _get(self, endpoint: str, params: Optional[dict] = None) -> Any:
        """Perform a rate-limited GET request.

        Parameters
        ----------
        endpoint : str
            Path relative to the base URL (e.g.
            ``"/competitions/PL/matches"``).
        params : dict, optional
            Query string parameters.

        Returns
        -------
        Any
            Parsed JSON response body.

        Raises
        ------
        RuntimeError
            If the client is used outside of an async context manager.
        httpx.HTTPStatusError
            On non-2xx responses.
        """
        if self._client is None:
            raise RuntimeError(
                "FootballDataClient must be used as an async context manager "
                "(async with FootballDataClient() as client: ...)"
            )
        await self._limiter.acquire()
        logger.debug("GET %s %s", endpoint, params or "")
        response = await self._client.get(endpoint, params=params)
        response.raise_for_status()
        return response.json()

    # ------------------------------------------------------------------
    # Response normalisers
    # ------------------------------------------------------------------

    @staticmethod
    def _normalize_match(raw: dict[str, Any]) -> dict[str, Any]:
        """Flatten a football-data.org match object into a clean dict.

        The raw API nests teams, scores, etc.  We flatten everything so
        downstream consumers have a simple, consistent schema.
        """
        score = raw.get("score", {})
        full_time = score.get("fullTime", {})
        home = raw.get("homeTeam") or {}
        away = raw.get("awayTeam") or {}
        group = raw.get("group")

        return {
            "fd_id": raw.get("id"),
            "competition": raw.get("competition", {}).get("code", ""),
            "season": str(
                raw.get("season", {}).get("startDate", "")[:4]
            ),
            "matchday": raw.get("matchday"),
            "date": raw.get("utcDate", ""),
            # name is None for knockout fixtures whose teams are still TBD
            "home_team": home.get("name"),
            "away_team": away.get("name"),
            "home_goals": full_time.get("home"),
            "away_goals": full_time.get("away"),
            "status": raw.get("status", "SCHEDULED"),
            # tournament context (None / "REGULAR_SEASON" for leagues)
            "stage": raw.get("stage"),
            "group": group.replace("GROUP_", "") if group else None,
            "winner": score.get("winner"),   # HOME_TEAM / AWAY_TEAM / DRAW / None
        }

    @staticmethod
    def _normalize_standing(raw: dict[str, Any]) -> dict[str, Any]:
        """Flatten a single standings-table entry."""
        return {
            "position": raw.get("position"),
            "team": raw.get("team", {}).get("name", ""),
            "team_id": raw.get("team", {}).get("id"),
            "played": raw.get("playedGames"),
            "won": raw.get("won"),
            "draw": raw.get("draw"),
            "lost": raw.get("lost"),
            "goals_for": raw.get("goalsFor"),
            "goals_against": raw.get("goalsAgainst"),
            "goal_difference": raw.get("goalDifference"),
            "points": raw.get("points"),
        }

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def get_matches(
        self,
        competition: str,
        season: Optional[str] = None,
        status: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        """Fetch matches for a competition.

        Parameters
        ----------
        competition : str
            Competition code, e.g. ``"PL"``, ``"BL1"``.
        season : str, optional
            Starting year of the season (e.g. ``"2024"``).
            If omitted, the API returns the current season.
        status : str, optional
            Filter by match status: ``"SCHEDULED"``, ``"FINISHED"``,
            ``"LIVE"``, ``"IN_PLAY"``, ``"PAUSED"``, ``"POSTPONED"``,
            ``"CANCELLED"``, ``"SUSPENDED"``, ``"AWARDED"``.

        Returns
        -------
        list[dict]
            Normalised match dicts.
        """
        params: dict[str, str] = {}
        if season is not None:
            params["season"] = season
        if status is not None:
            params["status"] = status

        data = await self._get(
            f"/competitions/{competition}/matches", params=params or None
        )
        raw_matches = data.get("matches", [])
        normalised = [self._normalize_match(m) for m in raw_matches]
        logger.info(
            "Fetched %d matches for %s (season=%s, status=%s)",
            len(normalised),
            competition,
            season,
            status,
        )
        return normalised

    async def get_world_cup_matches(self) -> list[dict[str, Any]]:
        """Fetch ALL FIFA World Cup matches (group + knockout), normalised.

        Unlike :meth:`get_matches`, this applies no status filter so the
        caller receives finished results and scheduled fixtures together,
        each carrying ``stage``, ``group`` and ``winner``.
        """
        data = await self._get("/competitions/WC/matches")
        raw_matches = data.get("matches", [])
        normalised = [self._normalize_match(m) for m in raw_matches]
        logger.info("Fetched %d FIFA World Cup matches", len(normalised))
        return normalised

    async def get_standings(
        self, competition: str
    ) -> list[dict[str, Any]]:
        """Fetch current league standings.

        Parameters
        ----------
        competition : str
            Competition code.

        Returns
        -------
        list[dict]
            Normalised standing entries for the ``TOTAL`` table.
        """
        data = await self._get(f"/competitions/{competition}/standings")
        standings_groups = data.get("standings", [])

        # We want the overall ("TOTAL") table.
        for group in standings_groups:
            if group.get("type") == "TOTAL":
                table = group.get("table", [])
                normalised = [self._normalize_standing(row) for row in table]
                logger.info(
                    "Fetched standings for %s (%d teams)",
                    competition,
                    len(normalised),
                )
                return normalised

        # Fallback: return the first group's table.
        if standings_groups:
            table = standings_groups[0].get("table", [])
            return [self._normalize_standing(row) for row in table]

        return []

    async def get_upcoming_matches(
        self, competition: str, days: int = 7
    ) -> list[dict[str, Any]]:
        """Fetch matches scheduled in the next *days* days.

        Parameters
        ----------
        competition : str
            Competition code.
        days : int
            Look-ahead window in days (default 7).

        Returns
        -------
        list[dict]
            Normalised upcoming match dicts.
        """
        now = datetime.now(timezone.utc)
        date_from = now.strftime("%Y-%m-%d")
        date_to = (now + timedelta(days=days)).strftime("%Y-%m-%d")

        params: dict[str, str] = {
            "dateFrom": date_from,
            "dateTo": date_to,
            "status": "SCHEDULED",
        }
        data = await self._get(
            f"/competitions/{competition}/matches", params=params
        )
        raw_matches = data.get("matches", [])
        normalised = [self._normalize_match(m) for m in raw_matches]
        logger.info(
            "Fetched %d upcoming matches for %s (next %d days)",
            len(normalised),
            competition,
            days,
        )
        return normalised
