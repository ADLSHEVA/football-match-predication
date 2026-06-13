"""
EuroGoal Predictor — API-Football H2H Client
=============================================
Fetches head-to-head historical data from api-football.com via RapidAPI.

Free tier: 100 requests/day.
Auth: x-apisports-key header.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

import httpx

from app.config import API_FOOTBALL_KEY, API_FOOTBALL_BASE_URL

logger = logging.getLogger(__name__)


class ApiFootballService:
    """Async client for API-Football (v3) via RapidAPI.

    Parameters
    ----------
    api_key : str
        Defaults to API_FOOTBALL_KEY from config.
    base_url : str
        Defaults to API_FOOTBALL_BASE_URL.
    """

    def __init__(
        self,
        api_key: str = API_FOOTBALL_KEY,
        base_url: str = API_FOOTBALL_BASE_URL,
    ) -> None:
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._client: Optional[httpx.AsyncClient] = None
        # In-memory cache for team ID resolution (avoids repeated API calls)
        self._team_id_cache: dict[str, Optional[int]] = {}

    async def __aenter__(self) -> "ApiFootballService":
        self._client = httpx.AsyncClient(
            base_url=self._base_url,
            headers={
                "x-apisports-key": self._api_key,
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

    async def _get(self, endpoint: str, params: Optional[dict] = None) -> Any:
        if self._client is None:
            raise RuntimeError("ApiFootballService must be used as async context manager")
        logger.debug("GET %s %s", endpoint, params or "")
        response = await self._client.get(endpoint, params=params)
        response.raise_for_status()
        return response.json()

    @staticmethod
    def _normalize_fixture(raw: dict[str, Any]) -> dict[str, Any]:
        """Flatten an API-Football fixture into a clean dict."""
        fixture = raw.get("fixture", {})
        teams = raw.get("teams", {})
        goals = raw.get("goals", {})
        league = raw.get("league", {})

        home = teams.get("home", {})
        away = teams.get("away", {})

        return {
            "date": fixture.get("date", ""),
            "home_team": home.get("name", ""),
            "away_team": away.get("name", ""),
            "home_goals": goals.get("home"),
            "away_goals": goals.get("away"),
            "league": league.get("name", ""),
        }

    async def get_h2h(
        self,
        home_team: str,
        away_team: str,
        last: int = 10,
    ) -> list[dict[str, Any]]:
        """Fetch head-to-head results between two teams.

        Parameters
        ----------
        home_team : str
            Team name (resolved to API-Football team ID).
        away_team : str
            Team name.
        last : int
            Number of previous H2H fixtures to return (default 10).

        Returns
        -------
        list[dict]
            Normalised fixture dicts sorted by date descending.
        """
        home_id = await self._resolve_team_id(home_team)
        away_id = await self._resolve_team_id(away_team)

        if not home_id or not away_id:
            logger.warning(
                "Could not resolve team IDs for H2H: %s vs %s",
                home_team, away_team,
            )
            return []

        data = await self._get(
            "/fixtures/headtohead",
            params={"h2h": f"{home_id}-{away_id}"},
        )

        raw_fixtures = data.get("response", [])
        normalized = [self._normalize_fixture(f) for f in raw_fixtures]
        normalized.sort(key=lambda x: x.get("date", ""), reverse=True)
        logger.info(
            "Fetched %d H2H results for %s vs %s",
            len(normalized), home_team, away_team,
        )
        return normalized

    # Common abbreviation → full name for API-Football search
    _TEAM_ALIASES: dict[str, str] = {
        "PSG": "Paris Saint Germain",
        "Man City": "Manchester City",
        "Man United": "Manchester United",
        "Man Utd": "Manchester United",
        "Spurs": "Tottenham",
        "Inter": "Inter Milan",
        "Juventus": "Juventus",
        "Atletico": "Atletico Madrid",
        "BVB": "Borussia Dortmund",
    }

    async def _resolve_team_id(self, team_name: str) -> Optional[int]:
        """Resolve a team name to its API-Football team ID.

        Uses in-memory cache to avoid redundant API calls.
        Tries the full name first, then strips common suffixes (FC, CF, etc.)
        if the initial search returns no results.
        """
        if team_name in self._team_id_cache:
            return self._team_id_cache[team_name]

        # Check aliases first
        search_variants = []
        if team_name in self._TEAM_ALIASES:
            search_variants.append(self._TEAM_ALIASES[team_name])

        search_variants.append(team_name)
        # Strip common suffixes like "FC", "CF", "SC", "SK", "FK", "BC"
        for suffix in [" FC", " CF", " SC", " SK", " FK", " BC", " AF"]:
            if team_name.upper().endswith(suffix):
                search_variants.append(team_name[: -len(suffix)].strip())
        # Also try without "AC", "AS", "SSC", "FC" prefixes for Italian/French
        cleaned = team_name
        for prefix in ["AC ", "AS ", "SSC ", "FC "]:
            if cleaned.upper().startswith(prefix):
                search_variants.append(cleaned[len(prefix) :].strip())

        for search_name in search_variants:
            try:
                data = await self._get("/teams", params={"search": search_name})
                responses = data.get("response", [])
                if responses:
                    team_info = responses[0].get("team", {})
                    team_id = team_info.get("id")
                    logger.info(
                        "Resolved '%s' (searched '%s') -> ID %d (%s)",
                        team_name, search_name, team_id, team_info.get("name", ""),
                    )
                    self._team_id_cache[team_name] = team_id
                    return team_id
            except Exception as e:
                logger.warning("Failed to resolve team ID for '%s': %s", search_name, e)
                break

        logger.warning("No team found for '%s' (tried: %s)", team_name, search_variants)
        self._team_id_cache[team_name] = None
        return None

    @property
    def is_configured(self) -> bool:
        return bool(self._api_key)

    # ------------------------------------------------------------------
    # Lineups & Fixtures
    # ------------------------------------------------------------------

    async def get_upcoming_fixture_id(
        self,
        home_team: str,
        away_team: str,
    ) -> Optional[int]:
        """Find the fixture ID for an upcoming match between two teams.

        Uses /fixtures?team={id}&next=10 to search multiple upcoming
        fixtures for the specific home/away pairing.
        """
        home_id = await self._resolve_team_id(home_team)
        away_id = await self._resolve_team_id(away_team)

        if not home_id or not away_id:
            logger.warning(
                "Could not resolve team IDs for fixture lookup: %s vs %s",
                home_team, away_team,
            )
            return None

        try:
            data = await self._get("/fixtures", params={"team": home_id, "next": 10})
            for fixture in data.get("response", []):
                teams = fixture.get("teams", {})
                home_info = teams.get("home", {})
                away_info = teams.get("away", {})
                # Check if this fixture matches the desired home/away pairing
                if home_info.get("id") == home_id and away_info.get("id") == away_id:
                    fixture_id = fixture.get("fixture", {}).get("id")
                    logger.info(
                        "Found fixture ID %d for %s vs %s",
                        fixture_id, home_team, away_team,
                    )
                    return fixture_id
        except Exception as e:
            logger.warning("Error fetching upcoming fixture: %s", e)

        logger.warning("No upcoming fixture found for %s vs %s", home_team, away_team)
        return None

    async def get_lineups(self, fixture_id: int) -> list[dict[str, Any]]:
        """Fetch lineup data for a specific fixture.

        Returns 0-2 team lineup objects (empty if lineups not yet announced).
        """
        data = await self._get("/fixtures/lineups", params={"fixture": fixture_id})
        response = data.get("response", [])
        logger.info("Fetched lineups for fixture %d: %d teams", fixture_id, len(response))
        return response

    @staticmethod
    def _normalize_lineup(raw: dict[str, Any]) -> dict[str, Any]:
        """Flatten an API-Football lineup object into a clean dict."""
        team = raw.get("team", {})
        coach = raw.get("coach", {})
        startxi = raw.get("startXI", [])

        players = []
        for entry in startxi:
            player = entry.get("player", {})
            players.append({
                "number": player.get("number"),
                "name": player.get("name", ""),
                "pos": player.get("pos", ""),
                "grid": player.get("grid"),
            })

        return {
            "team_id": team.get("id"),
            "team_name": team.get("name", ""),
            "team_logo": team.get("logo", ""),
            "formation": raw.get("formation", ""),
            "start_xi": players,
            "coach_name": coach.get("name", ""),
        }

    @staticmethod
    def _fuzzy_match_team(api_name: str, our_name: str) -> bool:
        """Check if two team names refer to the same team."""
        a = api_name.lower().strip()
        b = our_name.lower().strip()
        for suffix in [" fc", " cf", " sc", " sk", " fk"]:
            a = a.replace(suffix, "")
            b = b.replace(suffix, "")
        return a in b or b in a

    # ------------------------------------------------------------------
    # League fixtures & standings (used by the World Cup module)
    # ------------------------------------------------------------------

    async def get_fixtures(
        self,
        league_id: int,
        season: int,
    ) -> list[dict[str, Any]]:
        """Fetch all fixtures for a league/season, normalised.

        Each fixture is flattened to include the round label and status code
        (in addition to the usual teams/goals), which the World Cup module
        needs to tell group games from knockout games and finished from
        scheduled.
        """
        data = await self._get(
            "/fixtures", params={"league": league_id, "season": season}
        )
        fixtures: list[dict[str, Any]] = []
        for raw in data.get("response", []):
            flat = self._normalize_fixture(raw)
            league = raw.get("league", {})
            status = raw.get("fixture", {}).get("status", {})
            flat["round"] = league.get("round", "")
            flat["status"] = status.get("short", "")   # e.g. "FT", "NS"
            fixtures.append(flat)
        logger.info(
            "Fetched %d fixtures for league %d season %d",
            len(fixtures), league_id, season,
        )
        return fixtures

    async def get_standings(
        self,
        league_id: int,
        season: int,
    ) -> dict[str, list[str]]:
        """Fetch group standings → {group_label: [team_name, ...]} in order.

        Returns an empty dict if the provider has no standings yet (common
        before/at the very start of a tournament).
        """
        data = await self._get(
            "/standings", params={"league": league_id, "season": season}
        )
        response = data.get("response", [])
        if not response:
            return {}

        groups: dict[str, list[str]] = {}
        standings = response[0].get("league", {}).get("standings", [])
        for group_rows in standings:
            for row in group_rows:
                label = str(row.get("group", "")).replace("Group", "").strip()
                team_name = row.get("team", {}).get("name", "")
                if label and team_name:
                    groups.setdefault(label, []).append(team_name)
        logger.info("Fetched standings for league %d: %d groups", league_id, len(groups))
        return groups

    async def get_lineups_for_match(
        self,
        home_team: str,
        away_team: str,
    ) -> Optional[dict[str, Any]]:
        """Resolve fixture ID then fetch lineups for both teams.

        Returns dict with keys: fixture_id, home, away.
        Returns None if fixture ID cannot be resolved.
        """
        fixture_id = await self.get_upcoming_fixture_id(home_team, away_team)
        if not fixture_id:
            return None

        raw_lineups = await self.get_lineups(fixture_id)
        if not raw_lineups:
            return {"fixture_id": fixture_id, "home": None, "away": None}

        result: dict[str, Any] = {"fixture_id": fixture_id, "home": None, "away": None}
        for team_lineup in raw_lineups:
            normalized = self._normalize_lineup(team_lineup)
            team_name = normalized["team_name"]
            if self._fuzzy_match_team(team_name, home_team):
                result["home"] = normalized
            elif self._fuzzy_match_team(team_name, away_team):
                result["away"] = normalized

        return result
