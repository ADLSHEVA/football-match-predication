"""
EuroGoal Predictor - Dixon-Coles Bivariate Poisson Model
=========================================================

Implements the Dixon & Coles (1997) extension of the independent Poisson model
for predicting football match outcomes.  The key insight is that the basic
independent-Poisson model *under*-predicts low-scoring draws (0-0, 1-0, 0-1,
1-1).  Dixon-Coles adds a dependence parameter ``rho`` and a correction factor
``tau`` that concentrates or disperses probability mass on those specific
score-lines.

Mathematical formulation
------------------------
For a match between home team *i* and away team *j*:

    lambda_ij = alpha_i * beta_j * gamma          (expected home goals)
    mu_ij     = alpha_j * beta_i                   (expected away goals)

where
    alpha_i  = attack strength of team i,
    beta_i   = defense weakness of team i (higher ⇒ worse defense),
    gamma    = home-advantage parameter (> 1 means home advantage).

The probability of the exact score (x, y) is:

    P(x, y) = tau(x, y, lambda, mu, rho)
              * (lambda^x * exp(-lambda) / x!)
              * (mu^y   * exp(-mu)   / y!)

The tau function only modifies the four lowest-scoring outcomes:
    (0,0) → 1 - lambda*mu*rho
    (1,0) → 1 + mu*rho
    (0,1) → 1 + lambda*rho
    (1,1) → 1 - rho
    else  → 1

Parameters are estimated by *maximum-likelihood* on historical match data,
weighted by an exponential time-decay factor:

    w_t = exp(-phi * days_since_match)

An identifiability constraint (sum-to-zero on log-attack parameters) is
applied so that the system is not degenerate.

References
----------
Dixon, M. J. & Coles, S. G. (1997).  "Modelling Association Football Scores
and Inefficiencies in the Football Betting Market".  *Journal of the Royal
Statistical Society: Series C*, 46(2), 265-280.
"""

from __future__ import annotations

import logging
import warnings
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from scipy.optimize import minimize
from scipy.stats import poisson

from app.config import DC_TIME_DECAY_PHI

logger = logging.getLogger(__name__)

# Maximum number of goals per team in the score probability matrix.
# We use 0..MAX_GOALS (inclusive), so the matrix is (MAX_GOALS+1)².
MAX_GOALS: int = 7


class DixonColesModel:
    """xG-Dixon-Coles bivariate Poisson model with MLE fitting.

    Parameters
    ----------
    phi : float, optional
        Exponential time-decay rate.  Larger values discount older matches
        more aggressively.  Defaults to ``DC_TIME_DECAY_PHI`` from config.
    max_goals : int, optional
        Upper bound for goals per team in the probability matrix.  The
        resulting matrix is ``(max_goals + 1) × (max_goals + 1)``.

    Attributes
    ----------
    teams_ : list[str]
        Sorted list of team names observed during fitting.
    attack_ : dict[str, float]
        Fitted attack (alpha) parameters per team.
    defense_ : dict[str, float]
        Fitted defense (beta) parameters per team.
    home_adv_ : float
        Fitted home-advantage parameter (gamma).
    rho_ : float
        Fitted Dixon-Coles dependence parameter.
    is_fitted_ : bool
        Whether the model has been fitted to data.
    """

    def __init__(
        self,
        phi: float = DC_TIME_DECAY_PHI,
        max_goals: int = MAX_GOALS,
    ) -> None:
        self.phi: float = phi
        self.max_goals: int = max_goals

        # Fitted parameters — populated by ``fit()``.
        self.teams_: List[str] = []
        self.attack_: Dict[str, float] = {}
        self.defense_: Dict[str, float] = {}
        self.home_adv_: float = 1.0
        self.rho_: float = 0.0
        self.is_fitted_: bool = False

    # ── public API ────────────────────────────────────────────────────

    def fit(self, match_data: pd.DataFrame) -> None:
        """Fit the model to historical match data via MLE.

        Parameters
        ----------
        match_data : pd.DataFrame
            Must contain columns:
            ``home_team``, ``away_team``, ``home_xg``, ``away_xg``, ``date``.
            ``home_xg`` / ``away_xg`` are the expected-goals totals produced
            by the underlying xG model (or actual goals if xG is unavailable).
            ``date`` should be parseable by ``pd.to_datetime``.

        Raises
        ------
        ValueError
            If required columns are missing or the DataFrame is empty.
        RuntimeError
            If the optimiser fails to converge.
        """
        self._validate_input(match_data)

        df = match_data.copy()
        df["date"] = pd.to_datetime(df["date"])

        # ── time-decay weights ──────────────────────────────────────
        most_recent: datetime = df["date"].max()
        df["days_ago"] = (most_recent - df["date"]).dt.days.astype(float)
        # w_t = exp(-phi * t)  where t = days since match
        df["weight"] = np.exp(-self.phi * df["days_ago"])

        # ── team indexing ───────────────────────────────────────────
        self.teams_ = sorted(
            set(df["home_team"].unique()) | set(df["away_team"].unique())
        )
        n_teams: int = len(self.teams_)
        team_to_idx: Dict[str, int] = {t: i for i, t in enumerate(self.teams_)}

        home_idx = df["home_team"].map(team_to_idx).values
        away_idx = df["away_team"].map(team_to_idx).values
        home_xg = df["home_xg"].values.astype(float)
        away_xg = df["away_xg"].values.astype(float)
        weights = df["weight"].values.astype(float)

        # ── initial parameter vector ────────────────────────────────
        # Layout: [attack_0 .. attack_{n-1},
        #          defense_0 .. defense_{n-1},
        #          home_adv,  rho]
        # We initialise attack/defense on the log scale for positivity
        # and apply exp() inside the objective.  Home advantage starts
        # at log(1.25) ≈ 0.22 and rho at 0.
        x0 = np.zeros(2 * n_teams + 2)
        x0[2 * n_teams] = np.log(1.25)  # log(home_adv)
        x0[2 * n_teams + 1] = -0.05      # rho (small negative)

        # ── optimise ────────────────────────────────────────────────
        logger.info(
            "Fitting Dixon-Coles model on %d matches, %d teams …",
            len(df), n_teams,
        )

        result = minimize(
            fun=self._neg_log_likelihood,
            x0=x0,
            args=(home_idx, away_idx, home_xg, away_xg, weights, n_teams),
            method="L-BFGS-B",
            options={"maxiter": 5000, "ftol": 1e-12},
        )

        if not result.success:
            warnings.warn(
                f"Dixon-Coles optimiser did not fully converge: {result.message}",
                RuntimeWarning,
                stacklevel=2,
            )

        # ── unpack & store fitted parameters ────────────────────────
        params = result.x
        raw_attack = params[:n_teams]
        raw_defense = params[n_teams : 2 * n_teams]

        # Sum-to-zero constraint on attack params for identifiability:
        #   We centre so that  sum(log_attack) = 0
        raw_attack -= raw_attack.mean()

        attack_vals = np.exp(raw_attack)
        defense_vals = np.exp(raw_defense)
        home_adv = np.exp(params[2 * n_teams])
        rho = params[2 * n_teams + 1]

        self.attack_ = {t: float(attack_vals[i]) for i, t in enumerate(self.teams_)}
        self.defense_ = {t: float(defense_vals[i]) for i, t in enumerate(self.teams_)}
        self.home_adv_ = float(home_adv)
        self.rho_ = float(np.clip(rho, -1.0, 1.0))
        self.is_fitted_ = True

        logger.info(
            "Dixon-Coles fit complete.  Home advantage = %.3f, rho = %.4f",
            self.home_adv_, self.rho_,
        )

    def predict(
        self,
        home_team: str,
        away_team: str,
        adjustments: Optional[Dict[str, float]] = None,
    ) -> Dict[str, Any]:
        """Predict the outcome of a match between two teams.

        Parameters
        ----------
        home_team : str
            Name of the home team.
        away_team : str
            Name of the away team.
        adjustments : dict, optional
            Multipliers to tweak strength parameters on the fly.
            Supported keys:
                ``home_attack_adj``  – multiplier for home team's attack.
                ``home_defense_adj`` – multiplier for home team's defense.
                ``away_attack_adj``  – multiplier for away team's attack.
                ``away_defense_adj`` – multiplier for away team's defense.
            Values > 1 increase the parameter; < 1 decrease it.

        Returns
        -------
        dict
            ``score_matrix`` : np.ndarray of shape (max_goals+1, max_goals+1)
                Probability of each exact score.
            ``home_win_prob`` : float
            ``draw_prob``     : float
            ``away_win_prob`` : float
            ``expected_home_goals`` : float
            ``expected_away_goals`` : float
            ``most_likely_scores``  : list of (home_goals, away_goals, prob)

        Raises
        ------
        RuntimeError
            If the model has not been fitted yet.
        KeyError
            If either team was not seen during fitting.
        """
        self._check_fitted()

        if home_team not in self.attack_:
            raise KeyError(f"Unknown home team: '{home_team}'")
        if away_team not in self.attack_:
            raise KeyError(f"Unknown away team: '{away_team}'")

        # ── base expected-goals rates ───────────────────────────────
        # lambda = alpha_home * beta_away * gamma
        # mu     = alpha_away * beta_home
        alpha_home = self.attack_[home_team]
        beta_home = self.defense_[home_team]
        alpha_away = self.attack_[away_team]
        beta_away = self.defense_[away_team]

        # ── apply optional adjustments ──────────────────────────────
        adj = adjustments or {}
        alpha_home *= adj.get("home_attack_adj", 1.0)
        beta_home *= adj.get("home_defense_adj", 1.0)
        alpha_away *= adj.get("away_attack_adj", 1.0)
        beta_away *= adj.get("away_defense_adj", 1.0)

        lam: float = alpha_home * beta_away * self.home_adv_   # expected home goals
        mu: float = alpha_away * beta_home                      # expected away goals

        # ── build score probability matrix (vectorised) ─────────────
        n = self.max_goals + 1
        score_matrix = self._score_matrix(lam, mu, self.rho_, n)

        # ── aggregate probabilities ─────────────────────────────────
        # Home win: sum of P(x, y) where x > y
        home_win_prob = float(np.tril(score_matrix, k=-1).sum())
        # Away win: sum of P(x, y) where x < y
        away_win_prob = float(np.triu(score_matrix, k=1).sum())
        # Draw: sum of diagonal
        draw_prob = float(np.trace(score_matrix))

        # ── expected goals (from the Poisson parameters) ────────────
        expected_home = float(lam)
        expected_away = float(mu)

        # ── most likely scores ──────────────────────────────────────
        flat = score_matrix.ravel()
        top_indices = np.argsort(flat)[::-1][:5]
        most_likely = [
            (int(idx // n), int(idx % n), float(flat[idx]))
            for idx in top_indices
        ]

        return {
            "score_matrix": score_matrix,
            "home_win_prob": home_win_prob,
            "draw_prob": draw_prob,
            "away_win_prob": away_win_prob,
            "expected_home_goals": expected_home,
            "expected_away_goals": expected_away,
            "most_likely_scores": most_likely,
        }

    def get_team_params(self) -> Dict[str, Dict[str, float]]:
        """Return all fitted team-level parameters.

        Returns
        -------
        dict
            Keyed by team name.  Each value is a dict with keys
            ``attack``, ``defense``.  Also includes ``home_advantage``
            and ``rho`` at the top level.
        """
        self._check_fitted()
        team_params = {
            team: {"attack": self.attack_[team], "defense": self.defense_[team]}
            for team in self.teams_
        }
        return {
            "teams": team_params,
            "home_advantage": self.home_adv_,
            "rho": self.rho_,
        }

    # ── private helpers ───────────────────────────────────────────────

    @staticmethod
    def _tau(
        x: np.ndarray,
        y: np.ndarray,
        lam: np.ndarray,
        mu: np.ndarray,
        rho: float,
    ) -> np.ndarray:
        """Dixon-Coles tau correction factor for low-scoring outcomes.

        The independent Poisson assumption systematically mis-prices the
        four lowest score-lines.  Tau adjusts the probability mass:

            tau(0, 0) = 1 - lam * mu * rho
            tau(1, 0) = 1 + mu * rho
            tau(0, 1) = 1 + lam * rho
            tau(1, 1) = 1 - rho
            tau(x, y) = 1   otherwise

        Parameters
        ----------
        x, y : np.ndarray
            Home and away goals (integer arrays).
        lam, mu : np.ndarray
            Expected home and away goals.
        rho : float
            Dependence parameter.

        Returns
        -------
        np.ndarray
            Multiplicative correction factors (same shape as x).
        """
        tau = np.ones_like(x, dtype=float)
        mask_00 = (x == 0) & (y == 0)
        mask_10 = (x == 1) & (y == 0)
        mask_01 = (x == 0) & (y == 1)
        mask_11 = (x == 1) & (y == 1)

        tau[mask_00] = 1.0 - lam[mask_00] * mu[mask_00] * rho
        tau[mask_10] = 1.0 + mu[mask_10] * rho
        tau[mask_01] = 1.0 + lam[mask_01] * rho
        tau[mask_11] = 1.0 - rho
        return tau

    @staticmethod
    def _tau_scalar(x: int, y: int, lam: float, mu: float, rho: float) -> float:
        """Scalar version of the tau correction (for matrix construction)."""
        if x == 0 and y == 0:
            return 1.0 - lam * mu * rho
        if x == 1 and y == 0:
            return 1.0 + mu * rho
        if x == 0 and y == 1:
            return 1.0 + lam * rho
        if x == 1 and y == 1:
            return 1.0 - rho
        return 1.0

    def _score_matrix(
        self, lam: float, mu: float, rho: float, n: int
    ) -> np.ndarray:
        """Build an n×n score probability matrix (fully vectorised).

        P(x, y) = tau(x,y) * Poisson(x | lam) * Poisson(y | mu)

        Parameters
        ----------
        lam : float
            Expected home goals.
        mu : float
            Expected away goals.
        rho : float
            Dependence parameter.
        n : int
            Matrix dimension (0 .. n-1 goals each side).

        Returns
        -------
        np.ndarray of shape (n, n)
            Probability of each exact score (home_goals, away_goals).
        """
        # Poisson PMFs as 1-D vectors
        goals = np.arange(n)
        pmf_home = poisson.pmf(goals, lam)  # shape (n,)
        pmf_away = poisson.pmf(goals, mu)   # shape (n,)

        # Outer product → independent-Poisson matrix
        matrix = np.outer(pmf_home, pmf_away)  # shape (n, n)

        # Apply tau correction to the four relevant cells
        matrix[0, 0] *= self._tau_scalar(0, 0, lam, mu, rho)
        matrix[1, 0] *= self._tau_scalar(1, 0, lam, mu, rho)
        matrix[0, 1] *= self._tau_scalar(0, 1, lam, mu, rho)
        matrix[1, 1] *= self._tau_scalar(1, 1, lam, mu, rho)

        # Renormalise so the matrix sums to 1 (tau can shift total slightly)
        matrix /= matrix.sum()

        return matrix

    def _neg_log_likelihood(
        self,
        params: np.ndarray,
        home_idx: np.ndarray,
        away_idx: np.ndarray,
        home_xg: np.ndarray,
        away_xg: np.ndarray,
        weights: np.ndarray,
        n_teams: int,
    ) -> float:
        """Negative (weighted) log-likelihood of the Dixon-Coles model.

        This is the objective that the optimiser minimises.

        The log-likelihood for a single match with observed score (x, y)
        and weights w is:

            ℓ = w * [ log(tau(x,y,λ,μ,ρ))
                     + x*log(λ) - λ - log(x!)
                     + y*log(μ) - μ - log(y!) ]

        We sum over all matches and negate for minimisation.

        We parameterise attack / defense on the log scale so that the
        actual strength = exp(raw_param), ensuring positivity without
        explicit bound constraints.

        Parameters
        ----------
        params : np.ndarray
            Flat parameter vector: [log_attack * n_teams,
                                     log_defense * n_teams,
                                     log_home_adv,
                                     rho].
        home_idx, away_idx : np.ndarray of int
            Team indices for each match.
        home_xg, away_xg : np.ndarray of float
            Observed home/away xG (or actual goals).
        weights : np.ndarray of float
            Time-decay weights for each match.
        n_teams : int
            Number of distinct teams.

        Returns
        -------
        float
            Negative weighted log-likelihood (scalar).
        """
        # ── unpack parameters ───────────────────────────────────────
        raw_attack = params[:n_teams]
        raw_defense = params[n_teams : 2 * n_teams]
        log_home_adv = params[2 * n_teams]
        rho = params[2 * n_teams + 1]

        # Apply sum-to-zero constraint on attacks during optimisation
        raw_attack_centred = raw_attack - raw_attack.mean()

        attack = np.exp(raw_attack_centred)
        defense = np.exp(raw_defense)
        home_adv = np.exp(log_home_adv)

        # ── expected goals per match ────────────────────────────────
        # lambda_i = attack_home * defense_away * home_adv
        # mu_i     = attack_away * defense_home
        lam = attack[home_idx] * defense[away_idx] * home_adv
        mu = attack[away_idx] * defense[home_idx]

        # Clamp to avoid log(0) or numerical issues
        lam = np.clip(lam, 1e-6, 15.0)
        mu = np.clip(mu, 1e-6, 15.0)

        # ── round xG to nearest integer for Poisson PMF ────────────
        # The model treats the observed xG as the "score" for likelihood
        # purposes.  We floor to integers because the Poisson PMF is
        # defined on non-negative integers.
        x = np.round(home_xg).astype(int)
        y = np.round(away_xg).astype(int)

        # ── tau correction ──────────────────────────────────────────
        tau_vals = self._tau(x, y, lam, mu, rho)
        # Safety: tau must be > 0 for log
        tau_vals = np.clip(tau_vals, 1e-10, None)

        # ── Poisson log-likelihood components ───────────────────────
        # log P(x | λ) = x*log(λ) - λ - log(x!)
        from scipy.special import gammaln  # log(n!) = gammaln(n+1)

        log_lik = (
            np.log(tau_vals)
            + x * np.log(lam) - lam - gammaln(x + 1)
            + y * np.log(mu) - mu - gammaln(y + 1)
        )

        # Weighted sum
        total = np.sum(weights * log_lik)

        # Return negative for minimisation
        return -total

    def _check_fitted(self) -> None:
        """Raise if the model has not been fitted."""
        if not self.is_fitted_:
            raise RuntimeError(
                "Model has not been fitted yet.  Call .fit() first."
            )

    @staticmethod
    def _validate_input(df: pd.DataFrame) -> None:
        """Validate that the input DataFrame has the required columns."""
        required = {"home_team", "away_team", "home_xg", "away_xg", "date"}
        missing = required - set(df.columns)
        if missing:
            raise ValueError(
                f"Input DataFrame is missing required columns: {missing}"
            )
        if df.empty:
            raise ValueError("Input DataFrame is empty.")
