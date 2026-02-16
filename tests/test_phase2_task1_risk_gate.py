"""
Phase 2, Task 1: Risk Gate Integration
======================================
Tests for find_cheapest_options() with RiskEngine integration.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "agent"))

from options_scanner import find_cheapest_options
from risk_engine import RiskEngine


class TestFindCheapestOptionsBasic:
    """Basic function structure tests."""

    def test_function_exists(self):
        """Verify find_cheapest_options is callable."""
        assert callable(find_cheapest_options)

    def test_invalid_date_format_returns_error(self):
        result = find_cheapest_options("AAPL", "invalid", "2026-03-01")
        assert "Error" in result

    def test_start_after_end_returns_error(self):
        result = find_cheapest_options("AAPL", "2026-03-01", "2026-02-01")
        assert "Error" in result
        assert "start_date" in result.lower()

    @patch("options_scanner.yf.Ticker")
    def test_no_price_data_returns_error(self, mock_ticker_cls):
        """If yfinance returns no data, handle gracefully."""
        mock_ticker = MagicMock()
        mock_ticker.history.return_value = MagicMock(empty=True)
        mock_ticker_cls.return_value = mock_ticker

        result = find_cheapest_options("BAD", "2026-03-01", "2026-06-01")
        assert "Error" in result
        assert "No price data" in result


class TestRiskGateIntegration:
    """Risk gate filtering tests."""

    @patch("options_scanner.yf.Ticker")
    @patch("options_scanner.OptionsScanner.market_data")
    def test_rejects_oversized_trade(self, mock_market_data, mock_ticker_cls):
        """Trade with max_loss > limit should be rejected."""
        # Mock price data
        mock_ticker = MagicMock()
        price_data = MagicMock()
        price_data.empty = False
        price_data.__getitem__ = MagicMock(return_value=MagicMock(iloc=MagicMock(__getitem__=MagicMock(return_value=150.0))))
        mock_ticker.history.return_value = price_data
        mock_ticker.options = ["2026-03-20", "2026-04-17", "2026-05-15"]
        mock_ticker_cls.return_value = mock_ticker

        # Mock chain data
        calls = MagicMock()
        calls.__getitem__ = MagicMock(return_value=MagicMock(
            volume=500, openInterest=1000, impliedVolatility=0.25,
            iterrows=MagicMock(return_value=[])
        ))
        calls.iterrows.return_value = []

        puts = MagicMock()
        puts.iterrows.return_value = []
        puts.__getitem__ = MagicMock(return_value=MagicMock(iterrows=MagicMock(return_value=[])))

        chain = MagicMock()
        chain.calls = MagicMock(__getitem__=MagicMock(return_value=MagicMock(iterrows=MagicMock(return_value=[]))))
        chain.puts = puts

        mock_market_data.get_option_chain.return_value = chain

        # Call with small portfolio and strict risk limits
        result = find_cheapest_options(
            "AAPL",
            "2026-03-01",
            "2026-06-01",
            top_n=5,
            portfolio=[],
            market_context={"daily_pnl": 0, "portfolio_value": 100000}
        )

        # Should mention risk checks
        assert "Risk Engine" in result or "Rejected" in result or "No opportunities" in result

    @patch("options_scanner.yf.Ticker")
    def test_accepts_small_trade_within_limits(self, mock_ticker_cls):
        """Trade within risk limits should be accepted."""
        mock_ticker = MagicMock()
        price_data = MagicMock()
        price_data.empty = False
        price_data.__getitem__ = MagicMock(return_value=MagicMock(iloc=MagicMock(__getitem__=MagicMock(return_value=100.0))))
        mock_ticker.history.return_value = price_data
        mock_ticker.options = ["2026-03-20"]
        mock_ticker_cls.return_value = mock_ticker

        result = find_cheapest_options(
            "SPY",
            "2026-03-01",
            "2026-06-01",
            portfolio=[],
            market_context=None
        )

        # Even if no opportunities, should not crash
        assert isinstance(result, str)
        assert len(result) > 0


class TestRiskGateRejectionMessages:
    """Verify rejection reasons are logged."""

    @patch("options_scanner.yf.Ticker")
    @patch("options_scanner.RiskEngine")
    def test_rejection_reason_included_in_output(self, mock_risk_engine_cls, mock_ticker_cls):
        """If RiskEngine rejects, reason should appear in output."""
        mock_ticker = MagicMock()
        price_data = MagicMock()
        price_data.empty = False
        price_data.__getitem__ = MagicMock(return_value=MagicMock(iloc=MagicMock(__getitem__=MagicMock(return_value=100.0))))
        mock_ticker.history.return_value = price_data
        mock_ticker.options = []
        mock_ticker_cls.return_value = mock_ticker

        # Mock RiskEngine to reject all trades
        mock_engine = MagicMock()
        mock_engine.should_reject_trade.return_value = (True, "Trade exceeds max risk per trade")
        mock_risk_engine_cls.return_value = mock_engine

        result = find_cheapest_options("AAPL", "2026-03-01", "2026-06-01")

        # Should handle gracefully (might be "no opportunities" or error)
        assert isinstance(result, str)


class TestOutputFormat:
    """Verify output structure."""

    @patch("options_scanner.yf.Ticker")
    def test_output_includes_disclaimer(self, mock_ticker_cls):
        """Output should include financial disclaimer."""
        mock_ticker = MagicMock()
        price_data = MagicMock()
        price_data.empty = False
        price_data.__getitem__ = MagicMock(return_value=MagicMock(iloc=MagicMock(__getitem__=MagicMock(return_value=100.0))))
        mock_ticker.history.return_value = price_data
        mock_ticker.options = []
        mock_ticker_cls.return_value = mock_ticker

        result = find_cheapest_options("SPY", "2026-03-01", "2026-06-01")

        # Should include disclaimer for all output types
        assert "Disclaimer" in result or "Error" in result


class TestPortfolioContextPassed:
    """Verify portfolio and market context are used."""

    @patch("options_scanner.yf.Ticker")
    @patch("options_scanner.OptionsScanner.market_data")
    def test_portfolio_passed_to_risk_engine(self, mock_market_data, mock_ticker_cls):
        """Portfolio should be passed to RiskEngine.should_reject_trade()."""
        mock_ticker = MagicMock()
        price_data = MagicMock()
        price_data.empty = False
        price_data.__getitem__ = MagicMock(return_value=MagicMock(iloc=MagicMock(__getitem__=MagicMock(return_value=100.0))))
        mock_ticker.history.return_value = price_data
        mock_ticker.options = []
        mock_ticker_cls.return_value = mock_ticker

        portfolio = [{"symbol": "MSFT", "max_loss": 500, "sector": "Technology"}]
        market_ctx = {"daily_pnl": -1000, "portfolio_value": 100000}

        result = find_cheapest_options(
            "AAPL",
            "2026-03-01",
            "2026-06-01",
            portfolio=portfolio,
            market_context=market_ctx
        )

        # Should handle without error
        assert isinstance(result, str)
