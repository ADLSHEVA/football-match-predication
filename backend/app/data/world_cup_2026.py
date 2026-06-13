"""
EuroGoal Predictor — 2026 FIFA World Cup seed data
===================================================

The 2026 World Cup is the first 48-team edition: **12 groups (A–L) of 4
teams**, with the **top two of each group plus the eight best third-placed
teams** advancing to a 32-team knockout bracket (Round of 32 → R16 → QF →
SF → Final, plus a third-place play-off).

This module is the **offline fallback / strength prior** for the World Cup
module.  National teams cannot be fit with the league Dixon-Coles model
(no Understat xG, far too few matches), so we seed each team with an
approximate Elo strength derived from public national-team Elo ratings
(eloratings.net-style, ~1500–2150 range).  Those seeds are turned into
Poisson goal expectations by the tournament simulator.

IMPORTANT
---------
When a valid API key is configured, :class:`WorldCupService` pulls the
**real** teams, groups and fixtures from the live provider and this table
is used only to (a) supply a strength prior for each team and (b) act as a
fully offline demo.  The group draw encoded below is an *illustrative*,
plausible 48-team field — it is **not** guaranteed to match the official
draw.  The hosts (Mexico, Canada, USA) are placed in groups A, B and D
respectively, consistent with the published 2026 host slots.
"""

from __future__ import annotations

from typing import Dict, List, TypedDict

WORLD_CUP_SEASON: int = 2026

# API-Football competition id for the FIFA World Cup.
API_FOOTBALL_WC_LEAGUE_ID: int = 1
# football-data.org competition code for the World Cup.
FOOTBALL_DATA_WC_CODE: str = "WC"

# Default Elo for a team we have no prior for (weakest realistic WC side).
DEFAULT_SEED_ELO: float = 1550.0


class WCTeam(TypedDict):
    name: str
    code: str   # FIFA 3-letter code
    flag: str   # emoji
    group: str  # "A".."L"
    elo: float  # seed strength


# ── Real 2026 World Cup field (group draw per football-data.org) ───────────
# Team names match football-data.org exactly so live data resolves directly;
# Elo values are approximate national-team ratings (eloratings.net-style) used
# only as a strength prior, then nudged by real results.
WC_TEAMS: List[WCTeam] = [
    # Group A
    {"name": "Mexico",              "code": "MEX", "flag": "🇲🇽", "group": "A", "elo": 1790},
    {"name": "South Korea",         "code": "KOR", "flag": "🇰🇷", "group": "A", "elo": 1790},
    {"name": "Czechia",             "code": "CZE", "flag": "🇨🇿", "group": "A", "elo": 1790},
    {"name": "South Africa",        "code": "RSA", "flag": "🇿🇦", "group": "A", "elo": 1700},
    # Group B
    {"name": "Switzerland",         "code": "SUI", "flag": "🇨🇭", "group": "B", "elo": 1860},
    {"name": "Canada",              "code": "CAN", "flag": "🇨🇦", "group": "B", "elo": 1760},
    {"name": "Bosnia-Herzegovina",  "code": "BIH", "flag": "🇧🇦", "group": "B", "elo": 1710},
    {"name": "Qatar",               "code": "QAT", "flag": "🇶🇦", "group": "B", "elo": 1680},
    # Group C
    {"name": "Brazil",              "code": "BRA", "flag": "🇧🇷", "group": "C", "elo": 2030},
    {"name": "Morocco",             "code": "MAR", "flag": "🇲🇦", "group": "C", "elo": 1870},
    {"name": "Scotland",            "code": "SCO", "flag": "🏴󠁧󠁢󠁳󠁣󠁴󠁿", "group": "C", "elo": 1780},
    {"name": "Haiti",               "code": "HAI", "flag": "🇭🇹", "group": "C", "elo": 1500},
    # Group D
    {"name": "United States",       "code": "USA", "flag": "🇺🇸", "group": "D", "elo": 1800},
    {"name": "Turkey",              "code": "TUR", "flag": "🇹🇷", "group": "D", "elo": 1800},
    {"name": "Paraguay",            "code": "PAR", "flag": "🇵🇾", "group": "D", "elo": 1715},
    {"name": "Australia",           "code": "AUS", "flag": "🇦🇺", "group": "D", "elo": 1730},
    # Group E
    {"name": "Germany",             "code": "GER", "flag": "🇩🇪", "group": "E", "elo": 1960},
    {"name": "Ecuador",             "code": "ECU", "flag": "🇪🇨", "group": "E", "elo": 1810},
    {"name": "Ivory Coast",         "code": "CIV", "flag": "🇨🇮", "group": "E", "elo": 1750},
    {"name": "Curaçao",             "code": "CUR", "flag": "🇨🇼", "group": "E", "elo": 1600},
    # Group F
    {"name": "Netherlands",         "code": "NED", "flag": "🇳🇱", "group": "F", "elo": 2010},
    {"name": "Japan",               "code": "JPN", "flag": "🇯🇵", "group": "F", "elo": 1850},
    {"name": "Sweden",              "code": "SWE", "flag": "🇸🇪", "group": "F", "elo": 1800},
    {"name": "Tunisia",             "code": "TUN", "flag": "🇹🇳", "group": "F", "elo": 1690},
    # Group G
    {"name": "Belgium",             "code": "BEL", "flag": "🇧🇪", "group": "G", "elo": 1930},
    {"name": "Iran",                "code": "IRN", "flag": "🇮🇷", "group": "G", "elo": 1800},
    {"name": "Egypt",               "code": "EGY", "flag": "🇪🇬", "group": "G", "elo": 1760},
    {"name": "New Zealand",         "code": "NZL", "flag": "🇳🇿", "group": "G", "elo": 1510},
    # Group H
    {"name": "Spain",               "code": "ESP", "flag": "🇪🇸", "group": "H", "elo": 2080},
    {"name": "Uruguay",             "code": "URY", "flag": "🇺🇾", "group": "H", "elo": 1900},
    {"name": "Saudi Arabia",        "code": "KSA", "flag": "🇸🇦", "group": "H", "elo": 1685},
    {"name": "Cape Verde Islands",  "code": "CPV", "flag": "🇨🇻", "group": "H", "elo": 1620},
    # Group I
    {"name": "France",              "code": "FRA", "flag": "🇫🇷", "group": "I", "elo": 2090},
    {"name": "Senegal",             "code": "SEN", "flag": "🇸🇳", "group": "I", "elo": 1820},
    {"name": "Norway",              "code": "NOR", "flag": "🇳🇴", "group": "I", "elo": 1860},
    {"name": "Iraq",                "code": "IRQ", "flag": "🇮🇶", "group": "I", "elo": 1650},
    # Group J
    {"name": "Argentina",           "code": "ARG", "flag": "🇦🇷", "group": "J", "elo": 2140},
    {"name": "Austria",             "code": "AUT", "flag": "🇦🇹", "group": "J", "elo": 1820},
    {"name": "Algeria",             "code": "ALG", "flag": "🇩🇿", "group": "J", "elo": 1785},
    {"name": "Jordan",              "code": "JOR", "flag": "🇯🇴", "group": "J", "elo": 1640},
    # Group K
    {"name": "Portugal",            "code": "POR", "flag": "🇵🇹", "group": "K", "elo": 1990},
    {"name": "Colombia",            "code": "COL", "flag": "🇨🇴", "group": "K", "elo": 1910},
    {"name": "Congo DR",            "code": "COD", "flag": "🇨🇩", "group": "K", "elo": 1690},
    {"name": "Uzbekistan",          "code": "UZB", "flag": "🇺🇿", "group": "K", "elo": 1670},
    # Group L
    {"name": "England",             "code": "ENG", "flag": "🏴󠁧󠁢󠁥󠁮󠁧󠁿", "group": "L", "elo": 2000},
    {"name": "Croatia",             "code": "CRO", "flag": "🇭🇷", "group": "L", "elo": 1900},
    {"name": "Ghana",               "code": "GHA", "flag": "🇬🇭", "group": "L", "elo": 1710},
    {"name": "Panama",              "code": "PAN", "flag": "🇵🇦", "group": "L", "elo": 1640},
]

GROUP_LABELS: List[str] = list("ABCDEFGHIJKL")  # A..L (12 groups)

# Alternative spellings other sources may return → our canonical (football-
# data.org) name, so Elo/flag lookups resolve regardless of provider.
TEAM_NAME_ALIASES: Dict[str, str] = {
    "usa": "United States",
    "united states of america": "United States",
    "korea republic": "South Korea",
    "republic of korea": "South Korea",
    "ir iran": "Iran",
    "côte d'ivoire": "Ivory Coast",
    "cote d'ivoire": "Ivory Coast",
    "türkiye": "Turkey",
    "turkiye": "Turkey",
    "czech republic": "Czechia",
    "bosnia and herzegovina": "Bosnia-Herzegovina",
    "bosnia": "Bosnia-Herzegovina",
    "curacao": "Curaçao",
    "dr congo": "Congo DR",
    "democratic republic of congo": "Congo DR",
    "cabo verde": "Cape Verde Islands",
    "cape verde": "Cape Verde Islands",
}


def _norm(name: str) -> str:
    return name.strip().lower()


# Build fast lookups once at import time.
_BY_NAME: Dict[str, WCTeam] = {_norm(t["name"]): t for t in WC_TEAMS}
_BY_CODE: Dict[str, WCTeam] = {t["code"].upper(): t for t in WC_TEAMS}


def get_seed_teams() -> List[WCTeam]:
    """Return a copy of the full 48-team seed field."""
    return [dict(t) for t in WC_TEAMS]  # type: ignore[misc]


def get_seed_groups() -> Dict[str, List[WCTeam]]:
    """Return the seed field grouped by group label A..L."""
    groups: Dict[str, List[WCTeam]] = {g: [] for g in GROUP_LABELS}
    for t in WC_TEAMS:
        groups[t["group"]].append(dict(t))  # type: ignore[arg-type]
    return groups


def get_seed_team(name: str) -> WCTeam | None:
    """Best-effort lookup of the full seed record for a team name.

    Resolves via canonical name, known aliases, then 3-letter code.
    Returns ``None`` if the team is not in the seed field (e.g. a live-API
    qualifier we have no prior for).
    """
    key = _norm(name)
    if key in _BY_NAME:
        return dict(_BY_NAME[key])  # type: ignore[return-value]
    if key in TEAM_NAME_ALIASES:
        canon = _norm(TEAM_NAME_ALIASES[key])
        if canon in _BY_NAME:
            return dict(_BY_NAME[canon])  # type: ignore[return-value]
    if name.upper() in _BY_CODE:
        return dict(_BY_CODE[name.upper()])  # type: ignore[return-value]
    return None


def get_seed_elo(name: str) -> float:
    """Best-effort lookup of a seed Elo for a team name.

    Tries the canonical name, then known aliases, then the 3-letter code.
    Falls back to :data:`DEFAULT_SEED_ELO` for unknown teams so the
    simulator always has a usable strength.
    """
    key = _norm(name)
    if key in _BY_NAME:
        return float(_BY_NAME[key]["elo"])
    if key in TEAM_NAME_ALIASES:
        canon = _norm(TEAM_NAME_ALIASES[key])
        if canon in _BY_NAME:
            return float(_BY_NAME[canon]["elo"])
    if name.upper() in _BY_CODE:
        return float(_BY_CODE[name.upper()]["elo"])
    return DEFAULT_SEED_ELO
