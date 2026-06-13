"""
EuroGoal Predictor — Understat xG Scraper
==========================================

Asynchronously fetches match-level expected-goals (xG) data from
`understat.com <https://understat.com>`_.

Understat now loads data via an AJAX endpoint at
``/getLeagueData/{league}/{season}`` which returns JSON with
``dates``, ``teams``, and ``players`` keys.

Usage::

    from app.services.scraper import UnderstatScraper

    async with UnderstatScraper() as scraper:
        matches = await scraper.fetch_league_matches("EPL", "2024")
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Optional

import httpx

from app.config import UNDERSTAT_REQUEST_DELAY

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_UNDERSTAT_BASE_URL = "https://understat.com"


class UnderstatScraper:
    """Async scraper for Understat xG data.

    Parameters
    ----------
    request_delay : float, optional
        Minimum seconds to wait between consecutive HTTP requests.
        Defaults to ``app.config.UNDERSTAT_REQUEST_DELAY``.

    Notes
    -----
    Use as an async context manager to ensure the underlying
    ``httpx.AsyncClient`` is properly closed::

        async with UnderstatScraper() as scraper:
            data = await scraper.fetch_league_matches("EPL", "2024")
    """

    def __init__(self, request_delay: float = UNDERSTAT_REQUEST_DELAY) -> None:
        self._delay = request_delay
        self._client: Optional[httpx.AsyncClient] = None
        self._last_request_time: float = 0.0

    # ------------------------------------------------------------------
    # Async context manager
    # ------------------------------------------------------------------

    async def __aenter__(self) -> "UnderstatScraper":
        self._client = httpx.AsyncClient(
            headers={
                "User-Agent": "EuroGoalPredictor/3.0",
                "Referer": "https://understat.com/",
                "X-Requested-With": "XMLHttpRequest",
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
    # Rate limiting
    # ------------------------------------------------------------------

    async def _throttle(self) -> None:
        """Enforce the minimum delay between consecutive HTTP requests."""
        now = asyncio.get_event_loop().time()
        elapsed = now - self._last_request_time
        if elapsed < self._delay:
            await asyncio.sleep(self._delay - elapsed)
        self._last_request_time = asyncio.get_event_loop().time()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _fetch_json(self, url: str) -> Any:
        """GET *url* and return the parsed JSON response.

        Raises
        ------
        httpx.HTTPStatusError
            If the response status code indicates an error (4xx / 5xx).
        RuntimeError
            If the scraper is used outside of an async context manager.
        """
        if self._client is None:
            raise RuntimeError(
                "UnderstatScraper must be used as an async context manager "
                "(async with UnderstatScraper() as scraper: ...)"
            )
        await self._throttle()
        logger.debug("Fetching %s", url)
        response = await self._client.get(url)
        response.raise_for_status()
        return response.json()

    @staticmethod
    def _normalize_match(raw: dict[str, Any]) -> dict[str, Any]:
        """Convert a raw Understat match dict into the canonical schema.

        Parameters
        ----------
        raw : dict
            A single match entry from the Understat API ``dates`` array.

        Returns
        -------
        dict
            Normalised match with keys: ``home_team``, ``away_team``,
            ``home_goals``, ``away_goals``, ``home_xg``, ``away_xg``,
            ``date``, ``result``.
        """
        h = raw.get("h", {})
        a = raw.get("a", {})
        goals = raw.get("goals", {})
        xg = raw.get("xG", {})

        return {
            "home_team": h.get("title", "") if isinstance(h, dict) else str(h),
            "away_team": a.get("title", "") if isinstance(a, dict) else str(a),
            "home_goals": int(goals.get("h", 0)) if isinstance(goals, dict) else 0,
            "away_goals": int(goals.get("a", 0)) if isinstance(goals, dict) else 0,
            "home_xg": float(xg.get("h", 0.0)) if isinstance(xg, dict) else 0.0,
            "away_xg": float(xg.get("a", 0.0)) if isinstance(xg, dict) else 0.0,
            "date": raw.get("datetime", ""),
            "result": raw.get("forecast", {}).get("w", ""),
        }

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def fetch_league_matches(
        self, league: str, season: str
    ) -> list[dict[str, Any]]:
        """Fetch all match xG data for a league and season from Understat.

        Parameters
        ----------
        league : str
            Understat league identifier.  Must be one of: ``EPL``,
            ``La_liga``, ``Bundesliga``, ``Serie_A``, ``Ligue_1``.
        season : str
            The *starting year* of the season, e.g. ``"2024"`` for the
            2024/25 campaign.

        Returns
        -------
        list[dict]
            Normalised match dicts.  Each dict contains:

            - ``home_team`` (str)
            - ``away_team`` (str)
            - ``home_goals`` (int)
            - ``away_goals`` (int)
            - ``home_xg`` (float)
            - ``away_xg`` (float)
            - ``date`` (str) — ISO-formatted date/time
            - ``result`` (str)

        Raises
        ------
        httpx.HTTPStatusError
            On non-2xx responses.
        """
        url = f"{_UNDERSTAT_BASE_URL}/getLeagueData/{league}/{season}"
        logger.info("Fetching Understat data: %s", url)

        data = await self._fetch_json(url)
        raw_matches = data.get("dates", [])

        normalised = [self._normalize_match(m) for m in raw_matches]
        logger.info(
            "Fetched %d matches for %s %s", len(normalised), league, season
        )
        return normalised
