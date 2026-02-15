"""
Tests for risk_engine.py — Phase 1 Risk Engine
TDD: Write tests first, then implement to pass.
"""

import os
import sys

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
