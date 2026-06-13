"""
EuroGoal Predictor — Data Synchronisation Orchestrator
======================================================

Co-ordinates data flow between external APIs and the local SQLite
database:

1. **Results sync** — pull finished matches from football-data.org (with CSV fallback).
2. **xG sync** — enrich stored matches with Understat xG values.
3. **Upcoming sync** — store future fixtures for prediction.
4. **Full sync** — run all three in sequence.

Usage::

    from app.database.db import Database
    from app.services.football_data import FootballDataClient
    from app.services.scraper import UnderstatScraper
    from app.services.sync import DataSyncService

    db = Database()
    db.initialize()

    async with FootballDataClient() as fd, UnderstatScraper() as us:
        sync = DataSyncService(db, fd, us)
        await sync.full_sync("PL", "2024")
"""

from __future__ import annotations

import logging
from typing import Any

from app.config import COMPETITIONS, FOOTBALL_DATA_API_KEY
from app.database.db import Database
from app.services.football_data import FootballDataClient
from app.services.scraper import UnderstatScraper
from app.services.csv_data import CSVDataSource

logger = logging.getLogger(__name__)


class DataSyncService:
    """Orchestrates data synchronisation between external APIs and the
    local SQLite database.

    Parameters
    ----------
    db : Database
        Initialised :class:`Database` instance.
    fd_client : FootballDataClient
        Active :class:`FootballDataClient` (must be inside its async
        context manager).
    scraper : UnderstatScraper
        Active :class:`UnderstatScraper` (must be inside its async
        context manager).
    """

    def __init__(
        self,
        db: Database,
        fd_client: FootballDataClient,
        scraper: UnderstatScraper,
    ) -> None:
        self.db = db
        self.fd_client = fd_client
        self.scraper = scraper

    # ------------------------------------------------------------------
    # Result synchronisation (football-data.org → DB)
    # ------------------------------------------------------------------

    async def sync_results(self, competition: str, season: str) -> int:
        """Fetch the latest **finished** matches and store them in the database.

        Tries football-data.org first; falls back to free CSV data from
        football-data.co.uk if the API call fails (e.g. missing API key).

        Parameters
        ----------
        competition : str
            Competition code (e.g. ``"PL"``).
        season : str
            Starting year of the season (e.g. ``"2024"``).

        Returns
        -------
        int
            Number of new matches inserted.
        """
        logger.info("Syncing results for %s season %s …", competition, season)

        matches = []
        source = "football-data.org"

        # Try football-data.org API first
        if FOOTBALL_DATA_API_KEY:
            try:
                matches = await self.fd_client.get_matches(
                    competition=competition, season=season, status="FINISHED"
                )
            except Exception as e:
                logger.warning("football-data.org API failed (%s), trying CSV fallback...", e)
                matches = []
        else:
            logger.info("No FOOTBALL_DATA_API_KEY set, using CSV fallback.")

        # Fallback to free CSV data
        if not matches:
            source = "football-data.co.uk CSV"
            async with CSVDataSource() as csv_source:
                matches = await csv_source.fetch_matches(competition, season)

        if not matches:
            logger.info("No finished matches returned for %s %s.", competition, season)
            return 0

        # Enrich each match dict with competition/season keys expected
        # by the bulk-insert method.
        for m in matches:
            m.setdefault("competition", competition)
            m.setdefault("season", season)
            m.setdefault("status", "FINISHED")

        inserted = self.db.insert_matches_bulk(matches)
        logger.info(
            "Inserted %d new result(s) for %s %s from %s (of %d fetched).",
            inserted,
            competition,
            season,
            source,
            len(matches),
        )
        return inserted

    # ------------------------------------------------------------------
    # xG synchronisation (Understat → DB)
    # ------------------------------------------------------------------

    async def sync_xg_data(self, competition: str, season: str) -> int:
        """Fetch xG data from Understat and attach it to existing match
        rows in the database.

        The method maps the football-data.org competition code to the
        Understat league name using ``app.config.COMPETITIONS``.  If the
        competition does not have an Understat equivalent (e.g. Champions
        League), a warning is logged and ``0`` is returned.

        Parameters
        ----------
        competition : str
            Competition code (e.g. ``"PL"``).
        season : str
            Starting year of the season.

        Returns
        -------
        int
            Number of matches successfully enriched with xG data.
        """
        comp_info = COMPETITIONS.get(competition, {})
        understat_name: str | None = comp_info.get("understat_name")  # type: ignore[assignment]

        if not understat_name:
            logger.warning(
                "No Understat mapping for competition '%s'; skipping xG sync.",
                competition,
            )
            return 0

        logger.info(
            "Fetching xG data from Understat (%s, season %s) …",
            understat_name,
            season,
        )
        xg_matches = await self.scraper.fetch_league_matches(understat_name, season)

        if not xg_matches:
            logger.info("Understat returned no matches for %s %s.", understat_name, season)
            return 0

        updated = 0
        for xg in xg_matches:
            # Attempt to match by date-prefix + team names.
            date_prefix = xg["date"][:10]  # YYYY-MM-DD
            success = self.db.update_match_xg(
                competition=competition,
                date=date_prefix,
                home_team=xg["home_team"],
                away_team=xg["away_team"],
                home_xg=xg["home_xg"],
                away_xg=xg["away_xg"],
            )
            if success:
                updated += 1

        logger.info(
            "Updated xG for %d / %d matches (%s %s).",
            updated,
            len(xg_matches),
            competition,
            season,
        )
        return updated

    # ------------------------------------------------------------------
    # Upcoming fixtures (football-data.org → DB)
    # ------------------------------------------------------------------

    async def sync_upcoming(self, competition: str, days: int = 14) -> int:
        """Fetch upcoming fixtures from football-data.org and store them
        in the database.

        Parameters
        ----------
        competition : str
            Competition code.
        days : int
            Number of days to look ahead (default 14).

        Returns
        -------
        int
            Number of new fixture rows inserted.
        """
        logger.info(
            "Syncing upcoming fixtures for %s (next %d days) …",
            competition,
            days,
        )

        if not FOOTBALL_DATA_API_KEY:
            logger.info("Skipping upcoming sync — no API key configured.")
            return 0

        try:
            matches = await self.fd_client.get_upcoming_matches(
                competition=competition, days=days
            )
        except Exception as e:
            logger.warning("Failed to fetch upcoming fixtures: %s", e)
            return 0

        if not matches:
            logger.info("No upcoming matches found for %s.", competition)
            return 0

        for m in matches:
            m.setdefault("competition", competition)
            m.setdefault("status", "SCHEDULED")

        inserted = self.db.insert_matches_bulk(matches)
        logger.info(
            "Inserted %d upcoming fixture(s) for %s (of %d fetched).",
            inserted,
            competition,
            len(matches),
        )
        return inserted

    # ------------------------------------------------------------------
    # Full sync
    # ------------------------------------------------------------------

    async def full_sync(self, competition: str, season: str) -> dict[str, int]:
        """Run the complete synchronisation pipeline for a competition:

        1. Sync finished results from football-data.org.
        2. Enrich matches with Understat xG data.
        3. Sync upcoming fixtures.

        Parameters
        ----------
        competition : str
            Competition code.
        season : str
            Starting year of the season.

        Returns
        -------
        dict[str, int]
            Summary counts::

                {
                    "results_inserted": int,
                    "xg_updated": int,
                    "upcoming_inserted": int,
                }
        """
        logger.info(
            "=== Starting full sync for %s (season %s) ===", competition, season
        )

        results_inserted = await self.sync_results(competition, season)

        # xG enrichment is best-effort — don't fail the entire sync if it breaks
        try:
            xg_updated = await self.sync_xg_data(competition, season)
        except Exception as e:
            logger.warning("xG sync failed (non-fatal): %s", e)
            xg_updated = 0

        upcoming_inserted = await self.sync_upcoming(competition)

        summary = {
            "results_inserted": results_inserted,
            "xg_updated": xg_updated,
            "upcoming_inserted": upcoming_inserted,
        }
        logger.info("=== Full sync complete for %s: %s ===", competition, summary)
        return summary
