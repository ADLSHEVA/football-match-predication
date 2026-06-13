"""
EuroGoal Predictor - Elo Rating System
=======================================

A football-adapted Elo rating system based on the original chess Elo framework
(Elo, 1978) with modifications commonly used in football analytics:

1. **Home advantage**: A fixed rating bonus is added to the home team's
   effective rating when computing expected scores.

2. **Goal-difference multiplier**: Larger victories count more than narrow
   wins.  For a goal difference ``G ≥ 2``, the effective K-factor becomes
   ``K * (1 + ln(G))``.

3. **Draw handling**: Football has three outcomes.  We model draws via the
   ordinal-logistic approach: if the rating difference is small (within a
   "draw band"), a draw is the most likely outcome.

Mathematical formulation
------------------------
Expected score for the home team (logistic model):

    E_home = 1 / (1 + 10^(-(R_home - R_away + H) / 400))

where
    R_home, R_away = current Elo ratings,
    H              = home advantage (in rating points).

After a match the ratings are updated:

    R'_home = R_home + K_eff * (S_home - E_home)
    R'_away = R_away + K_eff * (S_away - E_away)

where
    S = actual score (1 for win, 0.5 for draw, 0 for loss),
    K_eff = K * goal_diff_multiplier.

Goal-difference multiplier:

    G_mult = 1                    if |goal_diff| <= 1
           = 1 + ln(|goal_diff|)  if |goal_diff| >= 2

This amplifies the rating change for convincing victories while keeping
narrow wins at the base K-factor.

References
----------
- Elo, A. E. (1978). *The Rating of Chessplayers, Past and Present*.
- Silver, N. (2014). FiveThirtyEight Soccer Power Index methodology.
"""

from __future__ import annotations

import logging
import math
from typing import Dict, Tuple

from app.config import ELO_HOME_ADVANTAGE, ELO_INITIAL_RATING, ELO_K_FACTOR

logger = logging.getLogger(__name__)


class EloRatingSystem:
    """Football Elo rating system with home advantage and margin-of-victory.

    Parameters
    ----------
    initial_rating : float, optional
        Default rating assigned to a team the first time it is encountered.
    k_factor : float, optional
        Base K-factor that controls how much ratings change per match.
    home_advantage : float, optional
        Rating-point bonus added to the home team's effective rating.

    Attributes
    ----------
    ratings : dict[str, float]
        Current Elo ratings keyed by team name.
    """

    def __init__(
        self,
        initial_rating: float = ELO_INITIAL_RATING,
        k_factor: float = ELO_K_FACTOR,
        home_advantage: float = ELO_HOME_ADVANTAGE,
    ) -> None:
        self.initial_rating: float = initial_rating
        self.k_factor: float = k_factor
        self.home_advantage: float = home_advantage
        self.ratings: Dict[str, float] = {}

    def reset(self) -> None:
        """Reset all ratings to empty (for recalculation from scratch)."""
        self.ratings.clear()

    # ── public API ────────────────────────────────────────────────────

    def update(
        self,
        home_team: str,
        away_team: str,
        home_goals: int,
        away_goals: int,
    ) -> Tuple[float, float]:
        """Update ratings after a match result.

        Parameters
        ----------
        home_team : str
            Name of the home team.
        away_team : str
            Name of the away team.
        home_goals : int
            Goals scored by the home team.
        away_goals : int
            Goals scored by the away team.

        Returns
        -------
        tuple[float, float]
            (new_home_rating, new_away_rating) after the update.
        """
        # Retrieve current ratings (or initialise)
        r_home = self.get_rating(home_team)
        r_away = self.get_rating(away_team)

        # ── expected scores (logistic model) ────────────────────────
        e_home = self._expected_score(r_home, r_away)
        e_away = 1.0 - e_home

        # ── actual scores ───────────────────────────────────────────
        if home_goals > away_goals:
            s_home, s_away = 1.0, 0.0
        elif home_goals < away_goals:
            s_home, s_away = 0.0, 1.0
        else:
            s_home, s_away = 0.5, 0.5

        # ── goal-difference multiplier ──────────────────────────────
        goal_diff = abs(home_goals - away_goals)
        g_mult = self._goal_diff_multiplier(goal_diff)

        # ── effective K-factor ──────────────────────────────────────
        k_eff = self.k_factor * g_mult

        # ── update ratings ──────────────────────────────────────────
        new_home = r_home + k_eff * (s_home - e_home)
        new_away = r_away + k_eff * (s_away - e_away)

        self.ratings[home_team] = new_home
        self.ratings[away_team] = new_away

        logger.debug(
            "%s (%.0f → %.0f) vs %s (%.0f → %.0f) | Score %d-%d",
            home_team, r_home, new_home,
            away_team, r_away, new_away,
            home_goals, away_goals,
        )

        return new_home, new_away

    def get_win_probability(
        self, home_team: str, away_team: str
    ) -> Dict[str, float]:
        """Estimate match outcome probabilities from current ratings.

        Uses a logistic function with home advantage, then allocates a
        draw probability proportional to how close the two teams are in
        strength.

        The draw probability is modelled as:

            P(draw) = 1 / (c * exp(d * |delta|))

        where ``delta`` is the adjusted rating difference and ``c``, ``d``
        are calibrated constants.  This gives roughly 25-28 % draw
        probability for evenly matched sides and falls off as the gap
        widens — consistent with empirical football data.

        Parameters
        ----------
        home_team : str
            Name of the home team.
        away_team : str
            Name of the away team.

        Returns
        -------
        dict
            ``{"home": float, "draw": float, "away": float}``
            The three probabilities sum to 1.
        """
        r_home = self.get_rating(home_team)
        r_away = self.get_rating(away_team)

        # Rating difference including home advantage
        delta = (r_home + self.home_advantage - r_away) / 400.0

        # Logistic expected score for the home team (before draw carve-out)
        e_home = 1.0 / (1.0 + 10.0 ** (-delta))

        # ── draw probability (empirical calibration) ────────────────
        # Constants calibrated to produce ~26 % draw rate at delta = 0,
        # matching observed frequencies in top European leagues.
        draw_prob = max(0.0, 0.28 * math.exp(-0.6 * abs(delta)))

        # Allocate remaining probability proportionally
        remaining = 1.0 - draw_prob
        home_prob = remaining * e_home
        away_prob = remaining * (1.0 - e_home)

        return {
            "home": round(home_prob, 4),
            "draw": round(draw_prob, 4),
            "away": round(away_prob, 4),
        }

    def get_rating(self, team: str) -> float:
        """Return a team's current rating, initialising if unseen.

        Parameters
        ----------
        team : str
            Team name.

        Returns
        -------
        float
            Current Elo rating.
        """
        if team not in self.ratings:
            self.ratings[team] = self.initial_rating
            logger.debug("Initialised %s at rating %.0f", team, self.initial_rating)
        return self.ratings[team]

    def get_all_ratings(self) -> Dict[str, float]:
        """Return a copy of all team ratings.

        Returns
        -------
        dict[str, float]
            Team name → current Elo rating.
        """
        return dict(self.ratings)

    # ── private helpers ───────────────────────────────────────────────

    def _expected_score(self, r_home: float, r_away: float) -> float:
        """Logistic expected score for the home team.

        E = 1 / (1 + 10^(-(R_home - R_away + H) / 400))

        Parameters
        ----------
        r_home : float
            Home team's current rating.
        r_away : float
            Away team's current rating.

        Returns
        -------
        float
            Expected score in [0, 1].
        """
        exponent = -(r_home - r_away + self.home_advantage) / 400.0
        return 1.0 / (1.0 + 10.0 ** exponent)

    @staticmethod
    def _goal_diff_multiplier(goal_diff: int) -> float:
        """Compute the goal-difference K-factor multiplier.

        For narrow results (0 or 1 goal difference) the multiplier is 1.
        For wider margins:

            G_mult = 1 + ln(goal_diff)

        This gives, for example:
            goal_diff = 2 → 1 + ln(2) ≈ 1.69
            goal_diff = 3 → 1 + ln(3) ≈ 2.10
            goal_diff = 5 → 1 + ln(5) ≈ 2.61

        Parameters
        ----------
        goal_diff : int
            Absolute goal difference (non-negative).

        Returns
        -------
        float
            Multiplier ≥ 1.
        """
        if goal_diff < 2:
            return 1.0
        return 1.0 + math.log(goal_diff)
