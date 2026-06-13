"""
EuroGoal Predictor - Configuration
"""
import os
from pathlib import Path

from dotenv import load_dotenv

# ─── Paths ────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent
DATABASE_PATH = BASE_DIR / "database.db"

# Load .env file from project root
load_dotenv(BASE_DIR.parent / ".env")

# ─── Football-Data.org API ────────────────────────────────
# Register for free at https://www.football-data.org/
# Place your API key in a .env file or set the environment variable
FOOTBALL_DATA_API_KEY = os.getenv("FOOTBALL_DATA_API_KEY", "")
FOOTBALL_DATA_BASE_URL = "https://api.football-data.org/v4"

# Supported competitions (football-data.org free tier codes)
COMPETITIONS = {
    "PL":  {"name": "Premier League",    "country": "England",  "understat_name": "EPL"},
    "PD":  {"name": "La Liga",           "country": "Spain",    "understat_name": "La_liga"},
    "BL1": {"name": "Bundesliga",        "country": "Germany",  "understat_name": "Bundesliga"},
    "SA":  {"name": "Serie A",           "country": "Italy",    "understat_name": "Serie_A"},
    "FL1": {"name": "Ligue 1",           "country": "France",   "understat_name": "Ligue_1"},
    "CL":  {"name": "Champions League",  "country": "Europe",   "understat_name": None},
}

# ─── Dixon-Coles Model Parameters ────────────────────────
# Time decay factor (phi): higher = more weight on recent matches
# Typical range: 0.001 (slow decay) to 0.005 (fast decay)
DC_TIME_DECAY_PHI = 0.003

# Number of historical seasons to use for parameter fitting
DC_HISTORY_SEASONS = 3

# ─── Monte Carlo Simulation ──────────────────────────────
MC_NUM_SIMULATIONS = 10_000
MC_MATCH_MINUTES = 90

# ─── CORS ─────────────────────────────────────────────────
# Comma-separated list of browser origins allowed to call the API.
# The frontend is served same-origin in production (static mount) and via the
# Vite dev proxy in development, so the defaults only cover local dev. Set the
# CORS_ALLOW_ORIGINS env var to override. NB: a wildcard "*" cannot be combined
# with credentialed requests, so credentials are auto-disabled if "*" is used.
CORS_ALLOW_ORIGINS = [
    o.strip()
    for o in os.getenv(
        "CORS_ALLOW_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173,http://localhost:3000,http://127.0.0.1:8000",
    ).split(",")
    if o.strip()
]

# ─── ELO Rating System ───────────────────────────────────
ELO_INITIAL_RATING = 1500
ELO_K_FACTOR = 20
ELO_HOME_ADVANTAGE = 100

# ─── API Rate Limits ─────────────────────────────────────
FOOTBALL_DATA_RATE_LIMIT = 10  # requests per minute
UNDERSTAT_REQUEST_DELAY = 2.0  # seconds between requests

# ─── The Odds API ──────────────────────────────────────────
THE_ODDS_API_KEY = os.getenv("THE_ODDS_API_KEY", "")
THE_ODDS_API_BASE_URL = "https://api.the-odds-api.com/v4"
THE_ODDS_API_RATE_LIMIT = 5  # requests per minute (free tier: 500/month)

# ─── API-Football (RapidAPI) ───────────────────────────────
API_FOOTBALL_KEY = os.getenv("API_FOOTBALL_KEY", "")
API_FOOTBALL_BASE_URL = "https://v3.football.api-sports.io"

# Competition code → The Odds API sport key mapping
ODDS_SPORT_KEYS = {
    "PL":  "soccer_epl",
    "PD":  "soccer_spain_la_liga",
    "BL1": "soccer_germany_bundesliga",
    "SA":  "soccer_italy_serie_a",
    "FL1": "soccer_france_ligue_one",
    "CL":  "soccer_uefa_champs_league",
}

# API-Football league IDs (used for /fixtures and /fixtures/lineups endpoints)
API_FOOTBALL_LEAGUE_IDS = {
    "PL":  39,    # Premier League
    "PD":  140,   # La Liga
    "BL1": 78,    # Bundesliga
    "SA":  135,   # Serie A
    "FL1": 61,    # Ligue 1
    "CL":  2,     # Champions League
}
