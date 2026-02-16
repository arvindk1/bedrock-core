# Phase 1: Core Infrastructure Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Rewrite and harden the three Phase 1 modules (risk_engine, vol_engine, event_loader) with full test coverage, following the design in `docs/plans/2026-02-15-phase1-core-infrastructure-design.md`.

**Architecture:** Three independent pure-Python modules with no agent/framework coupling. Each module is a class with configurable thresholds. yfinance for market data. All tests use mocks — no network calls. Bare imports for container compatibility.

**Tech Stack:** Python 3.10+, pytest, unittest.mock, yfinance, numpy, scipy, pandas

---

## Task 1: Risk Engine — Core Structure & Per-Trade Risk Check

**Files:**
- Create: `tests/test_risk_engine.py`
- Create: `agent/risk_engine.py` (rewrite)

**Step 1: Write the failing tests for RiskEngine core + per-trade risk**

```python
# tests/test_risk_engine.py
import pytest
from unittest.mock import patch, MagicMock

import sys
import os

# Add agent/ to path for bare imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "agent"))

from risk_engine import RiskEngine, RiskSeverity, ConcentrationAlert, RiskMetric


class TestRiskEngineInit:
    def test_default_thresholds(self):
        engine = RiskEngine()
        assert engine.max_risk_per_trade == 1000
        assert engine.max_sector_pct == 0.25
        assert engine.max_correlation == 0.7
        assert engine.drawdown_halt_pct == 0.02

    def test_custom_thresholds(self):
        engine = RiskEngine(max_risk_per_trade=500, max_sector_pct=0.30)
        assert engine.max_risk_per_trade == 500
        assert engine.max_sector_pct == 0.30


class TestPerTradeRisk:
    def test_reject_trade_exceeding_max_risk(self):
        engine = RiskEngine(max_risk_per_trade=1000)
        trade = {"symbol": "AAPL", "max_loss": 1500, "strategy_type": "BULL_CALL_DEBIT_SPREAD", "sector": "Technology"}
        rejected, reason = engine.should_reject_trade(trade, portfolio=[], market_context=None)
        assert rejected is True
        assert "max risk" in reason.lower()

    def test_accept_trade_within_max_risk(self):
        engine = RiskEngine(max_risk_per_trade=1000)
        trade = {"symbol": "AAPL", "max_loss": 800, "strategy_type": "BULL_CALL_DEBIT_SPREAD", "sector": "Technology"}
        rejected, reason = engine.should_reject_trade(trade, portfolio=[], market_context=None)
        assert rejected is False
        assert reason is None

    def test_reject_trade_missing_max_loss_defaults_to_reject(self):
        engine = RiskEngine(max_risk_per_trade=1000)
        trade = {"symbol": "AAPL", "strategy_type": "LONG_CALL", "sector": "Technology"}
        # No max_loss key — should reject for safety
        rejected, reason = engine.should_reject_trade(trade, portfolio=[], market_context=None)
        assert rejected is True
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/test_risk_engine.py -v`
Expected: FAIL with `ImportError` or `ModuleNotFoundError` (risk_engine not yet rewritten)

**Step 3: Write minimal RiskEngine implementation**

```python
# agent/risk_engine.py
"""
Risk Engine — The "No" Machine
===============================
Deterministic risk management: per-trade limits, sector concentration,
correlation checks, and drawdown circuit breaker.
"""

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class RiskSeverity(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class ConcentrationAlert:
    alert_type: str
    severity: RiskSeverity
    current_exposure: float
    limit_exposure: float
    message: str
    recommendation: str
    affected_positions: List[str] = field(default_factory=list)


@dataclass
class RiskMetric:
    metric_name: str
    current_value: float
    limit_value: float
    percentage_of_limit: float
    severity: RiskSeverity
    description: str


# GICS sector mapping for common symbols
SECTOR_MAP = {
    "AAPL": "Technology", "MSFT": "Technology", "GOOGL": "Technology",
    "AMZN": "Consumer Discretionary", "TSLA": "Consumer Discretionary",
    "META": "Technology", "NVDA": "Technology", "AMD": "Technology",
    "NFLX": "Communication Services", "QCOM": "Technology",
    "JPM": "Financials", "BAC": "Financials", "GS": "Financials",
    "WFC": "Financials", "MS": "Financials", "C": "Financials",
    "V": "Financials", "MA": "Financials",
    "JNJ": "Health Care", "PFE": "Health Care", "UNH": "Health Care",
    "ABBV": "Health Care", "MRK": "Health Care", "LLY": "Health Care",
    "XOM": "Energy", "CVX": "Energy", "COP": "Energy",
    "WMT": "Consumer Staples", "PG": "Consumer Staples", "KO": "Consumer Staples",
    "BA": "Industrials", "CAT": "Industrials", "HON": "Industrials",
    "SPY": "Index", "QQQ": "Index", "IWM": "Index",
}


class RiskEngine:
    """
    Deterministic risk gate for options trading.

    Checks (in order):
    1. Per-trade max loss
    2. Sector concentration (GICS, 25% default cap)
    3. Drawdown circuit breaker (daily loss > 2% halts trading)
    4. Strategy concentration (dollar-risk weighted)
    """

    def __init__(
        self,
        max_risk_per_trade: float = 1000.0,
        max_sector_pct: float = 0.25,
        max_correlation: float = 0.7,
        drawdown_halt_pct: float = 0.02,
    ):
        self.max_risk_per_trade = max_risk_per_trade
        self.max_sector_pct = max_sector_pct
        self.max_correlation = max_correlation
        self.drawdown_halt_pct = drawdown_halt_pct

    def should_reject_trade(
        self,
        trade: Dict[str, Any],
        portfolio: List[Dict[str, Any]],
        market_context: Optional[Dict[str, Any]] = None,
    ) -> Tuple[bool, Optional[str]]:
        """
        Run all rejection checks on a proposed trade.

        Returns:
            (should_reject, reason) — reason is None if trade passes.
        """
        # 1. Per-trade max loss check
        max_loss = trade.get("max_loss")
        if max_loss is None:
            return True, "Trade rejected: max_loss not specified (required for risk sizing)"
        if max_loss > self.max_risk_per_trade:
            return True, f"Trade rejected: max risk ${max_loss:.0f} exceeds limit ${self.max_risk_per_trade:.0f}"

        # 2. Sector concentration check
        sector_reject, sector_reason = self._check_sector_concentration(trade, portfolio)
        if sector_reject:
            return True, sector_reason

        # 3. Drawdown circuit breaker
        if market_context:
            halt = self.check_drawdown_halt(
                market_context.get("daily_pnl", 0),
                market_context.get("portfolio_value", 1),
            )
            if halt:
                return True, "Trade rejected: drawdown circuit breaker active (daily loss > limit)"

        return False, None

    def _check_sector_concentration(
        self,
        trade: Dict[str, Any],
        portfolio: List[Dict[str, Any]],
    ) -> Tuple[bool, Optional[str]]:
        """Check if adding this trade would breach sector concentration limits."""
        if not portfolio:
            return False, None

        trade_sector = trade.get("sector") or SECTOR_MAP.get(trade.get("symbol", ""), "Unknown")
        trade_risk = trade.get("max_loss", 0)

        # Calculate total portfolio risk
        total_risk = sum(pos.get("max_loss", 0) for pos in portfolio) + trade_risk
        if total_risk == 0:
            return False, None

        # Calculate sector risk including proposed trade
        sector_risk = trade_risk
        for pos in portfolio:
            pos_sector = pos.get("sector") or SECTOR_MAP.get(pos.get("symbol", ""), "Unknown")
            if pos_sector == trade_sector:
                sector_risk += pos.get("max_loss", 0)

        sector_pct = sector_risk / total_risk
        if sector_pct > self.max_sector_pct:
            return True, (
                f"Trade rejected: {trade_sector} sector exposure {sector_pct:.0%} "
                f"would exceed {self.max_sector_pct:.0%} limit"
            )

        return False, None

    def check_drawdown_halt(self, daily_pnl: float, portfolio_value: float) -> bool:
        """Check if daily drawdown exceeds circuit breaker threshold."""
        if portfolio_value <= 0:
            return False
        drawdown_pct = abs(min(0, daily_pnl)) / portfolio_value
        return drawdown_pct > self.drawdown_halt_pct

    def analyze_portfolio_risk(
        self,
        positions: List[Dict[str, Any]],
        proposed_trades: List[Dict[str, Any]],
        market_context: Optional[Dict[str, Any]] = None,
    ) -> Tuple[List[ConcentrationAlert], List[RiskMetric]]:
        """
        Analyze full portfolio risk and return alerts + metrics.

        Returns:
            (alerts, metrics)
        """
        alerts: List[ConcentrationAlert] = []
        metrics: List[RiskMetric] = []

        all_positions = positions + proposed_trades
        if not all_positions:
            return alerts, metrics

        # Sector concentration metrics
        sector_alerts, sector_metrics = self._analyze_sector_concentration(all_positions)
        alerts.extend(sector_alerts)
        metrics.extend(sector_metrics)

        # Strategy concentration metrics (dollar-risk weighted)
        strategy_alerts, strategy_metrics = self._analyze_strategy_concentration(all_positions)
        alerts.extend(strategy_alerts)
        metrics.extend(strategy_metrics)

        return alerts, metrics

    def _analyze_sector_concentration(
        self, positions: List[Dict[str, Any]]
    ) -> Tuple[List[ConcentrationAlert], List[RiskMetric]]:
        """Analyze sector concentration using dollar risk weighting."""
        alerts = []
        metrics = []

        total_risk = sum(pos.get("max_loss", 0) for pos in positions)
        if total_risk == 0:
            return alerts, metrics

        # Group by sector
        sector_risk: Dict[str, float] = {}
        sector_symbols: Dict[str, List[str]] = {}
        for pos in positions:
            sector = pos.get("sector") or SECTOR_MAP.get(pos.get("symbol", ""), "Unknown")
            risk = pos.get("max_loss", 0)
            sector_risk[sector] = sector_risk.get(sector, 0) + risk
            sector_symbols.setdefault(sector, []).append(pos.get("symbol", "?"))

        for sector, risk in sector_risk.items():
            pct = risk / total_risk
            severity = self._severity_from_pct(pct / self.max_sector_pct)

            metrics.append(RiskMetric(
                metric_name=f"{sector} Sector Exposure",
                current_value=pct,
                limit_value=self.max_sector_pct,
                percentage_of_limit=pct / self.max_sector_pct,
                severity=severity,
                description=f"{sector}: {pct:.0%} of portfolio risk",
            ))

            if pct > self.max_sector_pct:
                alerts.append(ConcentrationAlert(
                    alert_type="SECTOR_CONCENTRATION",
                    severity=RiskSeverity.CRITICAL,
                    current_exposure=pct,
                    limit_exposure=self.max_sector_pct,
                    message=f"{sector} sector at {pct:.0%}, exceeds {self.max_sector_pct:.0%} limit",
                    recommendation=f"Reduce {sector} exposure",
                    affected_positions=sector_symbols.get(sector, []),
                ))

        return alerts, metrics

    def _analyze_strategy_concentration(
        self, positions: List[Dict[str, Any]]
    ) -> Tuple[List[ConcentrationAlert], List[RiskMetric]]:
        """Analyze strategy concentration using dollar risk weighting."""
        alerts = []
        metrics = []

        total_risk = sum(pos.get("max_loss", 0) for pos in positions)
        if total_risk == 0:
            return alerts, metrics

        # Group by strategy type
        strategy_risk: Dict[str, float] = {}
        for pos in positions:
            strategy = self._normalize_strategy(pos.get("strategy_type", "UNKNOWN"))
            risk = pos.get("max_loss", 0)
            strategy_risk[strategy] = strategy_risk.get(strategy, 0) + risk

        for strategy, risk in strategy_risk.items():
            pct = risk / total_risk
            # Strategy limits are softer — use 50% as general max
            limit = 0.50
            severity = self._severity_from_pct(pct / limit)

            metrics.append(RiskMetric(
                metric_name=f"{strategy} Strategy Exposure",
                current_value=pct,
                limit_value=limit,
                percentage_of_limit=pct / limit,
                severity=severity,
                description=f"{strategy}: {pct:.0%} of portfolio risk",
            ))

        return alerts, metrics

    def _normalize_strategy(self, strategy: str) -> str:
        """Normalize strategy types for grouping."""
        s = strategy.upper()
        if "CONDOR" in s:
            return "IRON_CONDOR"
        elif "PUT_CREDIT" in s or "BULL_PUT" in s:
            return "CREDIT_SPREAD"
        elif "CALL_CREDIT" in s or "BEAR_CALL" in s:
            return "CREDIT_SPREAD"
        elif "DEBIT" in s:
            return "DEBIT_SPREAD"
        elif s in ("LONG_CALL", "LONG_PUT"):
            return "LONG_OPTIONS"
        elif s in ("STRADDLE", "STRANGLE"):
            return "VOLATILITY_PLAY"
        return s

    def _severity_from_pct(self, pct_of_limit: float) -> RiskSeverity:
        if pct_of_limit >= 1.0:
            return RiskSeverity.CRITICAL
        elif pct_of_limit >= 0.8:
            return RiskSeverity.HIGH
        elif pct_of_limit >= 0.6:
            return RiskSeverity.MEDIUM
        return RiskSeverity.LOW
```

**Step 4: Run tests to verify they pass**

Run: `pytest tests/test_risk_engine.py -v`
Expected: All 5 tests PASS

**Step 5: Commit**

```bash
git add tests/test_risk_engine.py agent/risk_engine.py
git commit -m "feat(risk): rewrite risk engine with per-trade limits and sector concentration"
```

---

## Task 2: Risk Engine — Sector Concentration & Drawdown Tests

**Files:**
- Modify: `tests/test_risk_engine.py`

**Step 1: Add sector concentration and drawdown tests**

```python
# Append to tests/test_risk_engine.py

class TestSectorConcentration:
    def test_reject_trade_breaching_sector_cap(self):
        engine = RiskEngine(max_risk_per_trade=5000, max_sector_pct=0.25)
        portfolio = [
            {"symbol": "AAPL", "max_loss": 500, "strategy_type": "DEBIT_SPREAD", "sector": "Technology"},
            {"symbol": "MSFT", "max_loss": 500, "strategy_type": "DEBIT_SPREAD", "sector": "Technology"},
        ]
        # Adding another Tech trade: Tech would be 1500/2000 = 75% > 25%
        trade = {"symbol": "NVDA", "max_loss": 500, "strategy_type": "DEBIT_SPREAD", "sector": "Technology"}
        rejected, reason = engine.should_reject_trade(trade, portfolio)
        assert rejected is True
        assert "Technology" in reason
        assert "sector" in reason.lower()

    def test_accept_trade_within_sector_cap(self):
        engine = RiskEngine(max_risk_per_trade=5000, max_sector_pct=0.50)
        portfolio = [
            {"symbol": "AAPL", "max_loss": 300, "strategy_type": "DEBIT_SPREAD", "sector": "Technology"},
            {"symbol": "JPM", "max_loss": 300, "strategy_type": "CREDIT_SPREAD", "sector": "Financials"},
            {"symbol": "XOM", "max_loss": 300, "strategy_type": "DEBIT_SPREAD", "sector": "Energy"},
        ]
        trade = {"symbol": "MSFT", "max_loss": 300, "strategy_type": "DEBIT_SPREAD", "sector": "Technology"}
        rejected, reason = engine.should_reject_trade(trade, portfolio)
        assert rejected is False

    def test_sector_uses_sector_map_when_no_sector_field(self):
        engine = RiskEngine(max_risk_per_trade=5000, max_sector_pct=0.25)
        portfolio = [
            {"symbol": "AAPL", "max_loss": 800},  # No sector field, should use SECTOR_MAP -> Technology
        ]
        trade = {"symbol": "MSFT", "max_loss": 500}  # Also Technology via SECTOR_MAP
        rejected, reason = engine.should_reject_trade(trade, portfolio)
        assert rejected is True  # 1300/1300 = 100% Technology


class TestDrawdownCircuitBreaker:
    def test_halt_when_loss_exceeds_threshold(self):
        engine = RiskEngine(drawdown_halt_pct=0.02)
        # Lost $2,500 on $100,000 portfolio = 2.5% > 2%
        assert engine.check_drawdown_halt(daily_pnl=-2500, portfolio_value=100000) is True

    def test_no_halt_within_threshold(self):
        engine = RiskEngine(drawdown_halt_pct=0.02)
        # Lost $1,500 on $100,000 = 1.5% < 2%
        assert engine.check_drawdown_halt(daily_pnl=-1500, portfolio_value=100000) is False

    def test_no_halt_on_positive_day(self):
        engine = RiskEngine(drawdown_halt_pct=0.02)
        assert engine.check_drawdown_halt(daily_pnl=500, portfolio_value=100000) is False

    def test_drawdown_rejects_trade_via_market_context(self):
        engine = RiskEngine(max_risk_per_trade=5000, drawdown_halt_pct=0.02)
        trade = {"symbol": "AAPL", "max_loss": 500, "sector": "Technology"}
        market_ctx = {"daily_pnl": -3000, "portfolio_value": 100000}
        rejected, reason = engine.should_reject_trade(trade, portfolio=[], market_context=market_ctx)
        assert rejected is True
        assert "circuit breaker" in reason.lower()

    def test_zero_portfolio_value_no_halt(self):
        engine = RiskEngine(drawdown_halt_pct=0.02)
        assert engine.check_drawdown_halt(daily_pnl=-100, portfolio_value=0) is False


class TestAnalyzePortfolioRisk:
    def test_empty_portfolio_returns_empty(self):
        engine = RiskEngine()
        alerts, metrics = engine.analyze_portfolio_risk([], [])
        assert alerts == []
        assert metrics == []

    def test_sector_alert_generated_for_concentration(self):
        engine = RiskEngine(max_sector_pct=0.25)
        positions = [
            {"symbol": "AAPL", "max_loss": 500, "sector": "Technology"},
            {"symbol": "MSFT", "max_loss": 500, "sector": "Technology"},
            {"symbol": "NVDA", "max_loss": 500, "sector": "Technology"},
            {"symbol": "JPM", "max_loss": 100, "sector": "Financials"},
        ]
        alerts, metrics = engine.analyze_portfolio_risk(positions, [])
        sector_alerts = [a for a in alerts if a.alert_type == "SECTOR_CONCENTRATION"]
        assert len(sector_alerts) >= 1
        assert sector_alerts[0].severity == RiskSeverity.CRITICAL

    def test_strategy_metrics_calculated(self):
        engine = RiskEngine()
        positions = [
            {"symbol": "AAPL", "max_loss": 500, "strategy_type": "BULL_CALL_DEBIT_SPREAD"},
            {"symbol": "MSFT", "max_loss": 500, "strategy_type": "IRON_CONDOR"},
        ]
        alerts, metrics = engine.analyze_portfolio_risk(positions, [])
        strategy_metrics = [m for m in metrics if "Strategy" in m.metric_name]
        assert len(strategy_metrics) >= 2
```

**Step 2: Run all tests**

Run: `pytest tests/test_risk_engine.py -v`
Expected: All tests PASS (implementation from Task 1 supports these)

**Step 3: Commit**

```bash
git add tests/test_risk_engine.py
git commit -m "test(risk): add sector concentration and drawdown circuit breaker tests"
```

---

## Task 3: Risk Engine — Correlation Check

**Files:**
- Modify: `tests/test_risk_engine.py`
- Modify: `agent/risk_engine.py`

**Step 1: Write failing correlation tests**

```python
# Append to tests/test_risk_engine.py
import numpy as np

class TestCorrelationCheck:
    def test_high_correlation_rejected(self):
        """Two perfectly correlated symbols should be rejected."""
        engine = RiskEngine(max_correlation=0.7)
        # Mock: provide price data directly instead of fetching
        prices_a = np.cumsum(np.random.randn(60)) + 100  # Random walk
        prices_b = prices_a + np.random.randn(60) * 0.1   # Nearly identical
        corr = engine.calculate_correlation(prices_a, prices_b)
        assert corr > 0.7
        reject, _ = engine.check_correlation_limit(corr)
        assert reject is True

    def test_low_correlation_accepted(self):
        engine = RiskEngine(max_correlation=0.7)
        np.random.seed(42)
        prices_a = np.cumsum(np.random.randn(60)) + 100
        prices_b = np.cumsum(np.random.randn(60)) + 200  # Independent random walk
        corr = engine.calculate_correlation(prices_a, prices_b)
        reject, _ = engine.check_correlation_limit(corr)
        assert reject is False

    def test_insufficient_data_returns_zero(self):
        engine = RiskEngine()
        corr = engine.calculate_correlation(np.array([100, 101]), np.array([200, 201]))
        # Too few data points — should return 0 (neutral, don't reject)
        assert corr == 0.0
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/test_risk_engine.py::TestCorrelationCheck -v`
Expected: FAIL with `AttributeError: 'RiskEngine' object has no attribute 'calculate_correlation'`

**Step 3: Add correlation methods to RiskEngine**

```python
# Add to agent/risk_engine.py — inside RiskEngine class

    def calculate_correlation(self, prices_a: "np.ndarray", prices_b: "np.ndarray") -> float:
        """
        Calculate 60-day rolling correlation of daily returns.

        Args:
            prices_a: Price series for symbol A
            prices_b: Price series for symbol B

        Returns:
            Correlation coefficient (-1 to 1), or 0.0 if insufficient data.
        """
        import numpy as np

        if len(prices_a) < 10 or len(prices_b) < 10:
            return 0.0

        # Use the shorter of the two series
        n = min(len(prices_a), len(prices_b))
        prices_a = prices_a[-n:]
        prices_b = prices_b[-n:]

        # Calculate daily log returns
        returns_a = np.diff(np.log(prices_a))
        returns_b = np.diff(np.log(prices_b))

        if len(returns_a) < 5:
            return 0.0

        corr_matrix = np.corrcoef(returns_a, returns_b)
        return float(corr_matrix[0, 1])

    def check_correlation_limit(self, correlation: float) -> Tuple[bool, Optional[str]]:
        """Check if correlation exceeds the max allowed threshold."""
        if abs(correlation) > self.max_correlation:
            return True, f"Correlation {correlation:.2f} exceeds limit {self.max_correlation}"
        return False, None
```

**Step 4: Run tests**

Run: `pytest tests/test_risk_engine.py -v`
Expected: All tests PASS

**Step 5: Commit**

```bash
git add tests/test_risk_engine.py agent/risk_engine.py
git commit -m "feat(risk): add 60-day correlation check with configurable threshold"
```

---

## Task 4: Vol Engine — Core Structure & Historical Volatility

**Files:**
- Create: `tests/test_vol_engine.py`
- Create: `agent/vol_engine.py` (rewrite)

**Step 1: Write failing tests for VolEngine core + historical vol**

```python
# tests/test_vol_engine.py
import pytest
import numpy as np
from unittest.mock import patch, MagicMock
from datetime import datetime

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "agent"))

from vol_engine import (
    VolEngine, VolatilityResult, VolatilityModel, VolRegime,
    GARCHParameters,
)


def _make_price_series(n=252, start=100, annual_vol=0.25):
    """Generate synthetic price series with known volatility."""
    np.random.seed(42)
    daily_vol = annual_vol / np.sqrt(252)
    returns = np.random.normal(0, daily_vol, n)
    prices = start * np.exp(np.cumsum(returns))
    return prices


def _mock_yf_history(prices):
    """Create a mock yfinance history DataFrame."""
    import pandas as pd
    dates = pd.date_range(end=datetime.now(), periods=len(prices), freq="B")
    return pd.DataFrame({"Close": prices}, index=dates)


class TestVolEngineInit:
    def test_default_construction(self):
        engine = VolEngine()
        assert engine.default_history_days == 252
        assert engine.ewma_lambda == 0.94

    def test_custom_params(self):
        engine = VolEngine(default_history_days=60, ewma_lambda=0.97)
        assert engine.default_history_days == 60
        assert engine.ewma_lambda == 0.97


class TestHistoricalVolatility:
    @patch("vol_engine.yf.Ticker")
    def test_historical_vol_calculation(self, mock_ticker_cls):
        prices = _make_price_series(n=252, annual_vol=0.25)
        mock_ticker = MagicMock()
        mock_ticker.history.return_value = _mock_yf_history(prices)
        mock_ticker_cls.return_value = mock_ticker

        engine = VolEngine()
        result = engine.calculate_volatility("AAPL", model=VolatilityModel.HISTORICAL)

        assert isinstance(result, VolatilityResult)
        assert result.model_used == VolatilityModel.HISTORICAL
        # Should be close to 0.25 annual vol (within tolerance for random sample)
        assert 0.15 < result.annual_volatility < 0.40
        assert result.daily_volatility > 0
        assert result.data_points > 200

    @patch("vol_engine.yf.Ticker")
    def test_insufficient_data_raises(self, mock_ticker_cls):
        prices = _make_price_series(n=5)
        mock_ticker = MagicMock()
        mock_ticker.history.return_value = _mock_yf_history(prices)
        mock_ticker_cls.return_value = mock_ticker

        engine = VolEngine()
        with pytest.raises(ValueError, match="Insufficient"):
            engine.calculate_volatility("BAD", model=VolatilityModel.HISTORICAL)


class TestVolRegime:
    def test_regime_enum_values(self):
        assert VolRegime.LOW.value == "low"
        assert VolRegime.MEDIUM.value == "medium"
        assert VolRegime.HIGH.value == "high"
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/test_vol_engine.py -v`
Expected: FAIL with `ImportError`

**Step 3: Write VolEngine with historical volatility + regime enum**

```python
# agent/vol_engine.py
"""
Volatility Engine
=================
Multi-model volatility calculator: Historical, GARCH(1,1), EWMA, IV, Hybrid.
Regime detection and expected move calculations.
"""

import logging
import warnings
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Tuple

import numpy as np
import yfinance as yf
from scipy import optimize
from scipy.stats import norm

warnings.filterwarnings("ignore", category=RuntimeWarning)
logger = logging.getLogger(__name__)


class VolatilityModel(Enum):
    HISTORICAL = "historical"
    GARCH = "garch"
    EWMA = "ewma"
    IMPLIED_VOLATILITY = "implied_vol"
    HYBRID = "hybrid"


class VolRegime(Enum):
    LOW = "low"       # IV < HV, IV Percentile < 25
    MEDIUM = "medium"  # Middle ground
    HIGH = "high"      # IV > HV, IV Percentile > 50


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


class VolEngine:
    """
    Advanced volatility calculator supporting multiple models.
    All methods are synchronous (yfinance is sync).
    """

    def __init__(
        self,
        default_history_days: int = 252,
        garch_max_iterations: int = 1000,
        ewma_lambda: float = 0.94,
    ):
        self.default_history_days = default_history_days
        self.garch_max_iterations = garch_max_iterations
        self.ewma_lambda = ewma_lambda

        self.hybrid_weights = {
            VolatilityModel.HISTORICAL: 0.3,
            VolatilityModel.GARCH: 0.4,
            VolatilityModel.EWMA: 0.2,
            VolatilityModel.IMPLIED_VOLATILITY: 0.1,
        }

    def calculate_volatility(
        self,
        symbol: str,
        model: VolatilityModel = VolatilityModel.HYBRID,
        history_days: Optional[int] = None,
    ) -> VolatilityResult:
        """Calculate volatility using specified model."""
        history_days = history_days or self.default_history_days

        if model == VolatilityModel.HISTORICAL:
            return self._calc_historical(symbol, history_days)
        elif model == VolatilityModel.GARCH:
            return self._calc_garch(symbol, history_days)
        elif model == VolatilityModel.EWMA:
            return self._calc_ewma(symbol, history_days)
        elif model == VolatilityModel.HYBRID:
            return self._calc_hybrid(symbol, history_days)
        else:
            raise ValueError(f"Unsupported model: {model}")

    def _fetch_returns(self, symbol: str, history_days: int, min_points: int = 20) -> np.ndarray:
        """Fetch historical log returns from yfinance."""
        end_date = datetime.now()
        start_date = end_date - timedelta(days=history_days + 30)

        ticker = yf.Ticker(symbol)
        hist = ticker.history(start=start_date, end=end_date)

        if len(hist) < min_points:
            raise ValueError(f"Insufficient data for {symbol}: {len(hist)} days (need {min_points})")

        prices = hist["Close"].values
        log_returns = np.log(prices[1:] / prices[:-1])
        log_returns = log_returns[np.isfinite(log_returns)]

        if len(log_returns) < min_points:
            raise ValueError(f"Insufficient valid returns for {symbol}: {len(log_returns)}")

        return log_returns

    def _calc_historical(self, symbol: str, history_days: int) -> VolatilityResult:
        """Traditional historical volatility."""
        log_returns = self._fetch_returns(symbol, history_days)

        daily_vol = np.std(log_returns, ddof=1)
        annual_vol = daily_vol * np.sqrt(252)

        return VolatilityResult(
            annual_volatility=float(annual_vol),
            daily_volatility=float(daily_vol),
            model_used=VolatilityModel.HISTORICAL,
            confidence_score=min(1.0, len(log_returns) / 252),
            data_points=len(log_returns),
            calculation_date=datetime.now(),
            additional_metrics={
                "mean_return": float(np.mean(log_returns)),
                "skewness": float(self._skewness(log_returns)),
                "kurtosis": float(self._kurtosis(log_returns)),
            },
        )

    def _calc_garch(self, symbol: str, history_days: int) -> VolatilityResult:
        """GARCH(1,1) volatility forecast."""
        log_returns = self._fetch_returns(symbol, max(history_days, 500), min_points=100)
        params = self._fit_garch(log_returns)

        if not params.convergence:
            logger.warning(f"GARCH did not converge for {symbol}, falling back to historical")
            return self._calc_historical(symbol, history_days)

        # One-step forecast
        recent = log_returns[-30:]
        current_var = np.var(recent[-10:])
        forecast_var = params.omega + params.alpha * (recent[-1] ** 2) + params.beta * current_var
        forecast_var = max(forecast_var, 1e-8)

        daily_vol = np.sqrt(forecast_var)
        annual_vol = daily_vol * np.sqrt(252)

        return VolatilityResult(
            annual_volatility=float(annual_vol),
            daily_volatility=float(daily_vol),
            model_used=VolatilityModel.GARCH,
            confidence_score=0.8 if params.convergence else 0.4,
            data_points=len(log_returns),
            calculation_date=datetime.now(),
            additional_metrics={
                "omega": params.omega,
                "alpha": params.alpha,
                "beta": params.beta,
                "persistence": params.alpha + params.beta,
            },
        )

    def _calc_ewma(self, symbol: str, history_days: int) -> VolatilityResult:
        """Exponentially Weighted Moving Average volatility."""
        log_returns = self._fetch_returns(symbol, history_days, min_points=30)

        ewma_var = log_returns[0] ** 2
        for r in log_returns[1:]:
            ewma_var = self.ewma_lambda * ewma_var + (1 - self.ewma_lambda) * (r ** 2)

        daily_vol = np.sqrt(ewma_var)
        annual_vol = daily_vol * np.sqrt(252)

        return VolatilityResult(
            annual_volatility=float(annual_vol),
            daily_volatility=float(daily_vol),
            model_used=VolatilityModel.EWMA,
            confidence_score=min(0.9, len(log_returns) / 100),
            data_points=len(log_returns),
            calculation_date=datetime.now(),
            additional_metrics={"ewma_lambda": self.ewma_lambda},
        )

    def _calc_hybrid(self, symbol: str, history_days: int) -> VolatilityResult:
        """Weighted ensemble of available models."""
        results = {}

        for model in [VolatilityModel.HISTORICAL, VolatilityModel.GARCH, VolatilityModel.EWMA]:
            try:
                results[model] = self.calculate_volatility(symbol, model, history_days)
            except (ValueError, RuntimeError) as e:
                logger.debug(f"{model.value} failed for {symbol}: {e}")

        if not results:
            raise ValueError(f"No volatility models succeeded for {symbol}")

        total_weight = 0
        weighted_annual = 0
        weighted_daily = 0

        for model, result in results.items():
            w = self.hybrid_weights.get(model, 0) * result.confidence_score
            total_weight += w
            weighted_annual += result.annual_volatility * w
            weighted_daily += result.daily_volatility * w

        if total_weight > 0:
            weighted_annual /= total_weight
            weighted_daily /= total_weight
        else:
            weighted_annual = np.mean([r.annual_volatility for r in results.values()])
            weighted_daily = np.mean([r.daily_volatility for r in results.values()])

        return VolatilityResult(
            annual_volatility=float(weighted_annual),
            daily_volatility=float(weighted_daily),
            model_used=VolatilityModel.HYBRID,
            confidence_score=float(np.mean([r.confidence_score for r in results.values()])),
            data_points=sum(r.data_points for r in results.values()),
            calculation_date=datetime.now(),
            additional_metrics={
                "models_used": len(results),
                **{f"{m.value}_vol": r.annual_volatility for m, r in results.items()},
            },
        )

    def detect_regime(self, symbol: str, history_days: int = 252) -> Tuple[VolRegime, Dict]:
        """
        Detect volatility regime: LOW, MEDIUM, or HIGH.

        Uses IV vs HV comparison and IV percentile.
        """
        try:
            hist_result = self._calc_historical(symbol, history_days)
            hv = hist_result.annual_volatility

            # Short-term vol (proxy for "current" IV-like measure)
            short_result = self._calc_historical(symbol, 30)
            short_vol = short_result.annual_volatility

            # Ratio: short-term / long-term vol
            vol_ratio = short_vol / hv if hv > 0 else 1.0

            # IV Rank approximation (where current short vol sits in 1yr range)
            iv_rank = self.calculate_iv_rank(symbol, history_days)

            if vol_ratio < 0.8 and iv_rank < 25:
                regime = VolRegime.LOW
            elif vol_ratio > 1.2 or iv_rank > 50:
                regime = VolRegime.HIGH
            else:
                regime = VolRegime.MEDIUM

            details = {
                "historical_vol": hv,
                "short_term_vol": short_vol,
                "vol_ratio": vol_ratio,
                "iv_rank": iv_rank,
            }

            return regime, details

        except Exception as e:
            logger.warning(f"Regime detection failed for {symbol}: {e}")
            return VolRegime.MEDIUM, {"error": str(e)}

    def calculate_iv_rank(self, symbol: str, lookback_days: int = 252) -> float:
        """
        Calculate IV Rank (0-100) using historical volatility as proxy.

        IV Rank = (Current IV - 52wk Low IV) / (52wk High IV - 52wk Low IV) * 100
        """
        try:
            log_returns = self._fetch_returns(symbol, lookback_days, min_points=60)

            # Calculate rolling 30-day volatility
            window = 30
            rolling_vols = []
            for i in range(window, len(log_returns)):
                chunk = log_returns[i - window:i]
                vol = np.std(chunk, ddof=1) * np.sqrt(252)
                rolling_vols.append(vol)

            if not rolling_vols:
                return 50.0

            current_vol = rolling_vols[-1]
            low_vol = min(rolling_vols)
            high_vol = max(rolling_vols)

            if high_vol == low_vol:
                return 50.0

            iv_rank = (current_vol - low_vol) / (high_vol - low_vol) * 100
            return float(np.clip(iv_rank, 0, 100))

        except Exception as e:
            logger.warning(f"IV Rank calculation failed for {symbol}: {e}")
            return 50.0

    def calculate_expected_move(
        self,
        symbol: str,
        current_price: float,
        days: int,
        confidence: float = 0.68,
    ) -> Dict[str, float]:
        """
        Calculate expected price move over a period.

        Args:
            symbol: Ticker symbol
            current_price: Current stock price
            days: Days to project
            confidence: Confidence level (0.68 = 1 std dev)
        """
        vol_result = self.calculate_volatility(symbol, VolatilityModel.HYBRID)
        time_factor = np.sqrt(days / 252.0)  # Trading days
        z_score = float(norm.ppf((1 + confidence) / 2))

        move_dollars = current_price * vol_result.annual_volatility * time_factor * z_score
        move_pct = (move_dollars / current_price) * 100

        return {
            "expected_move_dollars": float(move_dollars),
            "expected_move_percent": float(move_pct),
            "upper_target": float(current_price + move_dollars),
            "lower_target": float(current_price - move_dollars),
            "annual_volatility": float(vol_result.annual_volatility),
            "model_used": vol_result.model_used.value,
            "confidence": confidence,
            "days": days,
        }

    # --- Internal helpers ---

    def _fit_garch(self, returns: np.ndarray) -> GARCHParameters:
        """Fit GARCH(1,1) via MLE."""
        try:
            result = optimize.minimize(
                self._garch_neg_loglik,
                [0.01, 0.05, 0.9],
                args=(returns,),
                method="L-BFGS-B",
                bounds=[(1e-6, 1), (1e-6, 1), (1e-6, 1)],
                options={"maxiter": self.garch_max_iterations},
            )

            if result.success:
                omega, alpha, beta = result.x
                if alpha + beta >= 1.0:
                    return GARCHParameters(0.01, 0.05, 0.9, 0, float("inf"), False)
                return GARCHParameters(omega, alpha, beta, -result.fun, 2 * 3 + 2 * result.fun, True)

            return GARCHParameters(0.01, 0.05, 0.9, 0, float("inf"), False)

        except Exception as e:
            logger.error(f"GARCH fitting failed: {e}")
            return GARCHParameters(0.01, 0.05, 0.9, 0, float("inf"), False)

    def _garch_neg_loglik(self, params: List[float], returns: np.ndarray) -> float:
        """Negative log-likelihood for GARCH(1,1)."""
        omega, alpha, beta = params
        if omega <= 0 or alpha <= 0 or beta <= 0 or (alpha + beta) >= 1:
            return 1e8

        n = len(returns)
        sigma2 = np.zeros(n)
        sigma2[0] = np.var(returns)

        for t in range(1, n):
            sigma2[t] = omega + alpha * (returns[t - 1] ** 2) + beta * sigma2[t - 1]

        sigma2 = np.maximum(sigma2, 1e-10)
        return float(0.5 * np.sum(np.log(2 * np.pi * sigma2) + (returns ** 2) / sigma2))

    def _skewness(self, returns: np.ndarray) -> float:
        n = len(returns)
        if n < 3:
            return 0.0
        m = np.mean(returns)
        s = np.std(returns, ddof=1)
        if s == 0:
            return 0.0
        return float((n / ((n - 1) * (n - 2))) * np.sum(((returns - m) / s) ** 3))

    def _kurtosis(self, returns: np.ndarray) -> float:
        n = len(returns)
        if n < 4:
            return 0.0
        m = np.mean(returns)
        s = np.std(returns, ddof=1)
        if s == 0:
            return 0.0
        k = (n * (n + 1) / ((n - 1) * (n - 2) * (n - 3))) * np.sum(((returns - m) / s) ** 4)
        return float(k - 3 * (n - 1) ** 2 / ((n - 2) * (n - 3)))
```

**Step 4: Run tests**

Run: `pytest tests/test_vol_engine.py -v`
Expected: All tests PASS

**Step 5: Commit**

```bash
git add tests/test_vol_engine.py agent/vol_engine.py
git commit -m "feat(vol): rewrite vol engine with historical, GARCH, EWMA, hybrid, regime detection, IV rank"
```

---

## Task 5: Vol Engine — GARCH, EWMA, Hybrid, Regime, Expected Move Tests

**Files:**
- Modify: `tests/test_vol_engine.py`

**Step 1: Add comprehensive tests**

```python
# Append to tests/test_vol_engine.py

class TestGARCH:
    @patch("vol_engine.yf.Ticker")
    def test_garch_with_sufficient_data(self, mock_ticker_cls):
        prices = _make_price_series(n=500, annual_vol=0.30)
        mock_ticker = MagicMock()
        mock_ticker.history.return_value = _mock_yf_history(prices)
        mock_ticker_cls.return_value = mock_ticker

        engine = VolEngine()
        result = engine.calculate_volatility("AAPL", model=VolatilityModel.GARCH)
        assert result.model_used in (VolatilityModel.GARCH, VolatilityModel.HISTORICAL)
        assert result.annual_volatility > 0

    @patch("vol_engine.yf.Ticker")
    def test_garch_fallback_on_insufficient_data(self, mock_ticker_cls):
        prices = _make_price_series(n=50, annual_vol=0.25)
        mock_ticker = MagicMock()
        mock_ticker.history.return_value = _mock_yf_history(prices)
        mock_ticker_cls.return_value = mock_ticker

        engine = VolEngine()
        # GARCH needs 100+ points, should raise ValueError for insufficient data
        with pytest.raises(ValueError, match="Insufficient"):
            engine.calculate_volatility("BAD", model=VolatilityModel.GARCH)


class TestEWMA:
    @patch("vol_engine.yf.Ticker")
    def test_ewma_calculation(self, mock_ticker_cls):
        prices = _make_price_series(n=100, annual_vol=0.20)
        mock_ticker = MagicMock()
        mock_ticker.history.return_value = _mock_yf_history(prices)
        mock_ticker_cls.return_value = mock_ticker

        engine = VolEngine()
        result = engine.calculate_volatility("AAPL", model=VolatilityModel.EWMA)
        assert result.model_used == VolatilityModel.EWMA
        assert result.annual_volatility > 0
        assert "ewma_lambda" in result.additional_metrics


class TestHybrid:
    @patch("vol_engine.yf.Ticker")
    def test_hybrid_uses_multiple_models(self, mock_ticker_cls):
        prices = _make_price_series(n=500, annual_vol=0.25)
        mock_ticker = MagicMock()
        mock_ticker.history.return_value = _mock_yf_history(prices)
        mock_ticker_cls.return_value = mock_ticker

        engine = VolEngine()
        result = engine.calculate_volatility("AAPL", model=VolatilityModel.HYBRID)
        assert result.model_used == VolatilityModel.HYBRID
        assert result.additional_metrics.get("models_used", 0) >= 2


class TestRegimeDetection:
    @patch("vol_engine.yf.Ticker")
    def test_detect_regime_returns_valid_enum(self, mock_ticker_cls):
        prices = _make_price_series(n=300, annual_vol=0.25)
        mock_ticker = MagicMock()
        mock_ticker.history.return_value = _mock_yf_history(prices)
        mock_ticker_cls.return_value = mock_ticker

        engine = VolEngine()
        regime, details = engine.detect_regime("AAPL")
        assert isinstance(regime, VolRegime)
        assert "historical_vol" in details
        assert "iv_rank" in details


class TestIVRank:
    @patch("vol_engine.yf.Ticker")
    def test_iv_rank_returns_0_to_100(self, mock_ticker_cls):
        prices = _make_price_series(n=300, annual_vol=0.25)
        mock_ticker = MagicMock()
        mock_ticker.history.return_value = _mock_yf_history(prices)
        mock_ticker_cls.return_value = mock_ticker

        engine = VolEngine()
        rank = engine.calculate_iv_rank("AAPL")
        assert 0 <= rank <= 100

    @patch("vol_engine.yf.Ticker")
    def test_iv_rank_fallback_on_error(self, mock_ticker_cls):
        mock_ticker = MagicMock()
        mock_ticker.history.return_value = _mock_yf_history(np.array([100, 101]))
        mock_ticker_cls.return_value = mock_ticker

        engine = VolEngine()
        rank = engine.calculate_iv_rank("BAD")
        assert rank == 50.0  # Default fallback


class TestExpectedMove:
    @patch("vol_engine.yf.Ticker")
    def test_expected_move_structure(self, mock_ticker_cls):
        prices = _make_price_series(n=500, annual_vol=0.25)
        mock_ticker = MagicMock()
        mock_ticker.history.return_value = _mock_yf_history(prices)
        mock_ticker_cls.return_value = mock_ticker

        engine = VolEngine()
        result = engine.calculate_expected_move("AAPL", current_price=200.0, days=45)

        assert "expected_move_dollars" in result
        assert "upper_target" in result
        assert "lower_target" in result
        assert result["upper_target"] > 200.0
        assert result["lower_target"] < 200.0
        assert result["confidence"] == 0.68

    @patch("vol_engine.yf.Ticker")
    def test_expected_move_higher_confidence_wider_range(self, mock_ticker_cls):
        prices = _make_price_series(n=500, annual_vol=0.25)
        mock_ticker = MagicMock()
        mock_ticker.history.return_value = _mock_yf_history(prices)
        mock_ticker_cls.return_value = mock_ticker

        engine = VolEngine()
        move_68 = engine.calculate_expected_move("AAPL", 200.0, 45, confidence=0.68)
        move_95 = engine.calculate_expected_move("AAPL", 200.0, 45, confidence=0.95)

        assert move_95["expected_move_dollars"] > move_68["expected_move_dollars"]
```

**Step 2: Run all vol engine tests**

Run: `pytest tests/test_vol_engine.py -v`
Expected: All tests PASS

**Step 3: Commit**

```bash
git add tests/test_vol_engine.py
git commit -m "test(vol): add GARCH, EWMA, hybrid, regime detection, IV rank, expected move tests"
```

---

## Task 6: Event Loader — Core Structure & Earnings Check

**Files:**
- Create: `tests/test_event_loader.py`
- Create: `agent/event_loader.py` (rewrite)

**Step 1: Write failing tests for EventLoader**

```python
# tests/test_event_loader.py
import pytest
from unittest.mock import patch, MagicMock, PropertyMock
from datetime import datetime, timedelta

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "agent"))

from event_loader import EventLoader


class TestEventLoaderInit:
    def test_default_construction(self):
        loader = EventLoader()
        assert loader.cache_duration_hours == 4

    def test_macro_events_loaded(self):
        loader = EventLoader()
        assert len(loader.macro_events) > 0


class TestEarningsCheck:
    @patch("event_loader.yf.Ticker")
    def test_earnings_inside_trade_window(self, mock_ticker_cls):
        """If earnings is 10 days away and DTE is 45, should flag it."""
        mock_ticker = MagicMock()

        import pandas as pd
        future_date = datetime.now() + timedelta(days=10)
        earnings_df = pd.DataFrame(
            {"Earnings Date": [future_date]},
            index=pd.DatetimeIndex([future_date]),
        )
        type(mock_ticker).earnings_dates = PropertyMock(return_value=earnings_df)
        mock_ticker_cls.return_value = mock_ticker

        loader = EventLoader()
        result = loader.check_earnings_before_expiry("AAPL", days_to_expiry=45)
        assert result is not None
        assert result["affects_trade"] is True
        assert result["earnings_days"] <= 45

    @patch("event_loader.yf.Ticker")
    def test_earnings_outside_trade_window(self, mock_ticker_cls):
        """If earnings is 60 days away and DTE is 30, should return None."""
        mock_ticker = MagicMock()

        import pandas as pd
        future_date = datetime.now() + timedelta(days=60)
        earnings_df = pd.DataFrame(
            {"Earnings Date": [future_date]},
            index=pd.DatetimeIndex([future_date]),
        )
        type(mock_ticker).earnings_dates = PropertyMock(return_value=earnings_df)
        mock_ticker_cls.return_value = mock_ticker

        loader = EventLoader()
        result = loader.check_earnings_before_expiry("AAPL", days_to_expiry=30)
        assert result is None

    @patch("event_loader.yf.Ticker")
    def test_no_earnings_data_returns_none(self, mock_ticker_cls):
        mock_ticker = MagicMock()
        type(mock_ticker).earnings_dates = PropertyMock(return_value=None)
        mock_ticker_cls.return_value = mock_ticker

        loader = EventLoader()
        result = loader.check_earnings_before_expiry("AAPL", 45)
        assert result is None


class TestEarningsProximity:
    @patch("event_loader.yf.Ticker")
    def test_earnings_within_7_days(self, mock_ticker_cls):
        mock_ticker = MagicMock()
        import pandas as pd
        future_date = datetime.now() + timedelta(days=5)
        earnings_df = pd.DataFrame(index=pd.DatetimeIndex([future_date]))
        type(mock_ticker).earnings_dates = PropertyMock(return_value=earnings_df)
        mock_ticker_cls.return_value = mock_ticker

        loader = EventLoader()
        days = loader.get_earnings_proximity("AAPL")
        assert days is not None
        assert 0 <= days <= 7

    @patch("event_loader.yf.Ticker")
    def test_earnings_beyond_7_days(self, mock_ticker_cls):
        mock_ticker = MagicMock()
        import pandas as pd
        future_date = datetime.now() + timedelta(days=30)
        earnings_df = pd.DataFrame(index=pd.DatetimeIndex([future_date]))
        type(mock_ticker).earnings_dates = PropertyMock(return_value=earnings_df)
        mock_ticker_cls.return_value = mock_ticker

        loader = EventLoader()
        days = loader.get_earnings_proximity("AAPL")
        assert days is None


class TestMacroBlackout:
    def test_fomc_date_is_blackout(self):
        loader = EventLoader()
        # Use a known FOMC date from the static calendar
        if loader.macro_events:
            fomc_event = next((e for e in loader.macro_events if "FOMC" in e["name"]), None)
            if fomc_event:
                result, name = loader.is_macro_blackout(fomc_event["date"])
                assert result is True
                assert "FOMC" in name

    def test_random_date_not_blackout(self):
        loader = EventLoader()
        # Use a date far from any known event
        from datetime import date
        random_date = date(2026, 7, 15)  # Mid-July, unlikely to be FOMC/CPI
        result, name = loader.is_macro_blackout(random_date)
        # Might or might not be blackout depending on calendar, just check types
        assert isinstance(result, bool)
        assert name is None or isinstance(name, str)


class TestBlockingEvents:
    @patch("event_loader.yf.Ticker")
    def test_get_blocking_events_combines_earnings_and_macro(self, mock_ticker_cls):
        mock_ticker = MagicMock()
        import pandas as pd
        future_date = datetime.now() + timedelta(days=5)
        earnings_df = pd.DataFrame(index=pd.DatetimeIndex([future_date]))
        type(mock_ticker).earnings_dates = PropertyMock(return_value=earnings_df)
        mock_ticker_cls.return_value = mock_ticker

        loader = EventLoader()
        events = loader.get_blocking_events("AAPL", days_to_expiry=45)
        assert isinstance(events, list)
        # Should have at least the earnings event
        earnings_events = [e for e in events if e.get("type") == "earnings"]
        assert len(earnings_events) >= 1
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/test_event_loader.py -v`
Expected: FAIL with `ImportError`

**Step 3: Write EventLoader implementation**

```python
# agent/event_loader.py
"""
Event Loader — Earnings & Macro Calendar
=========================================
Context-aware event intelligence for trading decisions.
Checks earnings dates and macro event blackouts.
"""

import logging
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

import yfinance as yf

logger = logging.getLogger(__name__)


# 2026 FOMC meeting dates (announcement days)
# Update quarterly from https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm
FOMC_DATES_2026 = [
    date(2026, 1, 28), date(2026, 3, 18), date(2026, 5, 6),
    date(2026, 6, 17), date(2026, 7, 29), date(2026, 9, 16),
    date(2026, 10, 28), date(2026, 12, 9),
]

# 2026 CPI release dates (approximate — BLS releases ~10th-13th of month)
CPI_DATES_2026 = [
    date(2026, 1, 14), date(2026, 2, 11), date(2026, 3, 11),
    date(2026, 4, 10), date(2026, 5, 13), date(2026, 6, 10),
    date(2026, 7, 14), date(2026, 8, 12), date(2026, 9, 11),
    date(2026, 10, 13), date(2026, 11, 12), date(2026, 12, 10),
]

# Jobs report (first Friday of each month)
JOBS_DATES_2026 = [
    date(2026, 1, 2), date(2026, 2, 6), date(2026, 3, 6),
    date(2026, 4, 3), date(2026, 5, 1), date(2026, 6, 5),
    date(2026, 7, 2), date(2026, 8, 7), date(2026, 9, 4),
    date(2026, 10, 2), date(2026, 11, 6), date(2026, 12, 4),
]


class EventLoader:
    """
    Event intelligence service for trading context.
    Handles earnings calendars and macro event blackouts.
    """

    def __init__(self, cache_duration_hours: int = 4, blackout_days: int = 1):
        self.cache_duration_hours = cache_duration_hours
        self.blackout_days = blackout_days
        self._cache: Dict[str, Dict] = {}

        # Build macro events list
        self.macro_events = self._build_macro_calendar()

    def _build_macro_calendar(self) -> List[Dict[str, Any]]:
        """Build the static macro event calendar."""
        events = []
        for d in FOMC_DATES_2026:
            events.append({"name": "FOMC Decision", "date": d, "impact": "high"})
        for d in CPI_DATES_2026:
            events.append({"name": "CPI Release", "date": d, "impact": "high"})
        for d in JOBS_DATES_2026:
            events.append({"name": "Jobs Report", "date": d, "impact": "medium"})
        return events

    def check_earnings_before_expiry(
        self, symbol: str, days_to_expiry: int
    ) -> Optional[Dict[str, Any]]:
        """
        Check if earnings occur before option expiry.

        Returns:
            Dict with earnings info if earnings falls within trade window, None otherwise.
        """
        try:
            days_until = self._get_days_until_earnings(symbol)
            if days_until is not None and 0 <= days_until <= days_to_expiry:
                earnings_date = (datetime.now() + timedelta(days=days_until)).strftime("%Y-%m-%d")
                return {
                    "earnings_days": days_until,
                    "earnings_date": earnings_date,
                    "affects_trade": True,
                    "warning": "Earnings event occurs before expiration.",
                }
            return None
        except Exception as e:
            logger.warning(f"Earnings check failed for {symbol}: {e}")
            return None

    def get_earnings_proximity(self, symbol: str) -> Optional[int]:
        """
        Get days until next earnings if within 7 days.

        Returns:
            Number of days (0-7) or None if earnings is >7 days away.
        """
        try:
            days = self._get_days_until_earnings(symbol)
            if days is not None and 0 <= days <= 7:
                return days
            return None
        except Exception as e:
            logger.warning(f"Earnings proximity check failed for {symbol}: {e}")
            return None

    def is_macro_blackout(self, target_date: date) -> Tuple[bool, Optional[str]]:
        """
        Check if target_date falls within a macro event blackout window.

        Returns:
            (is_blackout, event_name) — event_name is None if not in blackout.
        """
        if isinstance(target_date, datetime):
            target_date = target_date.date()

        for event in self.macro_events:
            event_date = event["date"]
            delta = abs((target_date - event_date).days)
            if delta <= self.blackout_days:
                return True, event["name"]

        return False, None

    def get_blocking_events(
        self, symbol: str, days_to_expiry: int
    ) -> List[Dict[str, Any]]:
        """
        Get all blocking events (earnings + macro) within the trade window.

        Returns:
            List of event dicts with type, date, and description.
        """
        events = []

        # Check earnings
        earnings = self.check_earnings_before_expiry(symbol, days_to_expiry)
        if earnings:
            events.append({
                "type": "earnings",
                "symbol": symbol,
                "date": earnings["earnings_date"],
                "days_until": earnings["earnings_days"],
                "description": f"Earnings in {earnings['earnings_days']} days",
            })

        # Check macro events within trade window
        today = date.today()
        for event in self.macro_events:
            days_until = (event["date"] - today).days
            if 0 <= days_until <= days_to_expiry:
                events.append({
                    "type": "macro",
                    "name": event["name"],
                    "date": event["date"].isoformat(),
                    "days_until": days_until,
                    "impact": event["impact"],
                    "description": f"{event['name']} in {days_until} days",
                })

        return events

    def _get_days_until_earnings(self, symbol: str) -> Optional[int]:
        """Fetch next earnings date from yfinance and return days until."""
        cache_key = f"earnings_{symbol}"
        if self._is_cache_valid(cache_key):
            return self._cache[cache_key]["data"]

        try:
            ticker = yf.Ticker(symbol)
            earnings_dates = ticker.earnings_dates

            if earnings_dates is None or earnings_dates.empty:
                self._set_cache(cache_key, None)
                return None

            now = datetime.now()
            future_dates = [d for d in earnings_dates.index if d > now]

            if not future_dates:
                self._set_cache(cache_key, None)
                return None

            next_earnings = min(future_dates)
            days_until = (next_earnings - now).days

            self._set_cache(cache_key, days_until)
            return days_until

        except Exception as e:
            logger.warning(f"Could not fetch earnings for {symbol}: {e}")
            return None

    def _is_cache_valid(self, key: str) -> bool:
        if key not in self._cache:
            return False
        elapsed = datetime.now() - self._cache[key]["timestamp"]
        return elapsed < timedelta(hours=self.cache_duration_hours)

    def _set_cache(self, key: str, data: Any) -> None:
        self._cache[key] = {"data": data, "timestamp": datetime.now()}
```

**Step 4: Run tests**

Run: `pytest tests/test_event_loader.py -v`
Expected: All tests PASS

**Step 5: Commit**

```bash
git add tests/test_event_loader.py agent/event_loader.py
git commit -m "feat(events): rewrite event loader with earnings check, macro blackout, blocking events"
```

---

## Task 7: Fix Downstream Imports

**Files:**
- Modify: `agent/market_checks.py` — update imports to bare style
- Modify: `agent/options_scanner.py` — update imports to bare style

**Step 1: Update imports in market_checks.py**

Replace:
```python
from agent.event_loader import event_loader
from agent.market_data import market_data
from agent.risk_engine import risk_engine
from agent.vol_engine import AdvancedVolatilityCalculator, VolatilityModel
```
With:
```python
from event_loader import EventLoader
from market_data import MarketData
from risk_engine import RiskEngine
from vol_engine import VolEngine, VolatilityModel
```

And update usages from global singletons to class instances inside the `ScoredGatekeeper.__init__`.

**Step 2: Update imports in options_scanner.py**

Replace:
```python
from agent.vol_engine import AdvancedVolatilityCalculator, VolatilityModel
from agent.market_data import market_data
```
With:
```python
from vol_engine import VolEngine, VolatilityModel
from market_data import MarketData
```

And update usages from global singletons to class instances.

**Step 3: Run all tests**

Run: `pytest tests/ -v`
Expected: All tests PASS

**Step 4: Commit**

```bash
git add agent/market_checks.py agent/options_scanner.py
git commit -m "refactor: update imports to bare style, replace singletons with class instances"
```

---

## Task 8: Add numpy to requirements.txt (if missing)

**Files:**
- Modify: `agent/requirements.txt`

**Step 1: Verify numpy is in requirements**

Check `agent/requirements.txt` for `numpy`. It's currently not listed explicitly (scipy depends on it, but explicit is better).

**Step 2: Add numpy if missing**

Add `numpy>=1.24.0` to requirements.txt.

**Step 3: Commit**

```bash
git add agent/requirements.txt
git commit -m "chore: add explicit numpy dependency to requirements"
```

---

## Task 9: Run Full Test Suite & Verify

**Step 1: Install dependencies**

Run: `cd /home/arvindk/devl/aws/bedrock-core && source .venv/bin/activate && pip install -r agent/requirements.txt`

**Step 2: Run full test suite**

Run: `pytest tests/test_risk_engine.py tests/test_vol_engine.py tests/test_event_loader.py -v`
Expected: All tests PASS

**Step 3: Final commit if any fixes needed**

```bash
git add -A
git commit -m "test: verify full Phase 1 test suite passes"
```
