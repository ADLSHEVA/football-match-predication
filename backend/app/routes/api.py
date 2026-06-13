"""
EuroGoal Predictor — API Routes
================================
RESTful endpoints for the frontend to interact with prediction models,
data synchronization, and simulation engine.
"""

import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from app.config import COMPETITIONS

logger = logging.getLogger("eurogoal.api")


# ─── Request/Response Schemas ─────────────────────────────

class AdjustmentParams(BaseModel):
    """
    Human-in-the-Loop adjustment parameters for the match simulator.
    These mirror the frontend sliders and toggles.
    """
    home_attack_adj: float = Field(
        default=1.0, ge=0.5, le=1.5,
        description="Multiplier for home team attack strength (1.0 = no change, 0.7 = key striker out)"
    )
    home_defense_adj: float = Field(
        default=1.0, ge=0.5, le=1.5,
        description="Multiplier for home team defense (>1.0 = weaker defense, e.g. key CB injured)"
    )
    away_attack_adj: float = Field(
        default=1.0, ge=0.5, le=1.5,
        description="Multiplier for away team attack strength"
    )
    away_defense_adj: float = Field(
        default=1.0, ge=0.5, le=1.5,
        description="Multiplier for away team defense"
    )
    stamina_decay_home: float = Field(
        default=0.0, ge=0.0, le=0.3,
        description="Fatigue factor for home team (0 = fresh, 0.15 = midweek CL match)"
    )
    stamina_decay_away: float = Field(
        default=0.0, ge=0.0, le=0.3,
        description="Fatigue factor for away team"
    )
    park_the_bus_minute: Optional[int] = Field(
        default=None, ge=45, le=85,
        description="Minute after which a leading team shifts to ultra-defensive"
    )
    tactical_conservatism: float = Field(
        default=1.0, ge=0.5, le=1.5,
        description="Overall match tempo modifier (< 1.0 = cagey/defensive, > 1.0 = open/attacking)"
    )


class SimulateRequest(BaseModel):
    """Request body for the /simulate endpoint."""
    home_team: str
    away_team: str
    competition: str = "PL"
    adjustments: AdjustmentParams = AdjustmentParams()


class SyncRequest(BaseModel):
    """Request body for the /sync endpoint."""
    competition: str = "PL"
    season: str = "2025"


# ─── Router Factory ──────────────────────────────────────

def create_router() -> APIRouter:
    """Create and return the API router with all endpoints."""
    router = APIRouter(tags=["EuroGoal Predictor"])

    # ─── Health Check ─────────────────────────────────────

    @router.get("/health")
    async def health(request: Request):
        """Quick health check endpoint."""
        from app.config import FOOTBALL_DATA_API_KEY, THE_ODDS_API_KEY, API_FOOTBALL_KEY
        state = request.app.state.eurogoal
        return {
            "status": "ok",
            "service": "EuroGoal Predictor",
            "version": "3.0.0",
            "model_fitted": state.dixon_coles.is_fitted_ if hasattr(state, "dixon_coles") else False,
            "api_key_configured": bool(FOOTBALL_DATA_API_KEY),
            "odds_api_configured": bool(THE_ODDS_API_KEY),
            "api_football_configured": bool(API_FOOTBALL_KEY),
        }

    # ─── Competitions ─────────────────────────────────────

    @router.get("/competitions")
    async def list_competitions():
        """List all supported competitions."""
        return {
            "competitions": [
                {"code": code, **info}
                for code, info in COMPETITIONS.items()
            ]
        }

    # ─── Matches ──────────────────────────────────────────

    @router.get("/matches/upcoming")
    async def get_upcoming_matches(
        request: Request,
        competition: str = "PL",
    ):
        """Get upcoming scheduled matches for a competition."""
        state = request.app.state.eurogoal
        matches = state.db.get_upcoming_matches(competition)
        return {"competition": competition, "matches": matches}

    @router.get("/matches/results")
    async def get_match_results(
        request: Request,
        competition: str = "PL",
        season: str = "2025",
        limit: int = 20,
    ):
        """Get recent finished match results."""
        state = request.app.state.eurogoal
        matches = state.db.get_matches(competition, season, status="FINISHED")
        # Return most recent first
        matches.sort(key=lambda m: m.get("date", ""), reverse=True)
        return {
            "competition": competition,
            "season": season,
            "matches": matches[:limit],
        }

    # ─── Predictions ──────────────────────────────────────

    @router.get("/predict/{home_team}/{away_team}")
    async def predict_match(
        request: Request,
        home_team: str,
        away_team: str,
        competition: str = "PL",
    ):
        """
        Get baseline prediction for a match using the Dixon-Coles model.
        No adjustments applied — this is the pure model output.
        """
        state = request.app.state.eurogoal
        dc = state.dixon_coles

        if not dc.is_fitted_:
            raise HTTPException(
                status_code=503,
                detail="Model not fitted yet. Run /api/sync then /api/model/fit first."
            )

        try:
            prediction = dc.predict(home_team, away_team)
        except KeyError as e:
            raise HTTPException(
                status_code=404,
                detail=f"Team not found in model: {e}"
            )

        # Also get ELO-based probability for comparison
        elo_probs = state.elo.get_win_probability(home_team, away_team)

        return {
            "home_team": home_team,
            "away_team": away_team,
            "competition": competition,
            "dixon_coles": {
                "home_win": round(prediction["home_win_prob"], 4),
                "draw": round(prediction["draw_prob"], 4),
                "away_win": round(prediction["away_win_prob"], 4),
                "expected_home_goals": round(prediction["expected_home_goals"], 2),
                "expected_away_goals": round(prediction["expected_away_goals"], 2),
                "score_matrix": prediction["score_matrix"].tolist(),
                "most_likely_scores": prediction.get("most_likely_scores", []),
            },
            "elo": {
                "home_win": round(elo_probs["home"], 4),
                "draw": round(elo_probs["draw"], 4),
                "away_win": round(elo_probs["away"], 4),
                "home_rating": round(state.elo.get_rating(home_team), 1),
                "away_rating": round(state.elo.get_rating(away_team), 1),
            },
        }

    # ─── Monte Carlo Simulation ───────────────────────────

    @router.post("/simulate")
    async def simulate_match(request: Request, body: SimulateRequest):
        """
        Run Monte Carlo simulation with Human-in-the-Loop adjustments.
        This is the core "Brighton analyst panel" endpoint.

        The frontend sends slider/toggle values as adjustment parameters,
        and this endpoint returns the updated prediction within milliseconds.
        """
        state = request.app.state.eurogoal
        dc = state.dixon_coles
        sim = state.simulator

        if not dc.is_fitted_:
            raise HTTPException(
                status_code=503,
                detail="Model not fitted yet. Run /api/sync then /api/model/fit first."
            )

        # 1. Get baseline expected goals from Dixon-Coles
        adj_for_dc = {
            "home_attack_adj": body.adjustments.home_attack_adj,
            "home_defense_adj": body.adjustments.home_defense_adj,
            "away_attack_adj": body.adjustments.away_attack_adj,
            "away_defense_adj": body.adjustments.away_defense_adj,
        }

        try:
            dc_pred = dc.predict(
                body.home_team, body.away_team, adjustments=adj_for_dc
            )
        except KeyError as e:
            raise HTTPException(status_code=404, detail=f"Team not found: {e}")

        # Apply tactical conservatism to base expected goals
        lambda_home = dc_pred["expected_home_goals"] * body.adjustments.tactical_conservatism
        mu_away = dc_pred["expected_away_goals"] * body.adjustments.tactical_conservatism

        # 2. Run Monte Carlo simulation with dynamic adjustments
        sim_adjustments = {
            "stamina_decay_home": body.adjustments.stamina_decay_home,
            "stamina_decay_away": body.adjustments.stamina_decay_away,
            "park_the_bus_minute": body.adjustments.park_the_bus_minute,
        }

        try:
            result = sim.simulate(lambda_home, mu_away, adjustments=sim_adjustments)
        except Exception as e:
            logger.error("Simulation error: %s", e, exc_info=True)
            raise HTTPException(status_code=500, detail=f"Simulation error: {e}")

        # 3. Return comprehensive result
        return {
            "home_team": body.home_team,
            "away_team": body.away_team,
            "adjustments_applied": body.adjustments.model_dump(),
            "simulation": {
                "num_simulations": sim.num_simulations,
                "home_win_prob": round(result.home_win_prob, 4),
                "draw_prob": round(result.draw_prob, 4),
                "away_win_prob": round(result.away_win_prob, 4),
                "expected_home_goals": round(result.expected_home_goals, 2),
                "expected_away_goals": round(result.expected_away_goals, 2),
                "score_matrix": result.score_matrix.tolist(),
                "most_likely_scores": result.most_likely_scores,
                "over_under": {
                    k: round(v, 4) for k, v in result.over_under.items()
                },
            },
            "dixon_coles_baseline": {
                "expected_home_goals": round(dc_pred["expected_home_goals"], 2),
                "expected_away_goals": round(dc_pred["expected_away_goals"], 2),
            },
        }

    # ─── Standings ────────────────────────────────────────

    @router.get("/standings/{competition}")
    async def get_standings(request: Request, competition: str):
        """Get current league standings from football-data.org."""
        state = request.app.state.eurogoal
        try:
            standings = await state.fd_client.get_standings(competition)
        except Exception as e:
            raise HTTPException(status_code=502, detail=f"Failed to fetch standings: {e}")
        return {"competition": competition, "standings": standings}

    # ─── Team Data ────────────────────────────────────────

    @router.get("/teams")
    async def get_teams(request: Request, competition: Optional[str] = None):
        """Get all teams with their ELO ratings and model parameters."""
        state = request.app.state.eurogoal
        teams = state.db.get_all_teams()
        if competition:
            filtered = [t for t in teams if t.get("competition") == competition]
            # Fall back to all teams if competition filter yields nothing
            teams = filtered if filtered else teams

        # Enrich with ELO and Dixon-Coles params
        for team in teams:
            name = team["name"]
            team["elo_rating"] = round(state.elo.get_rating(name), 1)
            team["attack"] = state.dixon_coles.attack_.get(name)
            team["defense"] = state.dixon_coles.defense_.get(name)

        # Sort by ELO rating descending
        teams.sort(key=lambda t: t.get("elo_rating", 0), reverse=True)
        return {"teams": teams}

    # ─── Model Operations ─────────────────────────────────

    @router.post("/model/fit")
    async def fit_model(request: Request, competition: str = "PL"):
        """
        Re-fit the Dixon-Coles model using stored match data with xG.
        Also recalculates ELO ratings from scratch.
        """
        import pandas as pd

        state = request.app.state.eurogoal
        dc = state.dixon_coles
        elo = state.elo

        # Fetch all finished matches
        matches = state.db.get_matches(competition, season=None, status="FINISHED")
        
        valid_matches = []
        for m in matches:
            if m.get("home_goals") is not None and m.get("away_goals") is not None:
                # Fallback to actual goals if xG is missing
                m["home_xg"] = m.get("home_xg") if m.get("home_xg") is not None else m["home_goals"]
                m["away_xg"] = m.get("away_xg") if m.get("away_xg") is not None else m["away_goals"]
                valid_matches.append(m)

        if len(valid_matches) < 20:
            raise HTTPException(
                status_code=400,
                detail=f"Not enough valid matches ({len(valid_matches)}). Need at least 20."
            )

        # Convert to DataFrame for Dixon-Coles fitting
        df = pd.DataFrame(valid_matches)
        df["date"] = pd.to_datetime(df["date"])

        logger.info("Fitting Dixon-Coles model on %d matches with xG data...", len(df))
        dc.fit(df)
        logger.info("✅ Dixon-Coles model fitted. Teams: %d", len(dc.attack_))

        # Save fitted params to DB
        for team in dc.attack_:
            state.db.upsert_model_params(
                team=team,
                competition=competition,
                attack=dc.attack_[team],
                defense=dc.defense_[team],
            )

        # Recalculate ELO from match history (chronological order)
        elo.reset()
        all_matches = state.db.get_matches(competition, season=None, status="FINISHED")
        all_matches.sort(key=lambda m: m.get("date", ""))
        for m in all_matches:
            if m.get("home_goals") is not None and m.get("away_goals") is not None:
                elo.update(m["home_team"], m["away_team"], m["home_goals"], m["away_goals"])

        # Save ELO to DB
        for team, rating in elo.get_all_ratings().items():
            state.db.update_team_elo(team, rating)

        logger.info("✅ ELO ratings recalculated for %d teams", len(elo.get_all_ratings()))

        return {
            "status": "ok",
            "matches_used": len(df),
            "teams_fitted": len(dc.attack_),
            "home_advantage": round(dc.home_adv_, 4) if dc.home_adv_ else None,
            "rho": round(dc.rho_, 4) if dc.rho_ else None,
        }

    @router.get("/model/accuracy")
    async def get_model_accuracy(request: Request):
        """Get historical prediction accuracy metrics."""
        state = request.app.state.eurogoal
        predictions = state.db.get_historical_predictions()

        if not predictions:
            return {"message": "No prediction history available yet."}

        # Calculate accuracy
        correct = 0
        total = 0
        for p in predictions:
            if p.get("actual_result") and p.get("predicted_result"):
                total += 1
                if p["actual_result"] == p["predicted_result"]:
                    correct += 1

        accuracy = correct / total if total > 0 else 0
        return {
            "total_predictions": total,
            "correct": correct,
            "accuracy": round(accuracy, 4),
            "recent_predictions": predictions[-20:],
        }

    # ─── Data Synchronization ─────────────────────────────

    @router.post("/sync")
    async def sync_data(request: Request, body: SyncRequest):
        """
        Synchronize match data from external sources.
        1. Fetch results from football-data.org (or CSV fallback)
        2. Fetch xG data from Understat
        3. Fetch upcoming fixtures
        """
        from app.config import FOOTBALL_DATA_API_KEY

        state = request.app.state.eurogoal
        sync = state.sync_service

        try:
            logger.info("Starting data sync for %s (season %s)...", body.competition, body.season)
            report = await sync.full_sync(body.competition, body.season)
            logger.info("✅ Sync complete: %s", report)

            # Warn if no API key (upcoming fixtures won't be synced)
            if not FOOTBALL_DATA_API_KEY:
                report["warning"] = (
                    "No FOOTBALL_DATA_API_KEY configured. Historical data loaded from CSV fallback. "
                    "Upcoming fixtures require an API key from https://www.football-data.org/"
                )

            return {"status": "ok", "report": report}
        except Exception as e:
            logger.error("❌ Sync failed: %s", e)
            raise HTTPException(status_code=502, detail=f"Sync failed: {str(e)}")

    # ─── Batch Predictions for Upcoming ───────────────────

    @router.get("/predictions/upcoming")
    async def predict_upcoming(request: Request, competition: str = "PL"):
        """Generate predictions for all upcoming matches in a competition."""
        state = request.app.state.eurogoal
        dc = state.dixon_coles

        if not dc.is_fitted_:
            raise HTTPException(status_code=503, detail="Model not fitted yet.")

        upcoming = state.db.get_upcoming_matches(competition)
        predictions = []

        for match in upcoming:
            try:
                pred = dc.predict(match["home_team"], match["away_team"])
                elo_pred = state.elo.get_win_probability(
                    match["home_team"], match["away_team"]
                )
                predictions.append({
                    "match_id": match.get("id"),
                    "date": match.get("date"),
                    "home_team": match["home_team"],
                    "away_team": match["away_team"],
                    "home_win": round(pred["home_win_prob"], 4),
                    "draw": round(pred["draw_prob"], 4),
                    "away_win": round(pred["away_win_prob"], 4),
                    "expected_home_goals": round(pred["expected_home_goals"], 2),
                    "expected_away_goals": round(pred["expected_away_goals"], 2),
                    "elo_home_win": round(elo_pred["home"], 4),
                    "home_elo": round(state.elo.get_rating(match["home_team"]), 1),
                    "away_elo": round(state.elo.get_rating(match["away_team"]), 1),
                })
            except KeyError:
                # Team not in model — skip
                continue

        return {"competition": competition, "predictions": predictions}

    # ─── Betting Odds ────────────────────────────────────

    @router.get("/odds/{home_team}/{away_team}")
    async def get_match_odds(
        request: Request,
        home_team: str,
        away_team: str,
        competition: str = "PL",
    ):
        """Get betting odds and value bet analysis for a specific match."""
        from app.config import ODDS_SPORT_KEYS, THE_ODDS_API_KEY

        state = request.app.state.eurogoal
        odds_service = state.odds_service

        if not THE_ODDS_API_KEY:
            return {
                "home_team": home_team,
                "away_team": away_team,
                "configured": False,
                "odds": [],
                "value_bets": [],
            }

        # Check cache first (4-hour TTL)
        cached = state.db.get_cached_odds(home_team, away_team, max_age_minutes=240)
        if cached:
            odds_data = cached
        else:
            sport_key = ODDS_SPORT_KEYS.get(competition, "soccer_epl")
            try:
                odds_data = await odds_service.get_odds_for_match(
                    sport_key, home_team, away_team
                )
                for entry in odds_data:
                    state.db.upsert_odds(**entry)
            except Exception as e:
                logger.warning("Odds API error: %s", e)
                odds_data = []

        # Calculate value bets
        dc = state.dixon_coles
        value_bets = []
        if dc.is_fitted_ and odds_data:
            try:
                pred = dc.predict(home_team, away_team)
                model_probs = {
                    "home": pred["home_win_prob"],
                    "draw": pred["draw_prob"],
                    "away": pred["away_win_prob"],
                }
            except KeyError:
                model_probs = None

            if model_probs:
                for entry in odds_data:
                    if entry.get("market") != "h2h":
                        continue
                    for outcome_key, odds_key in [
                        ("home", "home_odds"),
                        ("draw", "draw_odds"),
                        ("away", "away_odds"),
                    ]:
                        odds_val = entry.get(odds_key)
                        if odds_val and odds_val > 0:
                            implied = 1.0 / odds_val
                            ev = model_probs[outcome_key] - implied
                            kelly = (
                                (model_probs[outcome_key] * odds_val - 1)
                                / (odds_val - 1)
                                if odds_val > 1
                                else 0
                            )
                            value_bets.append({
                                "market": entry.get("market"),
                                "bookmaker": entry.get("bookmaker"),
                                "outcome": outcome_key,
                                "decimal_odds": round(odds_val, 2),
                                "model_prob": round(model_probs[outcome_key], 4),
                                "implied_prob": round(implied, 4),
                                "expected_value": round(ev, 4),
                                "kelly_fraction": round(max(kelly, 0), 4),
                                "is_value": ev > 0,
                            })

        return {
            "home_team": home_team,
            "away_team": away_team,
            "configured": True,
            "odds": odds_data,
            "value_bets": value_bets,
        }

    @router.get("/odds/batch")
    async def get_batch_odds(
        request: Request,
        competition: str = "PL",
    ):
        """Get odds for all upcoming matches in a competition."""
        from app.config import ODDS_SPORT_KEYS, THE_ODDS_API_KEY

        state = request.app.state.eurogoal
        odds_service = state.odds_service

        if not THE_ODDS_API_KEY:
            return {"configured": False, "matches": {}}

        sport_key = ODDS_SPORT_KEYS.get(competition, "soccer_epl")
        try:
            all_odds = await odds_service.get_odds(sport_key)
        except Exception as e:
            logger.warning("Batch odds fetch failed: %s", e)
            return {"configured": True, "matches": {}, "error": str(e)}

        # Group by match
        match_odds: dict[str, list] = {}
        for entry in all_odds:
            key = f"{entry['home_team']}|{entry['away_team']}"
            match_odds.setdefault(key, []).append(entry)

        return {"configured": True, "matches": match_odds}

    # ─── Head-to-Head ────────────────────────────────────

    @router.get("/h2h/{home_team}/{away_team}")
    async def get_h2h(
        request: Request,
        home_team: str,
        away_team: str,
    ):
        """Get head-to-head historical record between two teams."""
        from app.config import API_FOOTBALL_KEY

        state = request.app.state.eurogoal
        api_football = state.api_football_service

        if not API_FOOTBALL_KEY:
            return {
                "home_team": home_team,
                "away_team": away_team,
                "configured": False,
                "total_matches": 0,
                "home_wins": 0,
                "draws": 0,
                "away_wins": 0,
                "avg_home_goals": 0.0,
                "avg_away_goals": 0.0,
                "recent_results": [],
            }

        # Check cache first (24-hour TTL)
        cached = state.db.get_cached_h2h(home_team, away_team, max_age_hours=24)
        if not cached:
            try:
                results = await api_football.get_h2h(home_team, away_team, last=10)
                if results:
                    state.db.insert_h2h_results(home_team, away_team, results)
                    cached = state.db.get_cached_h2h(
                        home_team, away_team, max_age_hours=24
                    )
            except Exception as e:
                logger.warning("API-Football H2H error: %s", e)
                cached = []

        # Calculate summary stats
        home_wins = 0
        draws = 0
        away_wins = 0
        total_home_goals = 0
        total_away_goals = 0
        for r in cached:
            hg = r.get("home_goals")
            ag = r.get("away_goals")
            if hg is not None and ag is not None:
                total_home_goals += hg
                total_away_goals += ag
                if hg > ag:
                    home_wins += 1
                elif hg < ag:
                    away_wins += 1
                else:
                    draws += 1

        n = len(cached) or 1
        return {
            "home_team": home_team,
            "away_team": away_team,
            "configured": True,
            "total_matches": len(cached),
            "home_wins": home_wins,
            "draws": draws,
            "away_wins": away_wins,
            "avg_home_goals": round(total_home_goals / n, 2),
            "avg_away_goals": round(total_away_goals / n, 2),
            "recent_results": cached[:10],
        }

    # ─── Lineups & Formation ─────────────────────────────

    @router.get("/lineups/{home_team}/{away_team}")
    async def get_lineups_endpoint(
        request: Request,
        home_team: str,
        away_team: str,
        competition: str = "PL",
    ):
        """Get lineup and formation data for an upcoming match, plus formation matchup analysis."""
        from app.config import API_FOOTBALL_KEY, API_FOOTBALL_LEAGUE_IDS
        from app.models.formation_matrix import get_matchup_analysis

        state = request.app.state.eurogoal
        api_football = state.api_football_service

        if not API_FOOTBALL_KEY:
            return {
                "home_team": home_team,
                "away_team": away_team,
                "configured": False,
                "home": None,
                "away": None,
                "formation_analysis": None,
            }

        # Check cache first (24-hour TTL)
        cached = state.db.get_cached_lineups(home_team, away_team, max_age_hours=24)
        if cached:
            formation_analysis = None
            if cached.get("home_formation") and cached.get("away_formation"):
                formation_analysis = get_matchup_analysis(
                    cached["home_formation"], cached["away_formation"]
                )
            return {
                "home_team": home_team,
                "away_team": away_team,
                "configured": True,
                "fixture_id": cached.get("fixture_id"),
                "home": {
                    "formation": cached.get("home_formation"),
                    "start_xi": cached.get("home_startxi", []),
                    "coach": cached.get("home_coach"),
                } if cached.get("home_formation") else None,
                "away": {
                    "formation": cached.get("away_formation"),
                    "start_xi": cached.get("away_startxi", []),
                    "coach": cached.get("away_coach"),
                } if cached.get("away_formation") else None,
                "formation_analysis": formation_analysis,
            }

        # Fetch from API
        try:
            lineups_data = await api_football.get_lineups_for_match(home_team, away_team)
        except Exception as e:
            logger.warning("API-Football lineups error: %s", e)
            lineups_data = None

        if lineups_data:
            home_lineup = lineups_data.get("home")
            away_lineup = lineups_data.get("away")
            state.db.upsert_lineups(
                home_team=home_team,
                away_team=away_team,
                fixture_id=lineups_data.get("fixture_id"),
                home_formation=home_lineup.get("formation") if home_lineup else None,
                away_formation=away_lineup.get("formation") if away_lineup else None,
                home_startxi=home_lineup.get("start_xi", []) if home_lineup else [],
                away_startxi=away_lineup.get("start_xi", []) if away_lineup else [],
                home_coach=home_lineup.get("coach_name") if home_lineup else None,
                away_coach=away_lineup.get("coach_name") if away_lineup else None,
            )

            formation_analysis = None
            hf = home_lineup.get("formation") if home_lineup else None
            af = away_lineup.get("formation") if away_lineup else None
            if hf and af:
                formation_analysis = get_matchup_analysis(hf, af)

            return {
                "home_team": home_team,
                "away_team": away_team,
                "configured": True,
                "fixture_id": lineups_data.get("fixture_id"),
                "home": home_lineup,
                "away": away_lineup,
                "formation_analysis": formation_analysis,
            }

        # No data available (lineups not announced yet)
        return {
            "home_team": home_team,
            "away_team": away_team,
            "configured": True,
            "fixture_id": None,
            "home": None,
            "away": None,
            "formation_analysis": None,
        }

    # ─── World Cup 2026 ───────────────────────────────────

    @router.get("/worldcup/simulate")
    async def worldcup_simulate(
        request: Request,
        num_simulations: int = 20000,
        refresh: bool = False,
    ):
        """Run the full 2026 World Cup Monte Carlo and return everything the
        World Cup page needs: per-team championship odds, group standings with
        advancement probabilities, and a projected knockout bracket.

        Live fixtures/results (when an API key is configured) condition the
        simulation; otherwise the built-in 48-team seed field is used.
        """
        svc = request.app.state.eurogoal.world_cup_service
        # Clamp to keep a single request cheap and bounded.
        n = max(1000, min(int(num_simulations), 50000))

        state = await svc.get_tournament_state(force_refresh=refresh)
        result = svc.run_simulation(state, num_simulations=n)
        bracket = svc.build_projected_bracket(result)

        return {
            "source": result.get("source"),
            "season": state.get("season"),
            "configured": state.get("configured"),
            "matches_played": result.get("matches_played", 0),
            "num_simulations": result.get("num_simulations"),
            "teams": result["teams"],
            "groups": result["groups"],
            "bracket": bracket,
        }

    @router.get("/worldcup/schedule")
    async def worldcup_schedule(request: Request, refresh: bool = False):
        """Real World Cup schedule + results + per-match predictions.

        Returns every fixture (group + knockout) with UTC and Central-European
        kick-off times, live scores, the model's locked pre-match prediction
        (1X2 + most-likely scoreline) and — for finished matches — the actual
        result and whether the prediction was correct, plus an overall
        accuracy/calibration summary.
        """
        svc = request.app.state.eurogoal.world_cup_service
        state = await svc.get_tournament_state(force_refresh=refresh)
        return {
            "source": state.get("source"),
            "season": state.get("season"),
            "configured": state.get("configured"),
            "matches_played": state.get("matches_played", 0),
            "fixtures": state.get("fixtures", []),
            "accuracy": state.get("accuracy"),
            "calibration": state.get("calibration"),
        }

    @router.post("/worldcup/sync")
    async def worldcup_sync(request: Request):
        """Force a refresh of World Cup data from the live provider.

        Returns the data source actually used and how many group-stage
        results are now conditioning the simulation.
        """
        svc = request.app.state.eurogoal.world_cup_service
        try:
            state = await svc.get_tournament_state(force_refresh=True)
        except Exception as e:
            logger.error("World Cup sync failed: %s", e)
            raise HTTPException(status_code=502, detail=f"World Cup sync failed: {e}")
        return {
            "status": "ok",
            "source": state.get("source"),
            "configured": state.get("configured"),
            "matches_played": state.get("matches_played", 0),
            "teams_loaded": len(state.get("teams", [])),
        }

    return router
