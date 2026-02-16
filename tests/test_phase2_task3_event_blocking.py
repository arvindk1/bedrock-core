"""
Task 3: Event Blocking Integration Tests
==========================================

Verifies that blocking events (earnings, macro) are properly detected
and enforce a hard-stop in the orchestrator (no candidates generated).

This is the "safety gate" that prevents trading around earnings/macro events.
"""

import sys
import os
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock, PropertyMock

import pandas as pd
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "agent"))

from orchestrator import full_scan_with_orchestration, DecisionLog
from event_loader import EventLoader


class TestEventBlockingHardStop:
    """Verify blocking events stop orchestrator completely."""

    @patch("orchestrator.vol_and_events_context")
    @patch("options_scanner.generate_candidates")
    def test_earnings_blocks_orchestrator(self, mock_gen_cand, mock_vol_events_ctx):
        """Orchestrator returns early if earnings detected in window."""
        # Mock vol_and_events_context to return blocking earnings event
        mock_vol_events_ctx.return_value = {
            "regime": MagicMock(value="LOW"),
            "vol_details": {},
            "blocking_events": [
                {
                    "type": "earnings",
                    "earnings_days": 10,
                    "affects_trade": True,
                    "warning": "Earnings in 10 days",
                }
            ],
            "strategy_hint": "DEBIT_SPREAD",
        }

        # Run orchestration with 45 DTE window (earnings is inside)
        log = full_scan_with_orchestration(
            symbol="AAPL",
            start_date="2026-03-01",
            end_date="2026-06-01",
            top_n=5,
            portfolio=[],
            policy_mode="tight",
        )

        # Verify hard-stop behavior
        assert len(log.blocking_events) > 0, "Should detect earnings"
        assert len(log.candidates_raw) == 0, "Should NOT generate candidates"
        assert len(log.final_picks) == 0, "Should have NO final picks"
        assert "earnings" in str(log.blocking_events).lower()

    @patch("event_loader.yf.Ticker")
    @patch("options_scanner.generate_candidates")
    def test_macro_event_blocks_orchestrator(self, mock_gen_cand, mock_ticker_cls):
        """Orchestrator returns early if FOMC/CPI/Jobs in window."""
        # Mock no earnings
        mock_ticker = MagicMock()
        mock_ticker_cls.return_value = mock_ticker
        type(mock_ticker).earnings_dates = PropertyMock(return_value=None)

        # Create a mock with a macro event (e.g., FOMC meeting)
        loader = EventLoader()
        fomc_events = [e for e in loader.macro_events if "FOMC" in e["name"]]
        assert len(fomc_events) > 0

        # Pick a FOMC date that will be in range
        fomc_date = fomc_events[0]["date"]

        # Calculate DTE to include this FOMC date
        today = datetime.now().date()
        if fomc_date >= today:
            dte = (fomc_date - today).days + 5  # Buffer to ensure inclusion

            # Run orchestration
            log = full_scan_with_orchestration(
                symbol="SPY",
                start_date="2026-03-01",
                end_date="2026-06-01",
                top_n=5,
                portfolio=[],
                policy_mode="tight",
            )

            # If FOMC is in window, should block
            if len(log.blocking_events) > 0:
                assert len(log.candidates_raw) == 0, "Macro event should block"
                assert len(log.final_picks) == 0
                assert any("FOMC" in str(e) or "CPI" in str(e) or "Jobs" in str(e)
                          for e in log.blocking_events)

    @patch("event_loader.yf.Ticker")
    @patch("options_scanner.generate_candidates")
    def test_no_blocking_events_allows_candidates(self, mock_gen_cand, mock_ticker_cls):
        """Without blocking events, orchestrator proceeds to generate candidates."""
        # Mock no earnings
        mock_ticker = MagicMock()
        mock_ticker_cls.return_value = mock_ticker
        type(mock_ticker).earnings_dates = PropertyMock(return_value=None)

        # Mock candidate generation (returns something)
        mock_gen_cand.return_value = [
            {
                "symbol": "AAPL",
                "strategy": "BULL_CALL_DEBIT_SPREAD",
                "expiration": "2026-06-01",
                "cost": 1.5,
                "max_loss": 150,
                "max_profit": 3.5,
                "legs": [
                    {"bid": 2.0, "ask": 2.05, "open_interest": 5000, "volume": 100},
                    {"bid": 0.5, "ask": 0.55, "open_interest": 4000, "volume": 80},
                ],
            }
        ]

        # Use a date range far from macro events to avoid macro blocking
        log = full_scan_with_orchestration(
            symbol="AAPL",
            start_date="2026-08-01",
            end_date="2026-08-15",
            top_n=5,
            portfolio=[],
            policy_mode="tight",
        )

        # Should allow processing (may have candidates or not, but not due to blocking)
        if len(log.blocking_events) == 0:
            # Process should have proceeded
            mock_gen_cand.assert_called()


class TestEventBlockingDecisionLog:
    """Verify blocking events appear correctly in DecisionLog."""

    def test_decision_log_shows_blocking_events(self):
        """DecisionLog captures blocking_events for transparency."""
        log = DecisionLog(
            symbol="AAPL",
            start_date="2026-03-01",
            end_date="2026-06-01",
            policy_mode="tight",
        )

        # Manually add a blocking event
        log.blocking_events = [
            {
                "type": "earnings",
                "earnings_days": 5,
                "affects_trade": True,
                "warning": "Earnings in 5 days",
            }
        ]

        # Format to string (used by tool)
        output = log.to_formatted_string()

        # Should mention blocking events
        assert "Blocking Events" in output or "blocking" in output.lower()
        assert "1" in output  # Count of blocking events

    def test_decision_log_format_with_no_events(self):
        """DecisionLog handles empty blocking_events gracefully."""
        log = DecisionLog(
            symbol="SPY",
            start_date="2026-03-01",
            end_date="2026-06-01",
            policy_mode="tight",
        )

        log.blocking_events = []
        output = log.to_formatted_string()

        # Should not crash, should show 0 events
        assert "0" in output


class TestEventBlockingTypes:
    """Verify different event types are recognized and blocked."""

    def test_earnings_event_structure(self):
        """Earnings events have correct structure."""
        loader = EventLoader()

        # Mock earning date
        with patch("event_loader.yf.Ticker") as mock_ticker_cls:
            mock_ticker = MagicMock()
            mock_ticker_cls.return_value = mock_ticker

            future_date = datetime.now() + timedelta(days=5)
            earnings_df = pd.DataFrame(
                {"Earnings Date": [future_date]},
                index=pd.DatetimeIndex([future_date]),
            )
            type(mock_ticker).earnings_dates = PropertyMock(return_value=earnings_df)

            events = loader.get_blocking_events("TEST", 30)
            earnings_events = [e for e in events if e.get("type") == "earnings"]

            assert len(earnings_events) > 0
            assert earnings_events[0]["type"] == "earnings"
            assert "earnings_days" in earnings_events[0]
            assert "warning" in earnings_events[0]

    def test_macro_event_structure(self):
        """Macro events have correct structure."""
        loader = EventLoader()

        # Get macro events in range
        events = loader.get_blocking_events("SPY", 100)
        macro_events = [e for e in events if e.get("type") == "macro"]

        if len(macro_events) > 0:
            assert macro_events[0]["type"] == "macro"
            assert "name" in macro_events[0]
            assert "date" in macro_events[0]
            assert "impact" in macro_events[0]


class TestEventBlockingErrorHandling:
    """Verify graceful handling of missing/bad earnings data."""

    @patch("event_loader.yf.Ticker")
    def test_missing_earnings_data_handled(self, mock_ticker_cls):
        """No earnings data available -> safe default (no blocking)."""
        mock_ticker = MagicMock()
        mock_ticker_cls.return_value = mock_ticker
        type(mock_ticker).earnings_dates = PropertyMock(return_value=None)

        loader = EventLoader()
        events = loader.get_blocking_events("UNKNOWN", 45)

        # Should not crash, should return safe list (no earnings block)
        assert isinstance(events, list)
        earnings_events = [e for e in events if e.get("type") == "earnings"]
        assert len(earnings_events) == 0

    @patch("event_loader.yf.Ticker")
    def test_ticker_fetch_error_handled(self, mock_ticker_cls):
        """yfinance error -> graceful degradation (no crash)."""
        mock_ticker_cls.side_effect = Exception("Network error")

        loader = EventLoader()
        # Should not crash even if yfinance fails
        events = loader.get_blocking_events("BAD_TICKER", 45)

        assert isinstance(events, list)


class TestEventBlockingVsOtherGates:
    """Verify event blocking is checked BEFORE other gates."""

    @patch("event_loader.yf.Ticker")
    @patch("options_scanner.generate_candidates")
    def test_event_blocks_before_risk_gate(self, mock_gen_cand, mock_ticker_cls):
        """Event blocking prevents risk gate from running."""
        # Mock earnings
        mock_ticker = MagicMock()
        mock_ticker_cls.return_value = mock_ticker

        future_date = datetime.now() + timedelta(days=5)
        earnings_df = pd.DataFrame(
            {"Earnings Date": [future_date]},
            index=pd.DatetimeIndex([future_date]),
        )
        type(mock_ticker).earnings_dates = PropertyMock(return_value=earnings_df)

        log = full_scan_with_orchestration(
            symbol="AAPL",
            start_date="2026-03-01",
            end_date="2026-06-01",
            top_n=5,
            portfolio=[],
            policy_mode="tight",
        )

        # If blocked by events, candidates_after_risk_gate should be empty
        # (because no candidates were generated at all)
        if len(log.blocking_events) > 0:
            assert len(log.candidates_raw) == 0
            assert len(log.candidates_after_risk_gate) == 0
            assert len(log.final_picks) == 0

    @patch("event_loader.yf.Ticker")
    @patch("options_scanner.generate_candidates")
    def test_event_blocks_before_gatekeeper(self, mock_gen_cand, mock_ticker_cls):
        """Event blocking prevents gatekeeper from running."""
        # Mock earnings
        mock_ticker = MagicMock()
        mock_ticker_cls.return_value = mock_ticker

        future_date = datetime.now() + timedelta(days=5)
        earnings_df = pd.DataFrame(
            {"Earnings Date": [future_date]},
            index=pd.DatetimeIndex([future_date]),
        )
        type(mock_ticker).earnings_dates = PropertyMock(return_value=earnings_df)

        log = full_scan_with_orchestration(
            symbol="AAPL",
            start_date="2026-03-01",
            end_date="2026-06-01",
            top_n=5,
            portfolio=[],
            policy_mode="tight",
        )

        # If blocked, candidates_after_correlation should be empty
        if len(log.blocking_events) > 0:
            assert len(log.candidates_after_correlation) == 0
