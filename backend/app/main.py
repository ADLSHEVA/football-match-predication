"""
EuroGoal Predictor — FastAPI Application Entry Point
=====================================================
Brighton/Starlizard-style quantitative football match prediction system.

Startup sequence:
1. Initialize SQLite database (create tables if needed)
2. Load Dixon-Coles model parameters from DB
3. Initialize ELO rating system from DB
4. Register API routes
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import BASE_DIR, DATABASE_PATH, CORS_ALLOW_ORIGINS
from app.database.db import Database
from app.models.dixon_coles import DixonColesModel
from app.models.elo import EloRatingSystem
from app.models.simulator import MonteCarloSimulator
from app.services.football_data import FootballDataClient
from app.services.scraper import UnderstatScraper
from app.services.sync import DataSyncService
from app.services.odds import OddsService
from app.services.api_football import ApiFootballService
from app.services.world_cup_service import WorldCupService
from app.routes.api import create_router

# ─── Logging ──────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("eurogoal")


# ─── Application State (shared singletons) ───────────────
class AppState:
    """Container for shared application-level singletons."""
    db: Database
    dixon_coles: DixonColesModel
    elo: EloRatingSystem
    simulator: MonteCarloSimulator
    fd_client: FootballDataClient
    scraper: UnderstatScraper
    odds_service: OddsService
    api_football_service: ApiFootballService
    world_cup_service: WorldCupService
    sync_service: DataSyncService


state = AppState()


# ─── Lifespan (startup / shutdown) ────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan handler.
    - On startup: initialize DB, load models, prepare services.
    - On shutdown: clean up resources.
    """
    logger.info("🚀 Starting EuroGoal Predictor backend...")

    # 1. Database
    state.db = Database(str(DATABASE_PATH))
    state.db.initialize()
    logger.info("✅ Database initialized at %s", DATABASE_PATH)

    # 2. Prediction models
    state.dixon_coles = DixonColesModel()
    state.elo = EloRatingSystem()
    state.simulator = MonteCarloSimulator()

    # Load existing ELO ratings from database
    teams = state.db.get_all_teams()
    for team in teams:
        if team.get("elo_rating"):
            state.elo.ratings[team["name"]] = team["elo_rating"]
    logger.info("✅ Loaded ELO ratings for %d teams", len(teams))

    # Load Dixon-Coles parameters if available
    params = state.db.get_all_model_params()
    if params:
        for p in params:
            state.dixon_coles.attack_[p["team"]] = p["attack"]
            state.dixon_coles.defense_[p["team"]] = p["defense"]
        state.dixon_coles.is_fitted_ = True
        logger.info("✅ Loaded Dixon-Coles params for %d teams", len(params))
    else:
        logger.warning("⚠️  No Dixon-Coles parameters found. Run /api/sync first.")

    # 3. Data services
    async with (
        FootballDataClient() as fd_client,
        UnderstatScraper() as scraper,
        OddsService() as odds_service,
        ApiFootballService() as api_football_service,
    ):
        state.fd_client = fd_client
        state.scraper = scraper
        state.odds_service = odds_service
        state.api_football_service = api_football_service
        state.world_cup_service = WorldCupService(fd_client=state.fd_client, db=state.db)
        state.sync_service = DataSyncService(
            db=state.db,
            fd_client=state.fd_client,
            scraper=state.scraper,
        )
        logger.info("✅ Data services initialized")

        # Make state accessible from request handlers
        app.state.eurogoal = state

        logger.info("🏟️  EuroGoal Predictor is ready!")
        yield

        # Shutdown
        logger.info("🛑 Shutting down EuroGoal Predictor...")


# ─── Create App ──────────────────────────────────────────
app = FastAPI(
    title="EuroGoal Predictor",
    description=(
        "Brighton/Starlizard-style quantitative football match prediction API. "
        "Combines xG-Dixon-Coles models, ELO ratings, and Monte Carlo simulation "
        "with real-time Human-in-the-Loop situational adjustments."
    ),
    version="3.0.0",
    lifespan=lifespan,
)

# ─── CORS (allow React frontend) ─────────────────────────
# Use an explicit origin allow-list (configurable via CORS_ALLOW_ORIGINS).
# A wildcard origin combined with credentials is rejected by browsers, so if
# "*" is configured we disable credentials to keep the policy valid.
_cors_allow_all = "*" in CORS_ALLOW_ORIGINS
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ALLOW_ORIGINS,
    allow_credentials=not _cors_allow_all,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Register Routes ─────────────────────────────────────
router = create_router()
app.include_router(router, prefix="/api")




# ─── Serve Frontend Static Files ─────────────────────────
frontend_dist = BASE_DIR.parent / "frontend" / "dist"
if frontend_dist.exists():
    app.mount("/", StaticFiles(directory=str(frontend_dist), html=True), name="frontend")
    logger.info("✅ Mounted frontend static files from %s", frontend_dist)
else:
    logger.warning("⚠️  Frontend dist directory not found at %s. Run 'npm run build' in frontend first.", frontend_dist)

