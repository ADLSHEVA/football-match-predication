"""
EuroGoal Predictor — 2026 FIFA World Cup tournament simulator
=============================================================

A vectorised Monte-Carlo of the **whole** 48-team tournament.  Each of the
``num_simulations`` runs plays the complete group stage, ranks the 12
groups under the 2026 rules, fills the 32-team knockout bracket and plays
it through to a champion — all in NumPy, looping only over the (fixed,
small) set of fixtures and never over the simulations themselves.

Match model
-----------
National teams have no Understat xG and far too few matches to fit the
league Dixon-Coles model, so match goal expectations are derived from each
team's **Elo strength** instead.  For a tie between Elo ``Ra`` and ``Rb``::

    d      = (Ra - Rb) / 400
    lam_a  = BASE_GOALS * exp(+k * d)      # favourite scores more
    lam_b  = BASE_GOALS * exp(-k * d)      # underdog scores less

Goals are then independent Poisson draws.  Equal teams average
``BASE_GOALS`` each (~1.35, a realistic World-Cup figure); the gap widens
monotonically with the Elo difference.  This is a deliberate,
well-behaved heuristic — documented as such — not a fitted xG model.

Knockout ties go to extra time (an extra ``ET_FRACTION`` of a match) and
then penalties, modelled as a near-coin-flip with a slight Elo lean.

Group-stage results that have **already been played** (passed in via
``played``) are fixed across every simulation, so probabilities sharpen
as the real tournament unfolds.

Bracket
-------
:data:`R32_TEMPLATE` is a fixed, balanced 16-match Round-of-32 layout in
which no group winner meets the runner-up of its own group, and the 12
winners are spread across the draw.  It is a faithful *structure* for the
2026 format but intentionally does **not** reproduce FIFA's full
"which third-placed team goes where" lookup table.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from app.config import MC_NUM_SIMULATIONS

logger = logging.getLogger(__name__)

# ── match-model constants ─────────────────────────────────────────────────
BASE_GOALS: float = 1.35      # expected goals for an evenly-matched side
ELO_GOAL_COEF: float = 0.40   # how strongly an Elo gap skews goal expectation
ET_FRACTION: float = 30.0 / 90.0   # extra-time is ~1/3 of a match
PEN_ELO_SCALE: float = 2000.0      # large ⇒ penalties are nearly a coin flip
_LAMBDA_LO, _LAMBDA_HI = 0.15, 5.0

# ── 2026 knockout bracket ─────────────────────────────────────────────────
# Qualifier specs: ("W", g) winner of group g, ("R", g) runner-up of group g,
# ("T", k) the k-th best third-placed team (0 = best).  Groups are 0..11 = A..L.
# 16 Round-of-32 matches; adjacent matches feed the next round.
R32_TEMPLATE: List[Tuple[Tuple[str, int], Tuple[str, int]]] = [
    (("W", 0),  ("R", 1)),   # M1   A1 v B2
    (("W", 2),  ("T", 0)),   # M2   C1 v 3rd
    (("W", 4),  ("R", 5)),   # M3   E1 v F2
    (("W", 6),  ("T", 1)),   # M4   G1 v 3rd
    (("W", 8),  ("R", 9)),   # M5   I1 v J2
    (("W", 10), ("T", 2)),   # M6   K1 v 3rd
    (("W", 1),  ("R", 0)),   # M7   B1 v A2
    (("W", 3),  ("T", 3)),   # M8   D1 v 3rd
    (("W", 5),  ("R", 4)),   # M9   F1 v E2
    (("W", 7),  ("T", 4)),   # M10  H1 v 3rd
    (("W", 9),  ("R", 8)),   # M11  J1 v I2
    (("W", 11), ("T", 5)),   # M12  L1 v 3rd
    (("R", 2),  ("R", 3)),   # M13  C2 v D2
    (("R", 6),  ("R", 7)),   # M14  G2 v H2
    (("R", 10), ("T", 6)),   # M15  K2 v 3rd
    (("R", 11), ("T", 7)),   # M16  L2 v 3rd
]


def _expected_goals(
    elo_a: np.ndarray, elo_b: np.ndarray, base_goals: float = BASE_GOALS
) -> Tuple[np.ndarray, np.ndarray]:
    """Vectorised Elo → (lambda_a, lambda_b) Poisson goal expectations."""
    d = (elo_a - elo_b) / 400.0
    lam_a = np.clip(base_goals * np.exp(ELO_GOAL_COEF * d), _LAMBDA_LO, _LAMBDA_HI)
    lam_b = np.clip(base_goals * np.exp(-ELO_GOAL_COEF * d), _LAMBDA_LO, _LAMBDA_HI)
    return lam_a, lam_b


def predict_fixture(
    elo_home: float,
    elo_away: float,
    base_goals: float = BASE_GOALS,
    max_goals: int = 7,
) -> Dict[str, Any]:
    """Single-match prediction from Elo strengths (the same goal model the
    tournament sim uses, evaluated analytically rather than by sampling).

    Returns 1X2 probabilities, the most-likely outcome and the most-likely
    exact scoreline.
    """
    from scipy.stats import poisson

    lam_h, lam_a = (float(x) for x in _expected_goals(
        np.array(elo_home), np.array(elo_away), base_goals
    ))
    goals = np.arange(max_goals + 1)
    pmf_h = poisson.pmf(goals, lam_h)
    pmf_a = poisson.pmf(goals, lam_a)
    matrix = np.outer(pmf_h, pmf_a)
    matrix /= matrix.sum()

    p_home = float(np.tril(matrix, -1).sum())   # home goals > away goals
    p_draw = float(np.trace(matrix))
    p_away = float(np.triu(matrix, 1).sum())

    if p_home >= p_draw and p_home >= p_away:
        result = "H"
    elif p_away >= p_draw and p_away >= p_home:
        result = "A"
    else:
        result = "D"

    # Most-likely exact scoreline *consistent with* the predicted outcome, so a
    # predicted home win never reports a level score (and a draw is always level).
    rows = np.arange(max_goals + 1)[:, None]
    cols = np.arange(max_goals + 1)[None, :]
    if result == "H":
        region = rows > cols
    elif result == "A":
        region = rows < cols
    else:
        region = rows == cols
    i, j = np.unravel_index(int(np.argmax(np.where(region, matrix, -1.0))), matrix.shape)

    return {
        "p_home": round(p_home, 4),
        "p_draw": round(p_draw, 4),
        "p_away": round(p_away, 4),
        "pred_result": result,
        "pred_home": int(i),
        "pred_away": int(j),
        "lam_home": round(lam_h, 3),
        "lam_away": round(lam_a, 3),
    }


class WorldCupSimulator:
    """Vectorised full-tournament Monte-Carlo for the 48-team World Cup.

    Parameters
    ----------
    num_simulations : int, optional
        Number of independent tournaments to simulate.  Defaults to
        ``MC_NUM_SIMULATIONS``.
    seed : int or None, optional
        Seed for reproducibility.
    """

    def __init__(self, num_simulations: int | None = None, seed: int | None = None) -> None:
        self.num_simulations = num_simulations if num_simulations is not None else MC_NUM_SIMULATIONS
        self.rng = np.random.default_rng(seed)

    # ── public API ─────────────────────────────────────────────────────────
    def simulate(
        self,
        teams: List[Dict[str, Any]],
        played: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """Run the tournament Monte-Carlo.

        Parameters
        ----------
        teams : list of dict
            Exactly 48 team dicts, each with ``name``, ``code``, ``flag``,
            ``group`` ("A".."L") and ``elo``.  Twelve groups of four.
        played : list of dict, optional
            Completed group-stage results to condition on.  Each dict needs
            ``home_team``, ``away_team``, ``home_goals``, ``away_goals``.
            Matches are located within their group by team name.

        Returns
        -------
        dict
            ``num_simulations``, ``teams`` (per-team probabilities, sorted by
            championship probability), ``groups`` (per-group standings ordered
            by mean points) and ``r32_template`` (the bracket layout).
        """
        n = self.num_simulations
        n_teams = len(teams)
        if n_teams != 48:
            logger.warning("Expected 48 teams, got %d — simulating anyway.", n_teams)

        # ── index teams & build group membership ────────────────────────────
        self.elo = np.array([float(t["elo"]) for t in teams], dtype=np.float64)
        name_to_idx = {t["name"]: i for i, t in enumerate(teams)}

        group_labels = sorted({t["group"] for t in teams})
        group_members: Dict[str, List[int]] = {g: [] for g in group_labels}
        for i, t in enumerate(teams):
            group_members[t["group"]].append(i)

        played_lookup = self._build_played_lookup(played, name_to_idx)

        logger.info(
            "Simulating %d World Cups: %d teams, %d groups, %d results fixed.",
            n, n_teams, len(group_labels), len(played_lookup),
        )

        # ── group stage ─────────────────────────────────────────────────────
        # Per-group results, collected as global team indices.
        winners = np.empty((n, len(group_labels)), dtype=np.int64)
        runners = np.empty((n, len(group_labels)), dtype=np.int64)
        thirds = np.empty((n, len(group_labels)), dtype=np.int64)
        thirds_key = np.empty((n, len(group_labels)), dtype=np.float64)

        points_sum = np.zeros(n_teams, dtype=np.float64)
        rank_sum = np.zeros(n_teams, dtype=np.float64)

        for gi, g in enumerate(group_labels):
            members = np.array(group_members[g], dtype=np.int64)
            order, key, points, ranks = self._play_group(members, played_lookup)
            members_by_rank = members[order]               # [n, k] global idx best→worst
            winners[:, gi] = members_by_rank[:, 0]
            runners[:, gi] = members_by_rank[:, 1]
            thirds[:, gi] = members_by_rank[:, 2]
            # key of the third-placed team (for best-third comparison across groups)
            thirds_key[:, gi] = np.take_along_axis(key, order[:, 2:3], axis=1)[:, 0]
            # accumulate per-team mean points / mean finishing rank
            idx2d = np.broadcast_to(members, (n, members.size))
            np.add.at(points_sum, idx2d, points)
            np.add.at(rank_sum, idx2d, ranks)

        # ── best eight third-placed teams ───────────────────────────────────
        third_order = np.argsort(-thirds_key, axis=1)      # groups, best third → worst
        top8_groups = third_order[:, :8]
        thirds_q = np.take_along_axis(thirds, top8_groups, axis=1)   # [n, 8] global idx

        # ── build Round-of-32 from the template ─────────────────────────────
        def resolve(spec: Tuple[str, int]) -> np.ndarray:
            kind, x = spec
            if kind == "W":
                return winners[:, x]
            if kind == "R":
                return runners[:, x]
            return thirds_q[:, x]   # "T"

        left = np.stack([resolve(l) for (l, r) in R32_TEMPLATE], axis=1)   # [n,16]
        right = np.stack([resolve(r) for (l, r) in R32_TEMPLATE], axis=1)  # [n,16]
        r32_participants = np.concatenate([left, right], axis=1)           # [n,32]

        # ── knockout rounds (each fully vectorised across simulations) ───────
        win_r32 = self._play_round(left, right)            # [n,16] → R16 field
        win_r16 = self._play_bracket_round(win_r32)        # [n,8]  → QF field
        win_qf = self._play_bracket_round(win_r16)         # [n,4]  → SF field
        win_sf = self._play_bracket_round(win_qf)          # [n,2]  → final
        champion, _runner_up = self._play(win_sf[:, 0], win_sf[:, 1])      # [n]

        # ── aggregate reach-counts per team ─────────────────────────────────
        bc = lambda arr: np.bincount(arr.ravel(), minlength=n_teams)
        cnt_advance = bc(r32_participants)     # reached knockout (top-2 or best-third)
        cnt_r16 = bc(win_r32)                  # won R32 → reached R16
        cnt_qf = bc(win_r16)
        cnt_sf = bc(win_qf)
        cnt_final = bc(win_sf)
        cnt_champ = bc(champion)
        cnt_group_winner = bc(winners)

        # ── assemble per-team stats ─────────────────────────────────────────
        team_stats: List[Dict[str, Any]] = []
        for i, t in enumerate(teams):
            team_stats.append({
                "name": t["name"],
                "code": t.get("code", ""),
                "flag": t.get("flag", ""),
                "group": t["group"],
                "elo": round(float(self.elo[i]), 1),
                "p_group_winner": round(cnt_group_winner[i] / n, 4),
                "p_advance": round(cnt_advance[i] / n, 4),
                "p_r16": round(cnt_r16[i] / n, 4),
                "p_qf": round(cnt_qf[i] / n, 4),
                "p_sf": round(cnt_sf[i] / n, 4),
                "p_final": round(cnt_final[i] / n, 4),
                "p_champion": round(cnt_champ[i] / n, 4),
                "avg_points": round(float(points_sum[i] / n), 2),
                "avg_rank": round(float(rank_sum[i] / n), 2),
            })

        groups_out: Dict[str, List[Dict[str, Any]]] = {}
        for g in group_labels:
            members_stats = [s for s in team_stats if s["group"] == g]
            members_stats.sort(key=lambda s: (-s["avg_points"], -s["p_advance"]))
            groups_out[g] = members_stats

        team_stats_sorted = sorted(team_stats, key=lambda s: -s["p_champion"])

        return {
            "num_simulations": n,
            "teams": team_stats_sorted,
            "groups": groups_out,
            "r32_template": [
                {"match": m + 1, "left": {"kind": l[0], "group": l[1]},
                 "right": {"kind": r[0], "group": r[1]}}
                for m, (l, r) in enumerate(R32_TEMPLATE)
            ],
        }

    # ── group stage ─────────────────────────────────────────────────────────
    def _play_group(
        self,
        members: np.ndarray,
        played_lookup: Dict[frozenset, Tuple[int, int, int]],
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        """Play one group's round-robin across all simulations.

        Returns ``(order, key, points, ranks)`` where ``order`` [n,k] sorts
        the group's local team slots best→worst, ``key`` is the tiebreak key,
        ``points``/``ranks`` are per local slot.
        """
        n = self.num_simulations
        k = members.size
        points = np.zeros((n, k), dtype=np.float64)
        gd = np.zeros((n, k), dtype=np.float64)
        gf = np.zeros((n, k), dtype=np.float64)

        for a in range(k):
            for b in range(a + 1, k):
                ga, gb = self._group_match(members[a], members[b], played_lookup)
                a_win = ga > gb
                b_win = gb > ga
                draw = ~(a_win | b_win)
                points[:, a] += np.where(a_win, 3.0, np.where(draw, 1.0, 0.0))
                points[:, b] += np.where(b_win, 3.0, np.where(draw, 1.0, 0.0))
                gd[:, a] += ga - gb
                gd[:, b] += gb - ga
                gf[:, a] += ga
                gf[:, b] += gb

        # Tiebreak key: points ≫ goal difference ≫ goals for, plus tiny random
        # jitter so exact ties resolve fairly rather than by team order.
        jitter = self.rng.random((n, k)) * 1e-3
        key = points * 1e6 + (gd + 256.0) * 1e3 + gf + jitter
        order = np.argsort(-key, axis=1)               # best → worst (local slots)

        # finishing rank (1 = winner) per local slot
        ranks = np.empty((n, k), dtype=np.float64)
        np.put_along_axis(ranks, order, np.arange(1, k + 1, dtype=np.float64)[None, :].repeat(n, 0), axis=1)
        return order, key, points, ranks

    def _group_match(
        self,
        idx_a: int,
        idx_b: int,
        played_lookup: Dict[frozenset, Tuple[int, int, int]],
    ) -> Tuple[np.ndarray, np.ndarray]:
        """Goals for one group fixture across all sims (fixed if already played)."""
        n = self.num_simulations
        fixed = played_lookup.get(frozenset((int(idx_a), int(idx_b))))
        if fixed is not None:
            ta, ga_val, gb_val = fixed
            # `fixed` stores goals oriented to a canonical team; flip if needed.
            if ta == int(idx_a):
                return np.full(n, ga_val, dtype=np.float64), np.full(n, gb_val, dtype=np.float64)
            return np.full(n, gb_val, dtype=np.float64), np.full(n, ga_val, dtype=np.float64)

        lam_a, lam_b = _expected_goals(
            np.full(n, self.elo[idx_a]), np.full(n, self.elo[idx_b])
        )
        return (self.rng.poisson(lam_a).astype(np.float64),
                self.rng.poisson(lam_b).astype(np.float64))

    # ── knockout ──────────────────────────────────────────────────────────
    def _play(self, idx_a: np.ndarray, idx_b: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """Single knockout tie across all sims → (winner_idx, loser_idx)."""
        ea, eb = self.elo[idx_a], self.elo[idx_b]
        lam_a, lam_b = _expected_goals(ea, eb)
        ga = self.rng.poisson(lam_a).astype(np.int64)
        gb = self.rng.poisson(lam_b).astype(np.int64)

        # extra time for level ties
        tie = ga == gb
        if tie.any():
            ga = ga + np.where(tie, self.rng.poisson(lam_a * ET_FRACTION), 0)
            gb = gb + np.where(tie, self.rng.poisson(lam_b * ET_FRACTION), 0)

        a_wins = ga > gb
        # penalties for anything still level — near coin-flip with a slight Elo lean
        tie = ga == gb
        if tie.any():
            pa = 1.0 / (1.0 + np.power(10.0, -(ea - eb) / PEN_ELO_SCALE))
            pen_a = self.rng.random(idx_a.shape[0]) < pa
            a_wins = np.where(tie, pen_a, a_wins)

        winner = np.where(a_wins, idx_a, idx_b)
        loser = np.where(a_wins, idx_b, idx_a)
        return winner, loser

    def _play_round(self, left: np.ndarray, right: np.ndarray) -> np.ndarray:
        """Play a round given explicit left/right fields → winners [n, m]."""
        m = left.shape[1]
        winners = np.empty_like(left)
        for j in range(m):
            winners[:, j], _ = self._play(left[:, j], right[:, j])
        return winners

    def _play_bracket_round(self, field: np.ndarray) -> np.ndarray:
        """Play a round where adjacent columns meet → winners [n, m//2]."""
        return self._play_round(field[:, 0::2], field[:, 1::2])

    # ── helpers ─────────────────────────────────────────────────────────────
    @staticmethod
    def _build_played_lookup(
        played: Optional[List[Dict[str, Any]]],
        name_to_idx: Dict[str, int],
    ) -> Dict[frozenset, Tuple[int, int, int]]:
        """Map {team_a_idx, team_b_idx} → (team_a_idx, goals_a, goals_b)."""
        lookup: Dict[frozenset, Tuple[int, int, int]] = {}
        if not played:
            return lookup
        for m in played:
            h, a = m.get("home_team"), m.get("away_team")
            hg, ag = m.get("home_goals"), m.get("away_goals")
            if h not in name_to_idx or a not in name_to_idx:
                continue
            if hg is None or ag is None:
                continue
            hi, ai = name_to_idx[h], name_to_idx[a]
            lookup[frozenset((hi, ai))] = (hi, int(hg), int(ag))
        return lookup
