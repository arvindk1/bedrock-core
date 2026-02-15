"""
Volatility Engine — Historical, GARCH, EWMA, Hybrid, Regime Detection, IV Rank
================================================================================
Synchronous implementation using yfinance for price data.
"""

import logging
import warnings
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, Optional

import numpy as np
import yfinance as yf
from scipy import optimize
from scipy.stats import norm

warnings.filterwarnings("ignore", category=RuntimeWarning)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class VolatilityModel(Enum):
    HISTORICAL = "historical"
    GARCH = "garch"
    EWMA = "ewma"
    IMPLIED_VOLATILITY = "implied_vol"
    HYBRID = "hybrid"


class VolRegime(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

@dataclass
class VolatilityResult:
    annual_volatility: float
    daily_volatility: float
    model_used: VolatilityModel
    confidence_score: float
    data_points: int
    calculation_date: datetime
    additional_metrics: Dict[str, float] = field(default_factory=dict)


@dataclass
class GARCHParameters:
    omega: float
    alpha: float
    beta: float
    likelihood: float
    aic: float
    convergence: bool


# ---------------------------------------------------------------------------
# VolEngine
# ---------------------------------------------------------------------------

class VolEngine:
    """Synchronous volatility engine supporting multiple models."""

    def __init__(
        self,
        default_history_days: int = 252,
        garch_max_iterations: int = 1000,
        ewma_lambda: float = 0.94,
        hybrid_weights: Optional[Dict[VolatilityModel, float]] = None,
    ):
        self.default_history_days = default_history_days
        self.garch_max_iterations = garch_max_iterations
        self.ewma_lambda = ewma_lambda
        self.hybrid_weights = hybrid_weights or {
            VolatilityModel.HISTORICAL: 0.3,
            VolatilityModel.GARCH: 0.4,
            VolatilityModel.EWMA: 0.2,
            VolatilityModel.IMPLIED_VOLATILITY: 0.1,
        }

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def calculate_volatility(
        self,
        symbol: str,
        model: VolatilityModel = VolatilityModel.HYBRID,
        history_days: Optional[int] = None,
    ) -> VolatilityResult:
        """Dispatch to model-specific volatility calculation."""
        history_days = history_days or self.default_history_days

        dispatch = {
            VolatilityModel.HISTORICAL: self._calc_historical,
            VolatilityModel.GARCH: self._calc_garch,
            VolatilityModel.EWMA: self._calc_ewma,
            VolatilityModel.HYBRID: self._calc_hybrid,
        }
        handler = dispatch.get(model)
        if handler is None:
            raise ValueError(f"Unsupported volatility model: {model}")
        return handler(symbol, history_days)

    def detect_regime(self, symbol: str, history_days: int = 252) -> VolRegime:
        """Compare short-term vs long-term vol + IV rank to classify regime."""
        short_result = self._calc_historical(symbol, 30)
        long_result = self._calc_historical(symbol, history_days)
        iv_rank = self.calculate_iv_rank(symbol, history_days)

        ratio = short_result.annual_volatility / max(long_result.annual_volatility, 1e-8)
        score = 0.5 * ratio + 0.5 * iv_rank

        if score < 0.8:
            return VolRegime.LOW
        elif score < 1.2:
            return VolRegime.MEDIUM
        else:
            return VolRegime.HIGH

    def calculate_iv_rank(self, symbol: str, lookback_days: int = 252) -> float:
        """Rolling 30-day vol, rank current value in historical range. Returns 0-1."""
        returns = self._fetch_returns(symbol, lookback_days, min_points=30)
        window = 30
        rolling_vols = []
        for i in range(window, len(returns) + 1):
            seg = returns[i - window : i]
            rolling_vols.append(np.std(seg, ddof=1) * np.sqrt(252))

        if len(rolling_vols) < 2:
            return 0.5

        current_vol = rolling_vols[-1]
        min_vol = min(rolling_vols)
        max_vol = max(rolling_vols)
        if max_vol == min_vol:
            return 0.5
        return (current_vol - min_vol) / (max_vol - min_vol)

    def calculate_expected_move(
        self,
        symbol: str,
        current_price: float,
        days: int,
        confidence: float = 0.68,
    ) -> Dict[str, float]:
        """Expected move using hybrid vol, sqrt(days/252), norm.ppf."""
        vol_result = self._calc_hybrid(symbol, self.default_history_days)
        annual_vol = vol_result.annual_volatility
        time_factor = np.sqrt(days / 252.0)
        z = norm.ppf((1 + confidence) / 2)
        move = current_price * annual_vol * time_factor * z
        return {
            "expected_move_dollars": move,
            "expected_move_percent": (move / current_price) * 100,
            "upper_target": current_price + move,
            "lower_target": current_price - move,
            "annual_volatility": annual_vol,
            "confidence": confidence,
            "days": days,
        }

    # ------------------------------------------------------------------
    # Data fetching
    # ------------------------------------------------------------------

    def _fetch_returns(
        self, symbol: str, history_days: int, min_points: int = 20
    ) -> np.ndarray:
        """Fetch prices from yfinance, compute log returns, validate."""
        end_date = datetime.now()
        start_date = end_date - timedelta(days=history_days + 30)

        ticker = yf.Ticker(symbol)
        hist = ticker.history(start=start_date, end=end_date)

        if len(hist) < min_points:
            raise ValueError(
                f"Insufficient data for {symbol}: got {len(hist)} rows, "
                f"need at least {min_points}"
            )

        prices = hist["Close"].values
        log_returns = np.log(prices[1:] / prices[:-1])
        log_returns = log_returns[np.isfinite(log_returns)]

        if len(log_returns) < min_points:
            raise ValueError(
                f"Insufficient valid returns for {symbol}: {len(log_returns)}"
            )
        return log_returns

    # ------------------------------------------------------------------
    # Model implementations
    # ------------------------------------------------------------------

    def _calc_historical(self, symbol: str, history_days: int) -> VolatilityResult:
        """Standard deviation of log returns * sqrt(252)."""
        returns = self._fetch_returns(symbol, history_days)
        daily_vol = np.std(returns, ddof=1)
        annual_vol = daily_vol * np.sqrt(252)
        confidence = min(1.0, len(returns) / 252)

        return VolatilityResult(
            annual_volatility=annual_vol,
            daily_volatility=daily_vol,
            model_used=VolatilityModel.HISTORICAL,
            confidence_score=confidence,
            data_points=len(returns),
            calculation_date=datetime.now(),
            additional_metrics={
                "mean_return": float(np.mean(returns)),
                "skewness": self._skewness(returns),
                "kurtosis": self._kurtosis(returns),
            },
        )

    def _calc_garch(self, symbol: str, history_days: int) -> VolatilityResult:
        """Fit GARCH(1,1) and produce one-step forecast. Falls back to historical."""
        try:
            returns = self._fetch_returns(symbol, max(history_days, 500), min_points=100)
        except ValueError:
            logger.warning("Insufficient data for GARCH, falling back to historical")
            return self._calc_historical(symbol, history_days)

        params = self._fit_garch(returns)
        if not params.convergence:
            logger.warning("GARCH did not converge, falling back to historical")
            return self._calc_historical(symbol, history_days)

        # One-step forecast
        last_var = np.var(returns[-10:])
        last_ret_sq = returns[-1] ** 2
        forecast_var = params.omega + params.alpha * last_ret_sq + params.beta * last_var
        forecast_var = max(forecast_var, 1e-8)

        daily_vol = np.sqrt(forecast_var)
        annual_vol = daily_vol * np.sqrt(252)

        return VolatilityResult(
            annual_volatility=annual_vol,
            daily_volatility=daily_vol,
            model_used=VolatilityModel.GARCH,
            confidence_score=0.8 if params.convergence else 0.4,
            data_points=len(returns),
            calculation_date=datetime.now(),
            additional_metrics={
                "garch_omega": params.omega,
                "garch_alpha": params.alpha,
                "garch_beta": params.beta,
                "garch_aic": params.aic,
                "persistence": params.alpha + params.beta,
            },
        )

    def _calc_ewma(self, symbol: str, history_days: int) -> VolatilityResult:
        """EWMA variance recursion."""
        returns = self._fetch_returns(symbol, history_days)
        lam = self.ewma_lambda
        var = returns[0] ** 2
        for r in returns[1:]:
            var = lam * var + (1 - lam) * r ** 2

        daily_vol = np.sqrt(var)
        annual_vol = daily_vol * np.sqrt(252)
        confidence = min(0.9, len(returns) / 100)

        return VolatilityResult(
            annual_volatility=annual_vol,
            daily_volatility=daily_vol,
            model_used=VolatilityModel.EWMA,
            confidence_score=confidence,
            data_points=len(returns),
            calculation_date=datetime.now(),
            additional_metrics={
                "ewma_lambda": lam,
                "current_variance": var,
            },
        )

    def _calc_hybrid(self, symbol: str, history_days: int) -> VolatilityResult:
        """Weighted ensemble of available models."""
        results: Dict[VolatilityModel, VolatilityResult] = {}

        for model, method in [
            (VolatilityModel.HISTORICAL, self._calc_historical),
            (VolatilityModel.GARCH, self._calc_garch),
            (VolatilityModel.EWMA, self._calc_ewma),
        ]:
            try:
                results[model] = method(symbol, history_days)
            except Exception as exc:
                logger.debug("Model %s failed: %s", model.value, exc)

        if not results:
            raise ValueError(f"All volatility models failed for {symbol}")

        total_weight = 0.0
        weighted_annual = 0.0
        weighted_daily = 0.0
        for model, res in results.items():
            w = self.hybrid_weights.get(model, 0) * res.confidence_score
            total_weight += w
            weighted_annual += res.annual_volatility * w
            weighted_daily += res.daily_volatility * w

        if total_weight == 0:
            weighted_annual = float(np.mean([r.annual_volatility for r in results.values()]))
            weighted_daily = float(np.mean([r.daily_volatility for r in results.values()]))
        else:
            weighted_annual /= total_weight
            weighted_daily /= total_weight

        return VolatilityResult(
            annual_volatility=weighted_annual,
            daily_volatility=weighted_daily,
            model_used=VolatilityModel.HYBRID,
            confidence_score=min(0.95, float(np.mean([r.confidence_score for r in results.values()]))),
            data_points=sum(r.data_points for r in results.values()),
            calculation_date=datetime.now(),
            additional_metrics={
                "model_count": len(results),
            },
        )

    # ------------------------------------------------------------------
    # GARCH fitting
    # ------------------------------------------------------------------

    def _fit_garch(self, returns: np.ndarray) -> GARCHParameters:
        """Fit GARCH(1,1) via scipy L-BFGS-B."""
        initial = [0.01, 0.05, 0.9]
        bounds = [(1e-6, 1.0), (1e-6, 1.0), (1e-6, 1.0)]
        try:
            result = optimize.minimize(
                self._garch_neg_loglik,
                initial,
                args=(returns,),
                method="L-BFGS-B",
                bounds=bounds,
                options={"maxiter": self.garch_max_iterations},
            )
            if result.success:
                omega, alpha, beta = result.x
                if alpha + beta >= 1.0:
                    return GARCHParameters(omega, alpha, beta, 0, float("inf"), False)
                likelihood = -result.fun
                aic = 2 * len(initial) - 2 * likelihood
                return GARCHParameters(omega, alpha, beta, likelihood, aic, True)
        except Exception as exc:
            logger.error("GARCH fitting failed: %s", exc)

        return GARCHParameters(0.01, 0.05, 0.9, 0, float("inf"), False)

    @staticmethod
    def _garch_neg_loglik(params, returns: np.ndarray) -> float:
        """Negative log-likelihood for GARCH(1,1)."""
        omega, alpha, beta = params
        if omega <= 0 or alpha <= 0 or beta <= 0 or (alpha + beta) >= 1.0:
            return 1e8

        n = len(returns)
        sigma2 = np.zeros(n)
        sigma2[0] = np.var(returns)

        for t in range(1, n):
            sigma2[t] = omega + alpha * returns[t - 1] ** 2 + beta * sigma2[t - 1]

        nll = 0.5 * np.sum(np.log(2 * np.pi * sigma2) + returns ** 2 / sigma2)
        return nll

    # ------------------------------------------------------------------
    # Statistics helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _skewness(returns: np.ndarray) -> float:
        n = len(returns)
        if n < 3:
            return 0.0
        m = np.mean(returns)
        s = np.std(returns, ddof=1)
        if s == 0:
            return 0.0
        return float((n / ((n - 1) * (n - 2))) * np.sum(((returns - m) / s) ** 3))

    @staticmethod
    def _kurtosis(returns: np.ndarray) -> float:
        n = len(returns)
        if n < 4:
            return 0.0
        m = np.mean(returns)
        s = np.std(returns, ddof=1)
        if s == 0:
            return 0.0
        k = (n * (n + 1) / ((n - 1) * (n - 2) * (n - 3))) * np.sum(
            ((returns - m) / s) ** 4
        ) - 3 * (n - 1) ** 2 / ((n - 2) * (n - 3))
        return float(k)
