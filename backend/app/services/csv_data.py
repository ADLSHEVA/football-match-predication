"""
EuroGoal Predictor — Free CSV Data Source (Fallback)
=====================================================

Fetches historical match data from football-data.co.uk CSV files.
This is a free, no-authentication fallback when the football-data.org
API key is not configured.

CSV source: https://www.football-data.co.uk/mmz4281/{season}/{division}.csv
"""

from __future__ import annotations

import csv
import io
import logging
from datetime import datetime
from typing import Any, Optional

import httpx

from app.config import COMPETITIONS

logger = logging.getLogger(__name__)

# Map competition codes to football-data.co.uk division codes
_DIVISION_MAP = {
    "PL":  "E0",
    "PD":  "SP1",
    "BL1": "D1",
    "SA":  "I1",
    "FL1": "F1",
}

# Column name mapping from CSV to our schema
_CSV_COLUMNS = {
    "Date":    "date",
    "HomeTeam": "home_team",
    "AwayTeam": "away_team",
    "FTHG":    "home_goals",
    "FTAG":    "away_goals",
    "FTR":     "result",
}


class CSVDataSource:
    """Fetches match data from free football-data.co.uk CSV files.

    Used as a fallback when the football-data.org API key is not set.
    """

    BASE_URL = "https://www.football-data.co.uk/mmz4281"

    def __init__(self) -> None:
        self._client: Optional[httpx.AsyncClient] = None

    async def __aenter__(self) -> "CSVDataSource":
        self._client = httpx.AsyncClient(
            follow_redirects=True,
            timeout=30.0,
            headers={"User-Agent": "EuroGoalPredictor/3.0"},
        )
        return self

    async def __aexit__(self, *exc: Any) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    @staticmethod
    def _season_to_path(season: str) -> str:
        """Convert season start year to URL path segment.

        '2024' -> '2425'
        '2023' -> '2324'
        """
        start = int(season)
        end_short = (start + 1) % 100
        return f"{start % 100:02d}{end_short:02d}"

    @staticmethod
    def _parse_date(date_str: str) -> Optional[str]:
        """Parse various date formats from CSV to ISO date (YYYY-MM-DD)."""
        if not date_str:
            return None
        for fmt in ("%d/%m/%Y", "%d/%m/%y", "%Y-%m-%d"):
            try:
                return datetime.strptime(date_str.strip(), fmt).strftime("%Y-%m-%d")
            except ValueError:
                continue
        return None

    async def fetch_matches(
        self, competition: str, season: str
    ) -> list[dict[str, Any]]:
        """Fetch finished matches from football-data.co.uk CSV.

        Parameters
        ----------
        competition : str
            Competition code (e.g. ``"PL"``).
        season : str
            Starting year of the season (e.g. ``"2024"``).

        Returns
        -------
        list[dict]
            Normalised match dicts compatible with ``Database.insert_matches_bulk``.
        """
        if self._client is None:
            raise RuntimeError("CSVDataSource must be used as async context manager")

        division = _DIVISION_MAP.get(competition)
        if not division:
            logger.warning("No CSV mapping for competition '%s'", competition)
            return []

        season_path = self._season_to_path(season)
        url = f"{self.BASE_URL}/{season_path}/{division}.csv"

        logger.info("Fetching CSV data from %s", url)
        try:
            response = await self._client.get(url)
            response.raise_for_status()
        except httpx.HTTPStatusError as e:
            logger.warning("CSV fetch failed (%s): %s", e.response.status_code, url)
            return []
        except Exception as e:
            logger.warning("CSV fetch error: %s", e)
            return []

        # Parse CSV
        matches = []
        text = response.text
        reader = csv.DictReader(io.StringIO(text))

        for row in reader:
            home_team = row.get("HomeTeam", "").strip()
            away_team = row.get("AwayTeam", "").strip()
            home_goals_str = row.get("FTHG", "").strip()
            away_goals_str = row.get("FTAG", "").strip()
            date_str = row.get("Date", "").strip()

            if not home_team or not away_team or not date_str:
                continue

            # Skip rows without full-time goals (unplayed matches)
            if not home_goals_str or not away_goals_str:
                continue

            try:
                home_goals = int(home_goals_str)
                away_goals = int(away_goals_str)
            except ValueError:
                continue

            iso_date = self._parse_date(date_str)
            if not iso_date:
                continue

            matches.append({
                "competition": competition,
                "season": season,
                "date": iso_date,
                "home_team": home_team,
                "away_team": away_team,
                "home_goals": home_goals,
                "away_goals": away_goals,
                "status": "FINISHED",
            })

        logger.info(
            "Parsed %d matches from CSV for %s %s", len(matches), competition, season
        )
        return matches
