"""
EuroGoal Predictor — World Cup data service
============================================

Assembles the 2026 World Cup tournament state and drives both the
:class:`~app.models.world_cup.WorldCupSimulator` (championship odds) and the
per-match prediction / results layer.

Data strategy (live-first with graceful fallback)
-------------------------------------------------
1. **football-data.org** is the primary source — it carries the real 2026
   draw, the full 104-match schedule with UTC kick-offs, and live results.
2. Team **strengths** can't be fit with Dixon-Coles (no xG, too few games),
   so each team is seeded with an Elo prior from :mod:`app.data.world_cup_2026`
   and nudged by finished results via :class:`EloRatingSystem`.
3. If live data is unavailable/incomplete, fall back to the built-in seed
   field so the module always works offline.

Predictions & learning
-----------------------
For every fixture we produce a **walk-forward** prediction: team strengths
are replayed from the seed prior forward through time, so each match is
predicted using only the results that preceded it.  Predictions are locked in
the DB and settled against the real score, giving an honest predicted-vs-actual
record.  The goal model's ``BASE_GOALS`` is **recalibrated** from observed
scores (shrunk toward the prior), and a result/exact-score/Brier scoreboard
measures how the predictions track reality.
"""

from __future__ import annotations

import logging
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from app.data.world_cup_2026 import (
    WORLD_CUP_SEASON,
    get_seed_elo,
    get_seed_team,
    get_seed_teams,
)
from app.models.elo import EloRatingSystem
from app.models.world_cup import BASE_GOALS, WorldCupSimulator, predict_fixture

logger = logging.getLogger("eurogoal.worldcup")

_FINISHED_STATUSES = {"FINISHED"}
_LIVE_STATUSES = {"IN_PLAY", "PAUSED", "LIVE"}
_STATE_TTL_SECONDS = 10 * 60          # cache assembled state for 10 minutes
_CALIBRATION_PRIOR_WEIGHT = 30.0      # match-equivalents of weight on the prior
_CET_OFFSET_HOURS = 2                 # Central European Summer Time (Jun–Jul)


class WorldCupService:
    """Builds World Cup state, runs the championship Monte-Carlo, and tracks
    per-match predictions vs results.

    Parameters
    ----------
    fd_client : FootballDataClient
        Shared, already-opened football-data.org client (primary source).
    db : Database, optional
        Used to persist/lock pre-match predictions.
    season : int
        Tournament season (default 2026).
    """

    def __init__(self, fd_client: Any, db: Any = None, season: int = WORLD_CUP_SEASON) -> None:
        self._fd = fd_client
        self._db = db
        self._season = season
        self._state_cache: Optional[Dict[str, Any]] = None
        self._state_cache_ts: float = 0.0
        self._sim_cache: Dict[str, Dict[str, Any]] = {}

    # ── public API ─────────────────────────────────────────────────────────
    async def get_tournament_state(self, force_refresh: bool = False) -> Dict[str, Any]:
        """Return the assembled tournament state (teams, groups, fixtures,
        played results, predictions, accuracy). Cached for 10 minutes."""
        now = time.time()
        if (
            not force_refresh
            and self._state_cache is not None
            and (now - self._state_cache_ts) < _STATE_TTL_SECONDS
        ):
            return self._state_cache

        state = await self._assemble_state()
        self._state_cache = state
        self._state_cache_ts = now
        self._sim_cache.clear()
        return state

    def run_simulation(
        self,
        state: Dict[str, Any],
        num_simulations: Optional[int] = None,
        seed: Optional[int] = 2026,
    ) -> Dict[str, Any]:
        """Run (or return a cached) full-tournament Monte-Carlo for ``state``.

        A **fixed default seed** makes the projected bracket reproducible: it
        changes only when the inputs change (new results → new strengths), not
        from run-to-run Monte-Carlo noise between near-equal teams.
        """
        sig = f"{seed}|{self._state_signature(state, num_simulations)}"
        if sig in self._sim_cache:
            return self._sim_cache[sig]

        sim = WorldCupSimulator(num_simulations=num_simulations, seed=seed)
        result = sim.simulate(state["teams"], played=state.get("played"))
        result["source"] = state.get("source")
        result["matches_played"] = state.get("matches_played", 0)
        self._sim_cache[sig] = result
        return result

    @property
    def is_configured(self) -> bool:
        return bool(getattr(self._fd, "_api_key", ""))

    # ── state assembly ───────────────────────────────────────────────────────
    async def _assemble_state(self) -> Dict[str, Any]:
        wc_matches: List[Dict[str, Any]] = []
        if self.is_configured:
            try:
                wc_matches = await self._fd.get_world_cup_matches()
            except Exception as e:   # network / provider / parsing — degrade gracefully
                logger.warning("World Cup live fetch failed, using seed data: %s", e)
                wc_matches = []

        groups = self._groups_from_matches(wc_matches)
        if self._is_valid_structure(groups):
            teams = self._teams_from_groups(groups)
            fixtures = self._build_display_fixtures(wc_matches)
            source = "live"
        else:
            teams = get_seed_teams()
            fixtures = []
            source = "seed"

        played = self._played_from_fixtures(fixtures)
        teams = self._apply_results_to_elo(teams, played)

        analysis = self._compute_predictions(fixtures, teams)

        return {
            "source": source,
            "season": self._season,
            "teams": teams,
            "played": played,
            "fixtures": fixtures,
            "accuracy": analysis["accuracy"],
            "calibration": analysis["calibration"],
            "matches_played": len(played),
            "configured": self.is_configured,
        }

    @staticmethod
    def _groups_from_matches(matches: List[Dict[str, Any]]) -> Dict[str, List[str]]:
        """Derive {group_label: [team, ...]} from the group-stage fixtures."""
        groups: Dict[str, set] = {}
        for m in matches:
            if m.get("stage") != "GROUP_STAGE":
                continue
            label = m.get("group")
            if not label:
                continue
            for name in (m.get("home_team"), m.get("away_team")):
                if name:
                    groups.setdefault(label, set()).add(name)
        return {g: sorted(v) for g, v in groups.items()}

    @staticmethod
    def _is_valid_structure(groups: Dict[str, List[str]]) -> bool:
        if len(groups) != 12:
            return False
        sizes = [len(v) for v in groups.values()]
        return all(3 <= s <= 4 for s in sizes) and 44 <= sum(sizes) <= 48

    @staticmethod
    def _teams_from_groups(groups: Dict[str, List[str]]) -> List[Dict[str, Any]]:
        teams: List[Dict[str, Any]] = []
        for label in sorted(groups.keys()):
            for name in groups[label]:
                seed = get_seed_team(name)
                teams.append({
                    "name": name,
                    "code": seed["code"] if seed else name[:3].upper(),
                    "flag": seed["flag"] if seed else "",
                    "group": label,
                    "elo": float(seed["elo"]) if seed else get_seed_elo(name),
                })
        return teams

    def _build_display_fixtures(self, matches: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Normalise all 104 matches for the schedule/results UI."""
        out: List[Dict[str, Any]] = []
        for m in matches:
            h, a = m.get("home_team"), m.get("away_team")
            hs = get_seed_team(h) if h else None
            as_ = get_seed_team(a) if a else None
            status = m.get("status") or "SCHEDULED"
            out.append({
                "fd_id": m.get("fd_id"),
                "utc_date": m.get("date"),
                "cet": self._to_cet(m.get("date")),
                "matchday": m.get("matchday"),
                "stage": m.get("stage"),
                "group": m.get("group"),
                "home_team": h,
                "away_team": a,
                "home_flag": hs["flag"] if hs else "",
                "away_flag": as_["flag"] if as_ else "",
                "home_goals": m.get("home_goals"),
                "away_goals": m.get("away_goals"),
                "status": status,
                "finished": status in _FINISHED_STATUSES,
                "live": status in _LIVE_STATUSES,
                "winner": m.get("winner"),
            })
        out.sort(key=lambda x: x.get("utc_date") or "")
        return out

    @staticmethod
    def _played_from_fixtures(fixtures: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Finished group-stage results (these condition the tournament sim)."""
        played: List[Dict[str, Any]] = []
        for f in fixtures:
            if f.get("stage") != "GROUP_STAGE" or not f.get("finished"):
                continue
            if f.get("home_goals") is None or f.get("away_goals") is None:
                continue
            if not f.get("home_team") or not f.get("away_team"):
                continue
            played.append({
                "home_team": f["home_team"],
                "away_team": f["away_team"],
                "home_goals": int(f["home_goals"]),
                "away_goals": int(f["away_goals"]),
                "date": f.get("utc_date", ""),
            })
        return played

    @staticmethod
    def _apply_results_to_elo(
        teams: List[Dict[str, Any]],
        played: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Seed Elo from the prior, then update from finished results (neutral
        venue → no home-advantage term)."""
        if not played:
            return teams
        elo = EloRatingSystem(home_advantage=0.0)
        elo.ratings = {t["name"]: float(t["elo"]) for t in teams}
        for m in sorted(played, key=lambda x: x.get("date", "")):
            if m["home_team"] in elo.ratings and m["away_team"] in elo.ratings:
                elo.update(m["home_team"], m["away_team"], m["home_goals"], m["away_goals"])
        for t in teams:
            t["elo"] = round(elo.get_rating(t["name"]), 1)
        return teams

    # ── predictions, calibration & accuracy ─────────────────────────────────
    def _compute_predictions(
        self,
        fixtures: List[Dict[str, Any]],
        teams: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Walk-forward predict every fixture, settle finished ones, and score
        accuracy. Mutates each fixture dict to attach its prediction."""
        finished = [
            f for f in fixtures
            if f.get("finished") and f.get("home_goals") is not None and f.get("away_goals") is not None
        ]
        base_cal, calibration = self._calibrate_base(finished)

        # Replay strengths forward from the seed prior.
        elo = EloRatingSystem(home_advantage=0.0)
        elo.ratings = {t["name"]: get_seed_elo(t["name"]) for t in teams}

        stored = self._db.get_wc_predictions() if self._db else {}

        n = res_ok = score_ok = 0
        brier = 0.0

        for f in sorted(fixtures, key=lambda x: x.get("utc_date") or ""):
            h, a = f.get("home_team"), f.get("away_team")
            if not h or not a:                      # knockout slot still TBD
                f["prediction"] = None
                f["result_correct"] = None
                f["score_correct"] = None
                continue

            rec = stored.get(f["fd_id"])
            if rec and rec.get("settled"):
                pred = {k: rec[k] for k in (
                    "p_home", "p_draw", "p_away", "pred_result", "pred_home", "pred_away")}
            else:
                pred = predict_fixture(elo.get_rating(h), elo.get_rating(a), base_goals=base_cal)

            f["prediction"] = {k: pred[k] for k in (
                "p_home", "p_draw", "p_away", "pred_result", "pred_home", "pred_away")}

            if f.get("finished") and f.get("home_goals") is not None:
                ah, ag = int(f["home_goals"]), int(f["away_goals"])
                actual = "H" if ah > ag else ("A" if ag > ah else "D")
                rc = pred["pred_result"] == actual
                sc = pred["pred_home"] == ah and pred["pred_away"] == ag
                f["result_correct"], f["score_correct"], f["actual_result"] = rc, sc, actual

                if self._db and not (rec and rec.get("settled")):
                    self._db.upsert_wc_prediction(
                        f["fd_id"], h, a, f.get("utc_date"), f.get("stage"), f.get("group"),
                        pred["p_home"], pred["p_draw"], pred["p_away"],
                        pred["pred_result"], pred["pred_home"], pred["pred_away"])
                    self._db.settle_wc_prediction(f["fd_id"], ah, ag, actual, rc, sc)

                n += 1
                res_ok += int(rc)
                score_ok += int(sc)
                brier += (
                    (pred["p_home"] - (actual == "H")) ** 2
                    + (pred["p_draw"] - (actual == "D")) ** 2
                    + (pred["p_away"] - (actual == "A")) ** 2
                )
                elo.update(h, a, ah, ag)            # advance strengths for later matches
            else:
                f["result_correct"] = None
                f["score_correct"] = None
                if self._db:
                    self._db.upsert_wc_prediction(
                        f["fd_id"], h, a, f.get("utc_date"), f.get("stage"), f.get("group"),
                        pred["p_home"], pred["p_draw"], pred["p_away"],
                        pred["pred_result"], pred["pred_home"], pred["pred_away"])

        accuracy = {
            "n": n,
            "result_correct": res_ok,
            "score_correct": score_ok,
            "result_hit_rate": round(res_ok / n, 4) if n else None,
            "score_hit_rate": round(score_ok / n, 4) if n else None,
            "brier": round(brier / n, 4) if n else None,   # 0=perfect, lower is better
        }
        return {"accuracy": accuracy, "calibration": calibration}

    @staticmethod
    def _calibrate_base(finished: List[Dict[str, Any]]) -> tuple[float, Dict[str, Any]]:
        """Shrink the per-team goal expectation toward the prior using observed
        scores. With few matches this stays near the prior; it adapts as more
        results arrive — the goal-model half of 'improve from results'."""
        n = len(finished)
        if n == 0:
            return BASE_GOALS, {
                "n_finished": 0, "obs_goals_per_team": None,
                "base_goals": round(BASE_GOALS, 3), "base_goals_prior": BASE_GOALS,
            }
        total = sum((f["home_goals"] + f["away_goals"]) for f in finished)
        obs_per_team = total / (2.0 * n)
        base_cal = (_CALIBRATION_PRIOR_WEIGHT * BASE_GOALS + total / 2.0) / (_CALIBRATION_PRIOR_WEIGHT + n)
        return base_cal, {
            "n_finished": n,
            "obs_goals_per_team": round(obs_per_team, 3),
            "base_goals": round(base_cal, 3),
            "base_goals_prior": BASE_GOALS,
        }

    # ── projected bracket ────────────────────────────────────────────────────
    @staticmethod
    def build_projected_bracket(sim_result: Dict[str, Any]) -> Dict[str, Any]:
        """Build a full knockout tree from the simulation's group projections.

        Group winners/runners-up are the mean-points leaders of each group;
        the eight best third-placed teams are the highest-mean-points thirds.
        Knockout winners are the model favourite of each tie (higher
        championship probability, Elo as tiebreak) — the model's modal path,
        not a guaranteed outcome.
        """
        groups: Dict[str, List[Dict[str, Any]]] = sim_result["groups"]
        labels = sorted(groups.keys())

        def slim(team: Dict[str, Any]) -> Dict[str, Any]:
            return {
                "name": team["name"], "code": team.get("code", ""),
                "flag": team.get("flag", ""), "elo": team.get("elo"),
                "p_champion": team.get("p_champion", 0.0),
            }

        thirds = [groups[l][2] for l in labels if len(groups[l]) >= 3]
        thirds_sorted = sorted(thirds, key=lambda t: -t["avg_points"])[:8]

        def resolve(spec: Dict[str, Any]) -> Dict[str, Any]:
            kind, x = spec["kind"], spec["group"]
            if kind == "W":
                return slim(groups[labels[x]][0])
            if kind == "R":
                return slim(groups[labels[x]][1])
            return slim(thirds_sorted[x]) if x < len(thirds_sorted) else {"name": "TBD"}

        r32 = [
            {"match": m["match"], "left": resolve(m["left"]), "right": resolve(m["right"])}
            for m in sim_result["r32_template"]
        ]

        def favourite(p: Dict[str, Any], q: Dict[str, Any]) -> Dict[str, Any]:
            return p if (p.get("p_champion", 0), p.get("elo", 0)) >= (q.get("p_champion", 0), q.get("elo", 0)) else q

        def winners(matches: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
            return [favourite(x["left"], x["right"]) for x in matches]

        def pair(teams: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
            return [{"left": teams[i], "right": teams[i + 1]} for i in range(0, len(teams), 2)]

        r16 = pair(winners(r32))
        qf = pair(winners(r16))
        sf = pair(winners(qf))
        final = pair(winners(sf))
        champion = winners(final)[0] if final else {"name": "TBD"}

        return {"r32": r32, "r16": r16, "qf": qf, "sf": sf, "final": final,
                "projected_champion": champion}

    # ── helpers ──────────────────────────────────────────────────────────────
    @staticmethod
    def _to_cet(utc_iso: Optional[str]) -> str:
        """Format a UTC ISO timestamp as Central European (CEST, UTC+2) 'MM-DD HH:MM'."""
        if not utc_iso:
            return ""
        try:
            dt = datetime.fromisoformat(utc_iso.replace("Z", "+00:00"))
            return (dt + timedelta(hours=_CET_OFFSET_HOURS)).strftime("%m-%d %H:%M")
        except Exception:
            return ""

    @staticmethod
    def _state_signature(state: Dict[str, Any], num_simulations: Optional[int]) -> str:
        teams_sig = ";".join(f"{t['name']}:{t['elo']}" for t in state.get("teams", []))
        return f"{num_simulations}|{state.get('matches_played')}|{hash(teams_sig)}"
