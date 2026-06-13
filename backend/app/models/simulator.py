"""
EuroGoal Predictor - Monte Carlo Match Simulation Engine
========================================================

Simulates football matches minute-by-minute using Bernoulli trials driven
by Poisson-derived per-minute goal probabilities.  All simulations are
fully vectorised with NumPy — no Python-level loop over the N simulation
runs — so the engine can comfortably process 10 000+ simulations in
fractions of a second.

Simulation model
----------------
For a 90-minute match with expected goals ``lambda`` (home) and ``mu`` (away):

    P(home goal in minute t) = lambda_t / 90
    P(away goal in minute t) = mu_t     / 90

where ``lambda_t`` and ``mu_t`` can vary dynamically based on in-match
tactical adjustments:

1. **Stamina decay** (after minute 70):
   The defending team's parameter degrades along a *bounded linear ramp*
   (0 at minute 70 → the full decay factor at full time), effectively
   boosting the opponent's scoring chance late on without compounding.

2. **Park the bus** (after a configurable minute, if a team leads):
   The *leading* team's attack rate drops by 30 %, reflecting ultra-
   defensive play to protect the lead.

3. **Red cards** (stochastic):
   Each minute there is a small probability of a red card event for
   either team, which permanently reduces that team's attack by 20 %
   and defense by 15 % for the remainder of the match.

Each minute is a Bernoulli trial across all simulations simultaneously,
producing a ``(num_simulations,)``-shaped boolean array of goal events.

Output
------
A ``SimulationResult`` dataclass containing:
    - Win / draw / loss probabilities
    - An 8×8 score-probability matrix
    - Expected goals for each team
    - Over/Under probabilities for common lines
    - Top-5 most likely exact scores
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from app.config import MC_MATCH_MINUTES, MC_NUM_SIMULATIONS

logger = logging.getLogger(__name__)

# Maximum goals per team tracked in the score matrix.
_MAX_GOALS: int = 7


@dataclass
class SimulationResult:
    """Container for Monte Carlo simulation outputs.

    Attributes
    ----------
    home_win_prob : float
        Probability of a home win.
    draw_prob : float
        Probability of a draw.
    away_win_prob : float
        Probability of an away win.
    score_matrix : np.ndarray
        (8 × 8) matrix of exact-score probabilities.  Entry [i, j] is
        P(home = i, away = j).
    expected_home_goals : float
        Mean home goals across all simulations.
    expected_away_goals : float
        Mean away goals across all simulations.
    over_under : dict[str, float]
        Over/Under probabilities for standard lines.
        Keys: ``"O0.5"``, ``"U0.5"``, ``"O1.5"``, ``"U1.5"``, etc.
    most_likely_scores : list[tuple[int, int, float]]
        Top-5 most probable exact scores as ``(home, away, probability)``.
    """

    home_win_prob: float
    draw_prob: float
    away_win_prob: float
    score_matrix: np.ndarray
    expected_home_goals: float
    expected_away_goals: float
    over_under: Dict[str, float] = field(default_factory=dict)
    most_likely_scores: List[Tuple[int, int, float]] = field(default_factory=list)


class MonteCarloSimulator:
    """Vectorised Monte Carlo minute-step match simulator.

    Parameters
    ----------
    num_simulations : int, optional
        Number of independent match simulations to run.
        Defaults to ``MC_NUM_SIMULATIONS`` from config.
    match_minutes : int, optional
        Duration of a regulation match in minutes.
        Defaults to ``MC_MATCH_MINUTES`` from config.
    seed : int or None, optional
        Random seed for reproducibility.  ``None`` (default) uses
        non-deterministic seeding.

    Examples
    --------
    >>> sim = MonteCarloSimulator(num_simulations=50_000)
    >>> result = sim.simulate(lambda_home=1.8, mu_away=1.2)
    >>> print(f"Home win: {result.home_win_prob:.1%}")
    Home win: 48.3%
    """

    def __init__(
        self,
        num_simulations: int | None = None,
        match_minutes: int | None = None,
        seed: int | None = None,
    ) -> None:
        self.num_simulations: int = (
            num_simulations if num_simulations is not None else MC_NUM_SIMULATIONS
        )
        self.match_minutes: int = (
            match_minutes if match_minutes is not None else MC_MATCH_MINUTES
        )
        self.rng: np.random.Generator = np.random.default_rng(seed)

    # ── public API ────────────────────────────────────────────────────

    def simulate(
        self,
        lambda_home: float,
        mu_away: float,
        adjustments: Optional[Dict[str, Any]] = None,
    ) -> SimulationResult:
        """Run a full Monte Carlo simulation of a single match.

        Parameters
        ----------
        lambda_home : float
            Expected total goals for the home team over 90 minutes.
        mu_away : float
            Expected total goals for the away team over 90 minutes.
        adjustments : dict, optional
            Tactical / contextual adjustments applied during simulation.
            Supported keys:

            ``stamina_decay_home`` : float (0–1)
                Home-team fatigue.  After minute 70 the home team's
                *defensive* strength degrades along a linear ramp, reaching a
                factor of ``(1 + stamina_decay_home)`` at full time (i.e. the
                *away* team's effective attack rate rises by up to this much).
                The ramp is bounded — it does not compound minute over minute.
            ``stamina_decay_away`` : float (0–1)
                Symmetric for the away team's defensive degradation.
            ``park_the_bus_minute`` : int
                If a team leads by ≥ 1 goal after this minute, its
                attack rate is reduced by 30 %.
            ``red_card_probability`` : float
                Per-minute probability of a red card event for *each*
                team.  A red card reduces the affected team's attack
                by 20 % and defence by 15 % for the rest of the match.

        Returns
        -------
        SimulationResult
            Full simulation output.
        """
        adj = adjustments or {}
        n = self.num_simulations
        minutes = self.match_minutes

        logger.info(
            "Running %d simulations (λ_home=%.2f, μ_away=%.2f) …",
            n, lambda_home, mu_away,
        )

        # ── validate inputs ─────────────────────────────────────────
        if lambda_home < 0 or mu_away < 0:
            raise ValueError("Expected goals must be non-negative.")

        # ── parse adjustments ───────────────────────────────────────
        stamina_decay_home: float = adj.get("stamina_decay_home") or 0.0
        stamina_decay_away: float = adj.get("stamina_decay_away") or 0.0
        park_the_bus_minute: int = adj.get("park_the_bus_minute") or (minutes + 1)
        red_card_prob: float = adj.get("red_card_probability") or 0.0

        # ── per-minute base probabilities ───────────────────────────
        # Under a Poisson process the probability of ≥ 1 event in a
        # small interval Δt is approximately λ*Δt when λ*Δt ≪ 1.
        # Here Δt = 1/90 of a match.
        base_p_home: float = lambda_home / minutes  # P(home goal | minute)
        base_p_away: float = mu_away / minutes      # P(away goal | minute)

        # ── simulation arrays ───────────────────────────────────────
        # Running goal tallies for each simulation
        home_goals = np.zeros(n, dtype=np.int32)
        away_goals = np.zeros(n, dtype=np.int32)

        # Persistent per-simulation rate multipliers — modified ONLY by red
        # cards (they last for the rest of the match once triggered).
        # home_attack_mult  affects base_p_home (home scoring rate)
        # away_attack_mult  affects base_p_away (away scoring rate)
        # home_defense_weaken (>1) degrades home defence → boosts away scoring
        # away_defense_weaken (>1) degrades away defence → boosts home scoring
        home_attack_mult = np.ones(n, dtype=np.float64)
        away_attack_mult = np.ones(n, dtype=np.float64)
        home_defense_weaken = np.ones(n, dtype=np.float64)
        away_defense_weaken = np.ones(n, dtype=np.float64)

        # Fatigue ramps from minute 70 to full time; guard the denominator so
        # short (sub-70-minute) matches never divide by zero.
        fatigue_span: float = float(max(minutes - 70, 1))

        # ── minute-by-minute simulation loop ────────────────────────
        # NOTE: We loop over *minutes* (90 iterations) but NOT over
        # simulations — each minute processes all N simulations in a
        # single vectorised step.
        for minute in range(1, minutes + 1):
            # ── stamina decay: a bounded LINEAR ramp after minute 70 ─
            # Fatigue grows from 0 at minute 70 to the full decay factor at
            # the final whistle.  This is recomputed fresh each minute (a
            # scalar in [0, decay]); it deliberately does NOT compound minute
            # over minute, so the effect stays bounded by (1 + decay).
            ramp = (minute - 70) / fatigue_span if minute > 70 else 0.0
            home_fatigue = 1.0 + stamina_decay_home * ramp  # weakens home defence
            away_fatigue = 1.0 + stamina_decay_away * ramp  # weakens away defence

            # ── park the bus ────────────────────────────────────────
            # If a team leads by ≥ 1 after park_the_bus_minute, its
            # attack rate drops by 30 % for this minute.
            ptb_home_factor = np.ones(n, dtype=np.float64)
            ptb_away_factor = np.ones(n, dtype=np.float64)
            if minute >= park_the_bus_minute:
                # Home team leading → home attacks less
                home_leading = home_goals > away_goals
                ptb_home_factor[home_leading] = 0.7
                # Away team leading → away attacks less
                away_leading = away_goals > home_goals
                ptb_away_factor[away_leading] = 0.7

            # ── red card events ─────────────────────────────────────
            # Each team has an independent small probability of
            # receiving a red card each minute.
            if red_card_prob > 0:
                # Home red cards this minute
                home_red = self.rng.random(n) < red_card_prob
                if home_red.any():
                    # Red card reduces attack by 20 %, defence by 15 %
                    home_attack_mult[home_red] *= 0.80
                    home_defense_weaken[home_red] *= (1.0 + 0.15)

                # Away red cards this minute
                away_red = self.rng.random(n) < red_card_prob
                if away_red.any():
                    away_attack_mult[away_red] *= 0.80
                    away_defense_weaken[away_red] *= (1.0 + 0.15)

            # ── effective per-minute goal probabilities ─────────────
            # Home scoring depends on the AWAY team's defence: red-card
            # weakening × away fatigue.  Away scoring depends on the HOME
            # team's defence symmetrically.
            p_home = (
                base_p_home
                * home_attack_mult
                * (away_defense_weaken * away_fatigue)
                * ptb_home_factor
            )
            p_away = (
                base_p_away
                * away_attack_mult
                * (home_defense_weaken * home_fatigue)
                * ptb_away_factor
            )

            # Clamp probabilities to [0, 1]
            np.clip(p_home, 0.0, 1.0, out=p_home)
            np.clip(p_away, 0.0, 1.0, out=p_away)

            # ── Bernoulli trials ────────────────────────────────────
            home_scored = self.rng.random(n) < p_home
            away_scored = self.rng.random(n) < p_away

            home_goals += home_scored.astype(np.int32)
            away_goals += away_scored.astype(np.int32)

        # ── aggregate results ───────────────────────────────────────
        return self._aggregate(home_goals, away_goals, n)

    # ── private helpers ───────────────────────────────────────────────

    def _aggregate(
        self,
        home_goals: np.ndarray,
        away_goals: np.ndarray,
        n: int,
    ) -> SimulationResult:
        """Aggregate raw simulation goal arrays into a SimulationResult.

        Parameters
        ----------
        home_goals : np.ndarray of int, shape (n,)
            Final home goal count per simulation.
        away_goals : np.ndarray of int, shape (n,)
            Final away goal count per simulation.
        n : int
            Number of simulations.

        Returns
        -------
        SimulationResult
        """
        # ── outcome probabilities ───────────────────────────────────
        home_wins = np.sum(home_goals > away_goals)
        away_wins = np.sum(away_goals > home_goals)
        draws = np.sum(home_goals == away_goals)

        home_win_prob = float(home_wins / n)
        away_win_prob = float(away_wins / n)
        draw_prob = float(draws / n)

        # ── expected goals ──────────────────────────────────────────
        expected_home = float(np.mean(home_goals))
        expected_away = float(np.mean(away_goals))

        # ── score matrix ────────────────────────────────────────────
        # Cap goals at _MAX_GOALS for the matrix; anything above is
        # lumped into the last column/row.
        capped_home = np.minimum(home_goals, _MAX_GOALS)
        capped_away = np.minimum(away_goals, _MAX_GOALS)

        matrix_size = _MAX_GOALS + 1
        score_matrix = np.zeros((matrix_size, matrix_size), dtype=np.float64)

        # np.add.at performs unbuffered addition — correct for repeated
        # index pairs (unlike score_matrix[h, a] += 1 which doesn't).
        np.add.at(score_matrix, (capped_home, capped_away), 1)
        score_matrix /= n  # convert counts → probabilities

        # ── over/under probabilities ────────────────────────────────
        total_goals = home_goals + away_goals
        over_under: Dict[str, float] = {}
        for line in [0.5, 1.5, 2.5, 3.5, 4.5]:
            over = float(np.mean(total_goals > line))
            under = 1.0 - over
            over_under[f"O{line}"] = round(over, 4)
            over_under[f"U{line}"] = round(under, 4)

        # ── most likely scores (top 5) ──────────────────────────────
        flat = score_matrix.ravel()
        top_idx = np.argsort(flat)[::-1][:5]
        most_likely: List[Tuple[int, int, float]] = [
            (int(idx // matrix_size), int(idx % matrix_size), float(flat[idx]))
            for idx in top_idx
        ]

        return SimulationResult(
            home_win_prob=home_win_prob,
            draw_prob=draw_prob,
            away_win_prob=away_win_prob,
            score_matrix=score_matrix,
            expected_home_goals=expected_home,
            expected_away_goals=expected_away,
            over_under=over_under,
            most_likely_scores=most_likely,
        )
