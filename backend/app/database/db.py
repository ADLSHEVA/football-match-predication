"""
EuroGoal Predictor — SQLite Database Manager
=============================================

Provides a synchronous SQLite wrapper with:
  • Schema initialisation (teams, matches, model_params, predictions)
  • Context-managed connection helpers
  • Full CRUD surface for every table

Usage::

    from app.database.db import Database

    db = Database()
    db.initialize()
    db.insert_match(competition="PL", season="2024", ...)
"""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Generator, Optional

from app.config import DATABASE_PATH, ELO_INITIAL_RATING

# ---------------------------------------------------------------------------
# SQL DDL – executed once via ``Database.initialize()``
# ---------------------------------------------------------------------------

_CREATE_TEAMS = """
CREATE TABLE IF NOT EXISTS teams (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT UNIQUE NOT NULL,
    short_name  TEXT,
    competition TEXT,
    elo_rating  REAL DEFAULT {elo_default}
);
""".format(elo_default=ELO_INITIAL_RATING)

_CREATE_MATCHES = """
CREATE TABLE IF NOT EXISTS matches (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    competition TEXT    NOT NULL,
    season      TEXT    NOT NULL,
    matchday    INTEGER,
    date        TEXT    NOT NULL,
    home_team   TEXT    NOT NULL,
    away_team   TEXT    NOT NULL,
    home_goals  INTEGER,
    away_goals  INTEGER,
    home_xg     REAL,
    away_xg     REAL,
    status      TEXT    DEFAULT 'SCHEDULED',
    UNIQUE(competition, season, date, home_team, away_team)
);
"""

_CREATE_MODEL_PARAMS = """
CREATE TABLE IF NOT EXISTS model_params (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    team        TEXT NOT NULL,
    competition TEXT NOT NULL,
    attack      REAL NOT NULL,
    defense     REAL NOT NULL,
    updated_at  TEXT NOT NULL,
    UNIQUE(team, competition)
);
"""

_CREATE_PREDICTIONS = """
CREATE TABLE IF NOT EXISTS predictions (
    id                   INTEGER PRIMARY KEY AUTOINCREMENT,
    match_id             INTEGER REFERENCES matches(id),
    home_win_prob        REAL,
    draw_prob            REAL,
    away_win_prob        REAL,
    predicted_home_goals REAL,
    predicted_away_goals REAL,
    model_version        TEXT,
    created_at           TEXT NOT NULL
);
"""

_CREATE_ODDS_CACHE = """
CREATE TABLE IF NOT EXISTS odds_cache (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    home_team   TEXT    NOT NULL,
    away_team   TEXT    NOT NULL,
    bookmaker   TEXT    NOT NULL,
    market      TEXT    NOT NULL,
    home_odds   REAL,
    draw_odds   REAL,
    away_odds   REAL,
    spread_home REAL,
    spread_away REAL,
    total_line  REAL,
    over_odds   REAL,
    under_odds  REAL,
    fetched_at  TEXT    NOT NULL,
    UNIQUE(home_team, away_team, bookmaker, market)
);
"""

_CREATE_H2H_CACHE = """
CREATE TABLE IF NOT EXISTS h2h_cache (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    home_team    TEXT    NOT NULL,
    away_team    TEXT    NOT NULL,
    fixture_date TEXT    NOT NULL,
    home_goals   INTEGER,
    away_goals   INTEGER,
    league       TEXT,
    fetched_at   TEXT    NOT NULL,
    UNIQUE(home_team, away_team, fixture_date)
);
"""

_CREATE_LINEUPS_CACHE = """
CREATE TABLE IF NOT EXISTS lineups_cache (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    home_team       TEXT    NOT NULL,
    away_team       TEXT    NOT NULL,
    fixture_id      INTEGER,
    home_formation  TEXT,
    away_formation  TEXT,
    home_startxi    TEXT,
    away_startxi    TEXT,
    home_coach      TEXT,
    away_coach      TEXT,
    fetched_at      TEXT    NOT NULL,
    UNIQUE(home_team, away_team)
);
"""

# World Cup pre-match predictions, locked once made and settled after the
# result is known — the basis for the predicted-vs-actual comparison.
_CREATE_WC_PREDICTIONS = """
CREATE TABLE IF NOT EXISTS wc_predictions (
    fixture_id     INTEGER PRIMARY KEY,
    home_team      TEXT,
    away_team      TEXT,
    utc_date       TEXT,
    stage          TEXT,
    grp            TEXT,
    p_home         REAL,
    p_draw         REAL,
    p_away         REAL,
    pred_result    TEXT,
    pred_home      INTEGER,
    pred_away      INTEGER,
    settled        INTEGER DEFAULT 0,
    actual_home    INTEGER,
    actual_away    INTEGER,
    actual_result  TEXT,
    result_correct INTEGER,
    score_correct  INTEGER,
    created_at     TEXT,
    updated_at     TEXT
);
"""


class Database:
    """Synchronous SQLite database manager for EuroGoal Predictor.

    Parameters
    ----------
    db_path : str | Path, optional
        Filesystem path to the SQLite database file.
        Defaults to ``app.config.DATABASE_PATH``.
    """

    def __init__(self, db_path: str | Path = DATABASE_PATH) -> None:
        self.db_path = Path(db_path)
        # Ensure parent directory exists so SQLite can create the file.
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Connection helpers
    # ------------------------------------------------------------------

    @contextmanager
    def _connect(self) -> Generator[sqlite3.Connection, None, None]:
        """Yield a connection that auto-commits on success and rolls back
        on exception.  ``Row`` factory is enabled so that ``fetchall``
        returns :class:`sqlite3.Row` objects (dict-like access).
        """
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    @contextmanager
    def _cursor(self) -> Generator[sqlite3.Cursor, None, None]:
        """Convenience wrapper: yields a *cursor* instead of a connection."""
        with self._connect() as conn:
            yield conn.cursor()

    # ------------------------------------------------------------------
    # Schema initialisation
    # ------------------------------------------------------------------

    def initialize(self) -> None:
        """Create all tables if they do not already exist.

        Safe to call multiple times — uses ``CREATE TABLE IF NOT EXISTS``.
        """
        with self._cursor() as cur:
            cur.execute(_CREATE_TEAMS)
            cur.execute(_CREATE_MATCHES)
            cur.execute(_CREATE_MODEL_PARAMS)
            cur.execute(_CREATE_PREDICTIONS)
            cur.execute(_CREATE_ODDS_CACHE)
            cur.execute(_CREATE_H2H_CACHE)
            cur.execute(_CREATE_LINEUPS_CACHE)
            cur.execute(_CREATE_WC_PREDICTIONS)

    # ------------------------------------------------------------------
    # Matches
    # ------------------------------------------------------------------

    def insert_match(
        self,
        competition: str,
        season: str,
        date: str,
        home_team: str,
        away_team: str,
        *,
        matchday: Optional[int] = None,
        home_goals: Optional[int] = None,
        away_goals: Optional[int] = None,
        home_xg: Optional[float] = None,
        away_xg: Optional[float] = None,
        status: str = "SCHEDULED",
    ) -> int:
        """Insert a single match row.

        Uses ``INSERT OR IGNORE`` to silently skip duplicates that violate
        the UNIQUE constraint on (competition, season, date, home_team,
        away_team).

        Returns
        -------
        int
            The ``rowid`` of the inserted (or existing) row.
        """
        sql = """
            INSERT OR IGNORE INTO matches
                (competition, season, matchday, date,
                 home_team, away_team, home_goals, away_goals,
                 home_xg, away_xg, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        with self._cursor() as cur:
            cur.execute(
                sql,
                (
                    competition,
                    season,
                    matchday,
                    date,
                    home_team,
                    away_team,
                    home_goals,
                    away_goals,
                    home_xg,
                    away_xg,
                    status,
                ),
            )
            return cur.lastrowid  # type: ignore[return-value]

    def insert_matches_bulk(self, matches_list: list[dict[str, Any]]) -> int:
        """Insert many matches in a single transaction.

        Each dict in *matches_list* must contain at least the keys
        ``competition``, ``season``, ``date``, ``home_team``, ``away_team``.
        Optional keys: ``matchday``, ``home_goals``, ``away_goals``,
        ``home_xg``, ``away_xg``, ``status``.

        Returns
        -------
        int
            Number of rows actually inserted (duplicates are silently
            skipped).
        """
        sql = """
            INSERT OR IGNORE INTO matches
                (competition, season, matchday, date,
                 home_team, away_team, home_goals, away_goals,
                 home_xg, away_xg, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        rows: list[tuple] = []
        for m in matches_list:
            rows.append(
                (
                    m["competition"],
                    m["season"],
                    m.get("matchday"),
                    m["date"],
                    m["home_team"],
                    m["away_team"],
                    m.get("home_goals"),
                    m.get("away_goals"),
                    m.get("home_xg"),
                    m.get("away_xg"),
                    m.get("status", "SCHEDULED"),
                )
            )
        with self._cursor() as cur:
            cur.executemany(sql, rows)
            return cur.rowcount

    def get_matches(
        self,
        competition: str,
        season: Optional[str] = None,
        status: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        """Return matches filtered by competition, and optionally by season
        and/or status.

        Parameters
        ----------
        competition : str
            Football-data.org competition code (e.g. ``"PL"``).
        season : str, optional
            Season identifier (e.g. ``"2024"``).
        status : str, optional
            Match status filter (``"FINISHED"``, ``"SCHEDULED"``, …).

        Returns
        -------
        list[dict]
            Each match as a plain dict.
        """
        clauses = ["competition = ?"]
        params: list[Any] = [competition]

        if season is not None:
            clauses.append("season = ?")
            params.append(season)
        if status is not None:
            clauses.append("status = ?")
            params.append(status)

        sql = f"SELECT * FROM matches WHERE {' AND '.join(clauses)} ORDER BY date"
        with self._cursor() as cur:
            cur.execute(sql, params)
            return [dict(row) for row in cur.fetchall()]

    def get_upcoming_matches(self, competition: str) -> list[dict[str, Any]]:
        """Return all ``SCHEDULED`` (or ``TIMED``) matches for *competition*
        whose date is today or in the future.

        Returns
        -------
        list[dict]
            Upcoming match dicts sorted by date ascending.
        """
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        sql = """
            SELECT * FROM matches
            WHERE competition = ?
              AND status IN ('SCHEDULED', 'TIMED')
              AND date >= ?
            ORDER BY date
        """
        with self._cursor() as cur:
            cur.execute(sql, (competition, today))
            return [dict(row) for row in cur.fetchall()]

    def update_match_xg(
        self,
        competition: str,
        date: str,
        home_team: str,
        away_team: str,
        home_xg: float,
        away_xg: float,
    ) -> bool:
        """Set xG values on an existing match row identified by its natural
        key.

        Returns
        -------
        bool
            ``True`` if a row was updated, ``False`` if no matching row was
            found.
        """
        sql = """
            UPDATE matches
               SET home_xg = ?, away_xg = ?
             WHERE competition = ?
               AND date LIKE ?
               AND home_team = ?
               AND away_team = ?
        """
        # date might be stored as full ISO or date-only; use LIKE prefix match
        with self._cursor() as cur:
            cur.execute(
                sql,
                (home_xg, away_xg, competition, f"{date}%", home_team, away_team),
            )
            return cur.rowcount > 0

    # ------------------------------------------------------------------
    # Teams / ELO
    # ------------------------------------------------------------------

    def update_team_elo(self, team: str, rating: float) -> None:
        """Insert the team if it does not exist, then update its ELO
        rating.

        Uses ``INSERT OR IGNORE`` followed by an ``UPDATE`` to implement
        an upsert-style pattern compatible with all SQLite versions.
        """
        with self._cursor() as cur:
            cur.execute(
                "INSERT OR IGNORE INTO teams (name) VALUES (?)", (team,)
            )
            cur.execute(
                "UPDATE teams SET elo_rating = ? WHERE name = ?", (rating, team)
            )

    def get_team_elo(self, team: str) -> Optional[float]:
        """Return the current ELO rating for *team*, or ``None`` if the
        team is not in the database.
        """
        with self._cursor() as cur:
            cur.execute(
                "SELECT elo_rating FROM teams WHERE name = ?", (team,)
            )
            row = cur.fetchone()
            return float(row["elo_rating"]) if row else None

    # ------------------------------------------------------------------
    # Model parameters
    # ------------------------------------------------------------------

    def upsert_model_params(
        self,
        team: str,
        competition: str,
        attack: float,
        defense: float,
    ) -> None:
        """Insert or update the Dixon-Coles attack/defense parameters for
        a (team, competition) pair.

        Uses SQLite's ``INSERT … ON CONFLICT … DO UPDATE`` (upsert)
        syntax, which requires SQLite ≥ 3.24.
        """
        now = datetime.now(timezone.utc).isoformat()
        sql = """
            INSERT INTO model_params (team, competition, attack, defense, updated_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(team, competition) DO UPDATE
               SET attack     = excluded.attack,
                   defense    = excluded.defense,
                   updated_at = excluded.updated_at
        """
        with self._cursor() as cur:
            cur.execute(sql, (team, competition, attack, defense, now))

    def get_model_params(
        self, competition: str
    ) -> dict[str, dict[str, float]]:
        """Return all fitted model parameters for a competition.

        Returns
        -------
        dict[str, dict[str, float]]
            Mapping ``{team_name: {"attack": …, "defense": …}}``.
        """
        sql = "SELECT team, attack, defense FROM model_params WHERE competition = ?"
        with self._cursor() as cur:
            cur.execute(sql, (competition,))
            return {
                row["team"]: {"attack": row["attack"], "defense": row["defense"]}
                for row in cur.fetchall()
            }

    # ------------------------------------------------------------------
    # Predictions
    # ------------------------------------------------------------------

    def save_prediction(
        self,
        match_id: int,
        home_win_prob: float,
        draw_prob: float,
        away_win_prob: float,
        predicted_home_goals: float,
        predicted_away_goals: float,
        model_version: str = "v1",
    ) -> int:
        """Persist a prediction for a given match.

        Returns
        -------
        int
            Row-id of the newly created prediction.
        """
        now = datetime.now(timezone.utc).isoformat()
        sql = """
            INSERT INTO predictions
                (match_id, home_win_prob, draw_prob, away_win_prob,
                 predicted_home_goals, predicted_away_goals,
                 model_version, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """
        with self._cursor() as cur:
            cur.execute(
                sql,
                (
                    match_id,
                    home_win_prob,
                    draw_prob,
                    away_win_prob,
                    predicted_home_goals,
                    predicted_away_goals,
                    model_version,
                    now,
                ),
            )
            return cur.lastrowid  # type: ignore[return-value]

    def get_historical_predictions(self) -> list[dict[str, Any]]:
        """Return all predictions joined with their corresponding match
        data, ordered most-recent first.

        The join provides context (team names, actual goals) alongside the
        predicted values so that calibration analyses can be performed.

        Returns
        -------
        list[dict]
            Combined prediction + match rows.
        """
        sql = """
            SELECT
                p.id               AS prediction_id,
                p.match_id,
                p.home_win_prob,
                p.draw_prob,
                p.away_win_prob,
                p.predicted_home_goals,
                p.predicted_away_goals,
                p.model_version,
                p.created_at,
                m.competition,
                m.season,
                m.date,
                m.home_team,
                m.away_team,
                m.home_goals,
                m.away_goals,
                m.home_xg,
                m.away_xg,
                m.status
            FROM predictions p
            LEFT JOIN matches m ON m.id = p.match_id
            ORDER BY p.created_at DESC
        """
        with self._cursor() as cur:
            cur.execute(sql)
            return [dict(row) for row in cur.fetchall()]

    # ------------------------------------------------------------------
    # Bulk accessors (used during app startup)
    # ------------------------------------------------------------------

    def get_all_teams(self) -> list[dict[str, Any]]:
        """Return all teams as a list of dicts.

        Returns
        -------
        list[dict]
            Each team as a dict with keys: id, name, short_name,
            competition, elo_rating.
        """
        sql = "SELECT * FROM teams ORDER BY name"
        with self._cursor() as cur:
            cur.execute(sql)
            return [dict(row) for row in cur.fetchall()]

    def get_all_model_params(self) -> list[dict[str, Any]]:
        """Return all model parameters across all competitions as a flat
        list (used during startup to populate the model).

        Returns
        -------
        list[dict]
            Each row as a dict with keys: team, competition, attack,
            defense, updated_at.
        """
        sql = "SELECT team, competition, attack, defense, updated_at FROM model_params"
        with self._cursor() as cur:
            cur.execute(sql)
            return [dict(row) for row in cur.fetchall()]

    # ------------------------------------------------------------------
    # Odds Cache
    # ------------------------------------------------------------------

    def upsert_odds(
        self,
        home_team: str,
        away_team: str,
        bookmaker: str,
        market: str,
        home_odds: Optional[float] = None,
        draw_odds: Optional[float] = None,
        away_odds: Optional[float] = None,
        spread_home: Optional[float] = None,
        spread_away: Optional[float] = None,
        total_line: Optional[float] = None,
        over_odds: Optional[float] = None,
        under_odds: Optional[float] = None,
    ) -> None:
        """Insert or update cached odds for a match/bookmaker/market."""
        now = datetime.now(timezone.utc).isoformat()
        sql = """
            INSERT INTO odds_cache (home_team, away_team, bookmaker, market,
                home_odds, draw_odds, away_odds, spread_home, spread_away,
                total_line, over_odds, under_odds, fetched_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(home_team, away_team, bookmaker, market) DO UPDATE
               SET home_odds   = excluded.home_odds,
                   draw_odds   = excluded.draw_odds,
                   away_odds   = excluded.away_odds,
                   spread_home = excluded.spread_home,
                   spread_away = excluded.spread_away,
                   total_line  = excluded.total_line,
                   over_odds   = excluded.over_odds,
                   under_odds  = excluded.under_odds,
                   fetched_at  = excluded.fetched_at
        """
        with self._cursor() as cur:
            cur.execute(
                sql,
                (
                    home_team, away_team, bookmaker, market,
                    home_odds, draw_odds, away_odds,
                    spread_home, spread_away, total_line,
                    over_odds, under_odds, now,
                ),
            )

    def get_cached_odds(
        self,
        home_team: str,
        away_team: str,
        max_age_minutes: int = 240,
    ) -> list[dict[str, Any]]:
        """Return cached odds if fetched within max_age_minutes, else empty list."""
        cutoff = (
            datetime.now(timezone.utc) - timedelta(minutes=max_age_minutes)
        ).isoformat()
        sql = """
            SELECT * FROM odds_cache
            WHERE home_team = ? AND away_team = ? AND fetched_at >= ?
            ORDER BY bookmaker
        """
        with self._cursor() as cur:
            cur.execute(sql, (home_team, away_team, cutoff))
            return [dict(row) for row in cur.fetchall()]

    # ------------------------------------------------------------------
    # H2H Cache
    # ------------------------------------------------------------------

    def insert_h2h_results(
        self,
        home_team: str,
        away_team: str,
        results: list[dict[str, Any]],
    ) -> int:
        """Bulk insert H2H match results with INSERT OR IGNORE."""
        now = datetime.now(timezone.utc).isoformat()
        sql = """
            INSERT OR IGNORE INTO h2h_cache
                (home_team, away_team, fixture_date, home_goals, away_goals,
                 league, fetched_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """
        rows = [
            (
                home_team, away_team,
                r.get("date", ""),
                r.get("home_goals"),
                r.get("away_goals"),
                r.get("league", ""),
                now,
            )
            for r in results
        ]
        with self._cursor() as cur:
            cur.executemany(sql, rows)
            return cur.rowcount

    def get_cached_h2h(
        self,
        home_team: str,
        away_team: str,
        max_age_hours: int = 24,
    ) -> list[dict[str, Any]]:
        """Return cached H2H results if fetched within max_age_hours, else empty list."""
        cutoff = (
            datetime.now(timezone.utc) - timedelta(hours=max_age_hours)
        ).isoformat()
        sql = """
            SELECT * FROM h2h_cache
            WHERE home_team = ? AND away_team = ? AND fetched_at >= ?
            ORDER BY fixture_date DESC
        """
        with self._cursor() as cur:
            cur.execute(sql, (home_team, away_team, cutoff))
            return [dict(row) for row in cur.fetchall()]

    # ------------------------------------------------------------------
    # Lineups Cache
    # ------------------------------------------------------------------

    def upsert_lineups(
        self,
        home_team: str,
        away_team: str,
        fixture_id: Optional[int],
        home_formation: Optional[str],
        away_formation: Optional[str],
        home_startxi: list[dict],
        away_startxi: list[dict],
        home_coach: Optional[str] = None,
        away_coach: Optional[str] = None,
    ) -> None:
        """Insert or update cached lineup data for a match."""
        import json
        now = datetime.now(timezone.utc).isoformat()
        sql = """
            INSERT INTO lineups_cache
                (home_team, away_team, fixture_id,
                 home_formation, away_formation,
                 home_startxi, away_startxi,
                 home_coach, away_coach, fetched_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(home_team, away_team) DO UPDATE
               SET fixture_id     = excluded.fixture_id,
                   home_formation = excluded.home_formation,
                   away_formation = excluded.away_formation,
                   home_startxi   = excluded.home_startxi,
                   away_startxi   = excluded.away_startxi,
                   home_coach     = excluded.home_coach,
                   away_coach     = excluded.away_coach,
                   fetched_at     = excluded.fetched_at
        """
        with self._cursor() as cur:
            cur.execute(sql, (
                home_team, away_team, fixture_id,
                home_formation, away_formation,
                json.dumps(home_startxi), json.dumps(away_startxi),
                home_coach, away_coach, now,
            ))

    def get_cached_lineups(
        self,
        home_team: str,
        away_team: str,
        max_age_hours: int = 24,
    ) -> Optional[dict[str, Any]]:
        """Return cached lineup data if fetched within max_age_hours, else None."""
        import json
        cutoff = (
            datetime.now(timezone.utc) - timedelta(hours=max_age_hours)
        ).isoformat()
        sql = """
            SELECT * FROM lineups_cache
            WHERE home_team = ? AND away_team = ? AND fetched_at >= ?
        """
        with self._cursor() as cur:
            cur.execute(sql, (home_team, away_team, cutoff))
            row = cur.fetchone()
            if not row:
                return None
            result = dict(row)
            result["home_startxi"] = json.loads(result["home_startxi"]) if result["home_startxi"] else []
            result["away_startxi"] = json.loads(result["away_startxi"]) if result["away_startxi"] else []
            return result

    # ------------------------------------------------------------------
    # World Cup predictions
    # ------------------------------------------------------------------

    def upsert_wc_prediction(
        self,
        fixture_id: int,
        home_team: Optional[str],
        away_team: Optional[str],
        utc_date: Optional[str],
        stage: Optional[str],
        grp: Optional[str],
        p_home: float,
        p_draw: float,
        p_away: float,
        pred_result: str,
        pred_home: int,
        pred_away: int,
    ) -> None:
        """Insert or refresh a pre-match prediction.

        Already-settled rows are left untouched (predictions lock once the
        match is played), so only pending fixtures get their prediction
        refreshed as team strengths evolve.
        """
        now = datetime.now(timezone.utc).isoformat()
        sql = """
            INSERT INTO wc_predictions
                (fixture_id, home_team, away_team, utc_date, stage, grp,
                 p_home, p_draw, p_away, pred_result, pred_home, pred_away,
                 settled, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?, ?)
            ON CONFLICT(fixture_id) DO UPDATE SET
                home_team   = excluded.home_team,
                away_team   = excluded.away_team,
                utc_date    = excluded.utc_date,
                stage       = excluded.stage,
                grp         = excluded.grp,
                p_home      = excluded.p_home,
                p_draw      = excluded.p_draw,
                p_away      = excluded.p_away,
                pred_result = excluded.pred_result,
                pred_home   = excluded.pred_home,
                pred_away   = excluded.pred_away,
                updated_at  = excluded.updated_at
            WHERE wc_predictions.settled = 0
        """
        with self._cursor() as cur:
            cur.execute(sql, (
                fixture_id, home_team, away_team, utc_date, stage, grp,
                p_home, p_draw, p_away, pred_result, pred_home, pred_away,
                now, now,
            ))

    def settle_wc_prediction(
        self,
        fixture_id: int,
        actual_home: int,
        actual_away: int,
        actual_result: str,
        result_correct: bool,
        score_correct: bool,
    ) -> None:
        """Lock in the actual result and correctness for a played fixture."""
        now = datetime.now(timezone.utc).isoformat()
        sql = """
            UPDATE wc_predictions
               SET settled = 1,
                   actual_home = ?, actual_away = ?, actual_result = ?,
                   result_correct = ?, score_correct = ?, updated_at = ?
             WHERE fixture_id = ? AND settled = 0
        """
        with self._cursor() as cur:
            cur.execute(sql, (
                actual_home, actual_away, actual_result,
                int(result_correct), int(score_correct), now, fixture_id,
            ))

    def get_wc_predictions(self) -> dict[int, dict[str, Any]]:
        """Return all stored World Cup predictions keyed by fixture_id."""
        with self._cursor() as cur:
            cur.execute("SELECT * FROM wc_predictions")
            return {row["fixture_id"]: dict(row) for row in cur.fetchall()}

    # ------------------------------------------------------------------
    # Utility
    # ------------------------------------------------------------------

    def __repr__(self) -> str:
        return f"Database(db_path={self.db_path!r})"

