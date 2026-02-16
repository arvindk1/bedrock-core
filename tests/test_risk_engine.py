"""
Tests for risk_engine.py — Phase 1 Risk Engine
TDD: Write tests first, then implement to pass.
"""

import os
import sys

import numpy as np

# Allow bare imports from agent/ (matches container layout)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "agent"))

from risk_engine import RiskEngine, RiskSeverity, ConcentrationAlert, RiskMetric


# ---------------------------------------------------------------------------
# TestRiskEngineInit
# ---------------------------------------------------------------------------
class TestRiskEngineInit:
    """Verify constructor defaults and custom overrides."""

    def test_default_thresholds(self):
        engine = RiskEngine()
        assert engine.max_risk_per_trade == 1000.0
        assert engine.max_sector_pct == 0.25
        assert engine.max_correlation == 0.7
        assert engine.drawdown_halt_pct == 0.02

    def test_custom_thresholds(self):
        engine = RiskEngine(
            max_risk_per_trade=500.0,
            max_sector_pct=0.15,
            max_correlation=0.5,
            drawdown_halt_pct=0.03,
        )
        assert engine.max_risk_per_trade == 500.0
        assert engine.max_sector_pct == 0.15
        assert engine.max_correlation == 0.5
        assert engine.drawdown_halt_pct == 0.03


# ---------------------------------------------------------------------------
# TestPerTradeRisk
# ---------------------------------------------------------------------------
class TestPerTradeRisk:
    """Per-trade risk gate: should_reject_trade."""

    def _make_portfolio(self):
        """Diversified portfolio — no single sector dominates."""
        return [
            {"symbol": "AAPL", "strategy": "bull_put_spread", "max_loss": 200.0, "sector": "Technology"},
            {"symbol": "XOM", "strategy": "iron_condor", "max_loss": 200.0, "sector": "Energy"},
            {"symbol": "JPM", "strategy": "bull_put_spread", "max_loss": 200.0, "sector": "Financials"},
            {"symbol": "JNJ", "strategy": "iron_condor", "max_loss": 200.0, "sector": "Healthcare"},
            {"symbol": "BA", "strategy": "bull_put_spread", "max_loss": 200.0, "sector": "Industrials"},
        ]

    def test_reject_trade_exceeding_max_risk(self):
        """A trade whose max_loss exceeds max_risk_per_trade must be rejected."""
        engine = RiskEngine(max_risk_per_trade=500.0)
        trade = {"symbol": "TSLA", "strategy": "bull_call_spread", "max_loss": 600.0, "sector": "Consumer Discretionary"}
        portfolio = self._make_portfolio()

        rejected, reason = engine.should_reject_trade(trade, portfolio, {})
        assert rejected is True
        assert reason is not None
        assert "max_loss" in reason.lower() or "risk" in reason.lower()

    def test_accept_trade_within_max_risk(self):
        """A trade within all limits should be accepted."""
        engine = RiskEngine(max_risk_per_trade=1000.0)
        # Use Consumer Staples (not in portfolio) with small risk — stays under 25%.
        trade = {"symbol": "PG", "strategy": "bull_put_spread", "max_loss": 200.0, "sector": "Consumer Staples"}
        portfolio = self._make_portfolio()

        rejected, reason = engine.should_reject_trade(trade, portfolio, {})
        assert rejected is False
        assert reason is None

    def test_reject_trade_missing_max_loss_defaults_to_reject(self):
        """Trade without max_loss field should be REJECTED for safety."""
        engine = RiskEngine()
        trade = {"symbol": "GOOG", "strategy": "iron_condor"}  # no max_loss
        portfolio = self._make_portfolio()

        rejected, reason = engine.should_reject_trade(trade, portfolio, {})
        assert rejected is True
        assert reason is not None
        assert "max_loss" in reason.lower()


# ---------------------------------------------------------------------------
# TestSectorConcentration
# ---------------------------------------------------------------------------
class TestSectorConcentration:
    """Sector concentration gate via should_reject_trade."""

    def test_reject_trade_breaching_sector_cap(self):
        """Portfolio with 2 Tech positions ($500 each), add 3rd Tech ($500).
        Total Tech = $1500/$2000 = 75% > 25%. Should reject."""
        engine = RiskEngine(max_risk_per_trade=5000)
        portfolio = [
            {"symbol": "AAPL", "strategy": "bull_put_spread", "max_loss": 500.0, "sector": "Technology"},
            {"symbol": "MSFT", "strategy": "iron_condor", "max_loss": 500.0, "sector": "Technology"},
        ]
        trade = {"symbol": "GOOG", "strategy": "bull_call_spread", "max_loss": 500.0, "sector": "Technology"}

        rejected, reason = engine.should_reject_trade(trade, portfolio, {})
        assert rejected is True
        assert "Technology" in reason
        assert "sector" in reason.lower()

    def test_accept_trade_within_sector_cap(self):
        """Diversified portfolio (Tech, Financials, Energy at $300 each),
        add another Tech ($300) with max_sector_pct=0.50.
        Tech = $600/$1200 = 50%. Should pass."""
        engine = RiskEngine(max_risk_per_trade=5000, max_sector_pct=0.50)
        portfolio = [
            {"symbol": "AAPL", "strategy": "bull_put_spread", "max_loss": 300.0, "sector": "Technology"},
            {"symbol": "JPM", "strategy": "iron_condor", "max_loss": 300.0, "sector": "Financials"},
            {"symbol": "XOM", "strategy": "bull_put_spread", "max_loss": 300.0, "sector": "Energy"},
        ]
        trade = {"symbol": "MSFT", "strategy": "iron_condor", "max_loss": 300.0, "sector": "Technology"}

        rejected, reason = engine.should_reject_trade(trade, portfolio, {})
        assert rejected is False
        assert reason is None

    def test_sector_uses_sector_map_when_no_sector_field(self):
        """Portfolio with AAPL ($800, no sector field), add MSFT ($500, no sector field).
        Both should map to Technology via SECTOR_MAP. 100% Tech > 25%. Should reject."""
        engine = RiskEngine(max_risk_per_trade=5000)
        portfolio = [
            {"symbol": "AAPL", "strategy": "bull_put_spread", "max_loss": 800.0},
        ]
        trade = {"symbol": "MSFT", "strategy": "iron_condor", "max_loss": 500.0}

        rejected, reason = engine.should_reject_trade(trade, portfolio, {})
        assert rejected is True
        assert "Technology" in reason
        assert "sector" in reason.lower()


# ---------------------------------------------------------------------------
# TestDrawdownCircuitBreaker
# ---------------------------------------------------------------------------
class TestDrawdownCircuitBreaker:
    """Drawdown circuit breaker via check_drawdown_halt and should_reject_trade."""

    def test_halt_when_loss_exceeds_threshold(self):
        """Lost $2500 on $100k = 2.5% > 2%. Should halt."""
        engine = RiskEngine()
        assert engine.check_drawdown_halt(daily_pnl=-2500.0, portfolio_value=100_000.0) is True

    def test_no_halt_within_threshold(self):
        """Lost $1500 on $100k = 1.5% < 2%. Should not halt."""
        engine = RiskEngine()
        assert engine.check_drawdown_halt(daily_pnl=-1500.0, portfolio_value=100_000.0) is False

    def test_no_halt_on_positive_day(self):
        """Gained $500 on $100k. Should not halt."""
        engine = RiskEngine()
        assert engine.check_drawdown_halt(daily_pnl=500.0, portfolio_value=100_000.0) is False

    def test_drawdown_rejects_trade_via_market_context(self):
        """Trade with max_loss=500, market_context has daily_pnl=-3000,
        portfolio_value=100000. Should reject with 'circuit breaker' in reason."""
        engine = RiskEngine(max_risk_per_trade=5000)
        portfolio = [
            {"symbol": "AAPL", "strategy": "bull_put_spread", "max_loss": 500.0, "sector": "Technology"},
            {"symbol": "JPM", "strategy": "iron_condor", "max_loss": 500.0, "sector": "Financials"},
            {"symbol": "XOM", "strategy": "bull_put_spread", "max_loss": 500.0, "sector": "Energy"},
            {"symbol": "JNJ", "strategy": "iron_condor", "max_loss": 500.0, "sector": "Healthcare"},
            {"symbol": "BA", "strategy": "bull_put_spread", "max_loss": 500.0, "sector": "Industrials"},
        ]
        trade = {"symbol": "DIS", "strategy": "iron_condor", "max_loss": 500.0, "sector": "Communication Services"}
        market_context = {"daily_pnl": -3000.0, "portfolio_value": 100_000.0}

        rejected, reason = engine.should_reject_trade(trade, portfolio, market_context)
        assert rejected is True
        # Check for structured reason code format
        assert "RISK_REJECT" in reason or "rule=" in reason
        assert "DRAWDOWN_HALT" in reason or "drawdown" in reason.lower()

    def test_zero_portfolio_value_no_halt(self):
        """Zero portfolio value, should not halt (no division by zero)."""
        engine = RiskEngine()
        assert engine.check_drawdown_halt(daily_pnl=-100.0, portfolio_value=0.0) is False


# ---------------------------------------------------------------------------
# TestAnalyzePortfolioRisk
# ---------------------------------------------------------------------------
class TestAnalyzePortfolioRisk:
    """Portfolio-level risk analysis via analyze_portfolio_risk."""

    def test_empty_portfolio_returns_empty(self):
        """Empty positions, empty proposed. Should return ([], [])."""
        engine = RiskEngine()
        alerts, metrics = engine.analyze_portfolio_risk(positions=[], proposed_trades=[])
        assert alerts == []
        assert metrics == []

    def test_sector_alert_generated_for_concentration(self):
        """3 Tech ($500 each) + 1 Financials ($100).
        Tech = $1500/$1600 = 93.75% > 25%. Should have SECTOR_CONCENTRATION alert
        with CRITICAL severity."""
        engine = RiskEngine()
        positions = [
            {"symbol": "AAPL", "strategy": "bull_put_spread", "max_loss": 500.0, "sector": "Technology"},
            {"symbol": "MSFT", "strategy": "iron_condor", "max_loss": 500.0, "sector": "Technology"},
            {"symbol": "GOOG", "strategy": "bull_call_spread", "max_loss": 500.0, "sector": "Technology"},
            {"symbol": "JPM", "strategy": "iron_condor", "max_loss": 100.0, "sector": "Financials"},
        ]

        alerts, metrics = engine.analyze_portfolio_risk(positions=positions)
        sector_alerts = [a for a in alerts if a.alert_type == "SECTOR_CONCENTRATION"]
        assert len(sector_alerts) >= 1
        tech_alert = [a for a in sector_alerts if "Technology" in a.message]
        assert len(tech_alert) == 1
        assert tech_alert[0].severity == RiskSeverity.CRITICAL

    def test_strategy_metrics_calculated(self):
        """1 BULL_CALL_DEBIT_SPREAD + 1 IRON_CONDOR.
        Should have >= 2 strategy metrics."""
        engine = RiskEngine()
        positions = [
            {"symbol": "AAPL", "strategy": "bull_call_spread", "max_loss": 500.0, "sector": "Technology"},
            {"symbol": "JPM", "strategy": "iron_condor", "max_loss": 500.0, "sector": "Financials"},
        ]

        alerts, metrics = engine.analyze_portfolio_risk(positions=positions)
        strategy_metrics = [m for m in metrics if m.metric_name.startswith("Strategy:")]
        assert len(strategy_metrics) >= 2


# ---------------------------------------------------------------------------
# TestCorrelationCheck
# ---------------------------------------------------------------------------
class TestCorrelationCheck:
    """Correlation check: calculate_correlation and check_correlation_limit."""

    def test_high_correlation_rejected(self):
        """Two nearly identical price series should have high correlation (>0.7)
        and check_correlation_limit should reject it."""
        engine = RiskEngine()
        np.random.seed(99)
        prices_a = 100.0 + np.cumsum(np.random.randn(60) * 0.5)
        prices_b = prices_a + np.random.randn(60) * 0.01  # tiny noise

        corr = engine.calculate_correlation(prices_a, prices_b)
        assert corr > 0.7, f"Expected high correlation, got {corr}"

        rejected, reason = engine.check_correlation_limit(corr)
        assert rejected is True
        assert reason is not None
        assert "correlation" in reason.lower()

    def test_low_correlation_accepted(self):
        """Two independent random walks should have low correlation
        and check_correlation_limit should accept it."""
        engine = RiskEngine()
        np.random.seed(42)
        prices_a = 100.0 + np.cumsum(np.random.randn(60) * 0.5)
        prices_b = 100.0 + np.cumsum(np.random.randn(60) * 0.5)

        corr = engine.calculate_correlation(prices_a, prices_b)
        rejected, reason = engine.check_correlation_limit(corr)
        assert rejected is False
        assert reason is None

    def test_insufficient_data_returns_zero(self):
        """Only 2 data points each. calculate_correlation should return 0.0."""
        engine = RiskEngine()
        prices_a = np.array([100.0, 101.0])
        prices_b = np.array([200.0, 202.0])

        corr = engine.calculate_correlation(prices_a, prices_b)
        assert corr == 0.0
