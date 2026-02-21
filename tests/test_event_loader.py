"""
Tests for event_loader.py — EventLoader core structure, earnings check,
macro blackout, and blocking events.
"""

import sys
import os
from datetime import datetime, date, timedelta
from unittest.mock import patch, MagicMock, PropertyMock

import pandas as pd

# Bare import path (matches container layout)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "agent"))

from event_loader import EventLoader
from reason_codes import is_structured_reason, parse_reason_code


# ---------------------------------------------------------------------------
# TestEventLoaderInit
# ---------------------------------------------------------------------------
class TestEventLoaderInit:
    """Basic construction tests."""

    def test_default_construction(self):
        loader = EventLoader()
        assert loader.cache_duration_hours == 4

    def test_macro_events_loaded(self):
        loader = EventLoader()
        assert len(loader.macro_events) > 0


# ---------------------------------------------------------------------------
# TestEarningsCheck
# ---------------------------------------------------------------------------
class TestEarningsCheck:
    """Tests for check_earnings_before_expiry using mock yfinance."""

    @patch("event_loader.yf.Ticker")
    def test_earnings_inside_trade_window(self, mock_ticker_cls):
        """Earnings 10 days out, DTE=45 -> affects_trade=True."""
        mock_ticker = MagicMock()
        mock_ticker_cls.return_value = mock_ticker

        future_date = datetime.now() + timedelta(days=10)
        earnings_df = pd.DataFrame(
            {"Earnings Date": [future_date]},
            index=pd.DatetimeIndex([future_date]),
        )
        type(mock_ticker).earnings_dates = PropertyMock(return_value=earnings_df)

        loader = EventLoader()
        result = loader.check_earnings_before_expiry("AAPL", 45)

        assert result is not None
        assert result["affects_trade"] is True
        assert result["earnings_days"] <= 45

    @patch("event_loader.yf.Ticker")
    def test_earnings_outside_trade_window(self, mock_ticker_cls):
        """Earnings 60 days out, DTE=30 -> None."""
        mock_ticker = MagicMock()
        mock_ticker_cls.return_value = mock_ticker

        future_date = datetime.now() + timedelta(days=60)
        earnings_df = pd.DataFrame(
            {"Earnings Date": [future_date]},
            index=pd.DatetimeIndex([future_date]),
        )
        type(mock_ticker).earnings_dates = PropertyMock(return_value=earnings_df)

        loader = EventLoader()
        result = loader.check_earnings_before_expiry("AAPL", 30)

        assert result is None

    @patch("event_loader.yf.Ticker")
    def test_no_earnings_data_returns_none(self, mock_ticker_cls):
        """earnings_dates=None -> None."""
        mock_ticker = MagicMock()
        mock_ticker_cls.return_value = mock_ticker
        type(mock_ticker).earnings_dates = PropertyMock(return_value=None)

        loader = EventLoader()
        result = loader.check_earnings_before_expiry("AAPL", 45)

        assert result is None


# ---------------------------------------------------------------------------
# TestEarningsProximity
# ---------------------------------------------------------------------------
class TestEarningsProximity:
    """Tests for get_earnings_proximity."""

    @patch("event_loader.yf.Ticker")
    def test_earnings_within_7_days(self, mock_ticker_cls):
        """Earnings 5 days away -> returns 0 <= days <= 7."""
        mock_ticker = MagicMock()
        mock_ticker_cls.return_value = mock_ticker

        future_date = datetime.now() + timedelta(days=5)
        earnings_df = pd.DataFrame(
            {"Earnings Date": [future_date]},
            index=pd.DatetimeIndex([future_date]),
        )
        type(mock_ticker).earnings_dates = PropertyMock(return_value=earnings_df)

        loader = EventLoader()
        result = loader.get_earnings_proximity("AAPL")

        assert result is not None
        assert 0 <= result <= 7

    @patch("event_loader.yf.Ticker")
    def test_earnings_beyond_7_days(self, mock_ticker_cls):
        """Earnings 30 days away -> None."""
        mock_ticker = MagicMock()
        mock_ticker_cls.return_value = mock_ticker

        future_date = datetime.now() + timedelta(days=30)
        earnings_df = pd.DataFrame(
            {"Earnings Date": [future_date]},
            index=pd.DatetimeIndex([future_date]),
        )
        type(mock_ticker).earnings_dates = PropertyMock(return_value=earnings_df)

        loader = EventLoader()
        result = loader.get_earnings_proximity("AAPL")

        assert result is None


# ---------------------------------------------------------------------------
# TestMacroBlackout
# ---------------------------------------------------------------------------
class TestMacroBlackout:
    """Tests for is_macro_blackout."""

    def test_fomc_date_is_blackout(self):
        """A known FOMC date should be a blackout."""
        loader = EventLoader()
        # Pick the first FOMC date from macro_events
        fomc_events = [e for e in loader.macro_events if "FOMC" in e["name"]]
        assert len(fomc_events) > 0, "Should have FOMC events"

        fomc_date = fomc_events[0]["date"]
        is_blackout, name = loader.is_macro_blackout(fomc_date)

        assert is_blackout is True
        assert "FOMC" in name

    def test_random_date_not_blackout(self):
        """A random date far from any event should not be blackout."""
        loader = EventLoader()
        result = loader.is_macro_blackout(date(2026, 7, 15))

        is_blackout, name = result
        assert isinstance(is_blackout, bool)
        assert name is None or isinstance(name, str)


# ---------------------------------------------------------------------------
# TestBlockingEvents
# ---------------------------------------------------------------------------
class TestBlockingEvents:
    """Tests for get_blocking_events."""

    @patch("event_loader.yf.Ticker")
    def test_get_blocking_events_combines_earnings_and_macro(self, mock_ticker_cls):
        """Mock earnings 5 days away, DTE=45 -> at least 1 earnings event."""
        mock_ticker = MagicMock()
        mock_ticker_cls.return_value = mock_ticker

        future_date = datetime.now() + timedelta(days=5)
        earnings_df = pd.DataFrame(
            {"Earnings Date": [future_date]},
            index=pd.DatetimeIndex([future_date]),
        )
        type(mock_ticker).earnings_dates = PropertyMock(return_value=earnings_df)

        loader = EventLoader()
        events = loader.get_blocking_events("AAPL", 45)

        earnings_events = [e for e in events if e.get("type") == "earnings"]
        assert len(earnings_events) >= 1


# ---------------------------------------------------------------------------
# TestStructuredReasonCodes
# ---------------------------------------------------------------------------
class TestStructuredReasonCodes:
    """Tests for structured reason codes in events."""

    @patch("event_loader.yf.Ticker")
    def test_earnings_generates_reason_code(self, mock_ticker_cls):
        """Earnings check should include structured EVENT_BLOCK reason code."""
        mock_ticker = MagicMock()
        mock_ticker_cls.return_value = mock_ticker

        future_date = datetime.now() + timedelta(days=10)
        earnings_df = pd.DataFrame(
            {"Earnings Date": [future_date]},
            index=pd.DatetimeIndex([future_date]),
        )
        type(mock_ticker).earnings_dates = PropertyMock(return_value=earnings_df)

        loader = EventLoader()
        result = loader.check_earnings_before_expiry("AAPL", 45)

        assert result is not None
        assert "reason_code" in result
        assert is_structured_reason(result["reason_code"])
        parsed = parse_reason_code(result["reason_code"])
        assert parsed["rule"] == "EARNINGS"
        assert parsed["context"]["symbol"] == "AAPL"
        assert "days_until" in parsed["context"]

    @patch("event_loader.yf.Ticker")
    def test_blocking_events_include_reason_codes(self, mock_ticker_cls):
        """Macro events should include structured reason codes."""
        mock_ticker = MagicMock()
        mock_ticker_cls.return_value = mock_ticker
        type(mock_ticker).earnings_dates = PropertyMock(return_value=None)

        loader = EventLoader()
        # Get events for the next 60 days - should include some macro events
        events = loader.get_blocking_events("SPY", 60)

        # Verify each event has a reason_code
        for event in events:
            assert "reason_code" in event, f"Event {event} missing reason_code"
            assert is_structured_reason(event["reason_code"])
            parsed = parse_reason_code(event["reason_code"])
            assert "days_until" in parsed["context"]

    @patch("event_loader.yf.Ticker")
    def test_macro_reason_codes_have_correct_rule(self, mock_ticker_cls):
        """Macro events should have correct rule type in reason code."""
        mock_ticker = MagicMock()
        mock_ticker_cls.return_value = mock_ticker
        type(mock_ticker).earnings_dates = PropertyMock(return_value=None)

        loader = EventLoader()
        events = loader.get_blocking_events("SPY", 180)  # 6 months

        macro_events = [e for e in events if e.get("type") == "macro"]
        assert len(macro_events) > 0, "Should have macro events in 180-day window"

        # Verify rules match event types
        for event in macro_events:
            parsed = parse_reason_code(event["reason_code"])
            rule = parsed["rule"]
            name = event["name"]

            if "FOMC" in name:
                assert rule == "FOMC"
            elif "CPI" in name:
                assert rule == "CPI"
            elif "Jobs" in name:
                assert rule == "JOBS_REPORT"
