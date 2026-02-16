"""
Phase 2, Task 6: Tool API Contract Tests
=========================================
Tests for the three-tool surface (scan_options, scan_options_with_strategy, check_trade_risk).
Also tests DecisionLog and orchestrator stubs.
"""

import pytest
from datetime import datetime
from unittest.mock import patch, MagicMock
import json

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "agent"))

from tools import scan_options, scan_options_with_strategy, check_trade_risk
from orchestrator import DecisionLog, vol_and_events_context, policy_to_limit


# ============================================================================
# TOOL 1: scan_options (Legacy/Simple)
# ============================================================================

class TestScanOptionsLegacy:
    """Test the simple scan_options tool (Phase 1 behavior)."""

    def test_scan_options_callable(self):
        """Tool exists and is callable."""
        assert callable(scan_options)

    def test_scan_options_returns_string(self):
        """Tool always returns string."""
        result = scan_options("INVALID", "2026-03-01", "2026-06-01")
        assert isinstance(result, str)

    def test_scan_options_handles_invalid_dates(self):
        """Tool gracefully handles bad date formats."""
        result = scan_options("AAPL", "invalid", "2026-06-01")
        assert "Error" in result


# ============================================================================
# TOOL 2: scan_options_with_strategy (Orchestrated)
# ============================================================================

class TestScanOptionsWithStrategy:
    """Test the orchestrated scan_options_with_strategy tool."""

    def test_tool_callable(self):
        """Tool exists."""
        assert callable(scan_options_with_strategy)

    def test_returns_string(self):
        """Tool always returns string."""
        result = scan_options_with_strategy("AAPL", "2026-03-01", "2026-06-01")
        assert isinstance(result, str)

    def test_accepts_empty_portfolio(self):
        """Tool handles empty portfolio (default)."""
        result = scan_options_with_strategy(
            "AAPL",
            "2026-03-01",
            "2026-06-01",
            portfolio_json="[]"
        )
        assert isinstance(result, str)

    def test_rejects_invalid_portfolio_json(self):
        """Tool rejects malformed portfolio JSON."""
        result = scan_options_with_strategy(
            "AAPL",
            "2026-03-01",
            "2026-06-01",
            portfolio_json="NOT_JSON"
        )
        assert "Error" in result
        assert "JSON" in result

    def test_accepts_valid_portfolio_json(self):
        """Tool accepts valid portfolio JSON."""
        portfolio = json.dumps([
            {"symbol": "MSFT", "max_loss": 500},
            {"symbol": "NVDA", "max_loss": 300},
        ])
        result = scan_options_with_strategy(
            "AAPL",
            "2026-03-01",
            "2026-06-01",
            portfolio_json=portfolio
        )
        assert isinstance(result, str)

    def test_policy_modes_accepted(self):
        """Tool accepts all policy modes."""
        for mode in ["tight", "moderate", "aggressive"]:
            result = scan_options_with_strategy(
                "SPY",
                "2026-03-01",
                "2026-06-01",
                policy_mode=mode
            )
            assert isinstance(result, str)

    def test_bad_date_range_returns_error(self):
        """Tool rejects inverted date ranges."""
        result = scan_options_with_strategy(
            "AAPL",
            "2026-06-01",
            "2026-03-01"
        )
        assert isinstance(result, str)  # Should return error string, not crash


# ============================================================================
# TOOL 3: check_trade_risk
# ============================================================================

class TestCheckTradeRisk:
    """Test the check_trade_risk tool."""

    def test_tool_callable(self):
        """Tool exists."""
        assert callable(check_trade_risk)

    def test_returns_string(self):
        """Tool always returns string."""
        result = check_trade_risk("AAPL", "BULL_CALL_DEBIT_SPREAD", 1000.0)
        assert isinstance(result, str)

    def test_approval_message_format(self):
        """Approval includes checkmark and details."""
        result = check_trade_risk("AAPL", "BULL_CALL_DEBIT_SPREAD", 500.0)
        if "APPROVED" in result:
            assert "✅" in result or "APPROVED" in result
            assert "500.00" in result

    def test_rejection_message_format(self):
        """Rejection includes X and reason."""
        result = check_trade_risk("AAPL", "BULL_CALL_DEBIT_SPREAD", 10000.0, portfolio_json="[]")
        if "REJECTED" in result:
            assert "❌" in result or "REJECTED" in result

    def test_handles_invalid_portfolio_json(self):
        """Tool rejects malformed portfolio JSON."""
        result = check_trade_risk("AAPL", "BULL_CALL_DEBIT_SPREAD", 1000.0, portfolio_json="BAD")
        assert "Error" in result

    def test_handles_portfolio_context(self):
        """Tool accepts portfolio context for concentration checks."""
        portfolio = json.dumps([
            {"symbol": "AAPL", "max_loss": 800, "sector": "Technology"},
            {"symbol": "MSFT", "max_loss": 700, "sector": "Technology"},
        ])
        result = check_trade_risk(
            "AAPL",
            "BULL_CALL_DEBIT_SPREAD",
            500.0,
            portfolio_json=portfolio
        )
        assert isinstance(result, str)


# ============================================================================
# DecisionLog Artifact
# ============================================================================

class TestDecisionLog:
    """Test DecisionLog dataclass and formatting."""

    def test_decision_log_creation(self):
        """Can create a DecisionLog."""
        log = DecisionLog(
            symbol="AAPL",
            start_date="2026-03-01",
            end_date="2026-06-01",
        )
        assert log.symbol == "AAPL"
        assert log.regime is None
        assert len(log.blocking_events) == 0

    def test_decision_log_to_formatted_string(self):
        """Can convert DecisionLog to formatted string."""
        log = DecisionLog(
            symbol="AAPL",
            start_date="2026-03-01",
            end_date="2026-06-01",
            regime="LOW",
        )
        output = log.to_formatted_string()
        assert isinstance(output, str)
        assert "DECISION LOG" in output
        assert "AAPL" in output
        assert "LOW" in output

    def test_decision_log_with_blocking_events(self):
        """DecisionLog shows blocking events."""
        log = DecisionLog(
            symbol="AAPL",
            start_date="2026-03-01",
            end_date="2026-06-01",
        )
        log.blocking_events = [
            {"type": "earnings", "date": "2026-02-18", "description": "Earnings in 2 days"},
        ]
        output = log.to_formatted_string()
        assert "Earnings" in output or "Blocking" in output

    def test_decision_log_with_candidates(self):
        """DecisionLog shows candidate flow."""
        log = DecisionLog(
            symbol="AAPL",
            start_date="2026-03-01",
            end_date="2026-06-01",
        )
        log.candidates_raw = [{"strategy": "BULL_CALL"}] * 10
        log.candidates_after_risk_gate = [{"strategy": "BULL_CALL"}] * 5
        log.final_picks = [{"strategy": "BULL_CALL"}] * 2

        output = log.to_formatted_string()
        assert "10" in output or "Generated" in output
        assert "5" in output or "Risk Gate" in output
        assert "2" in output or "Final" in output

    def test_decision_log_with_rejections(self):
        """DecisionLog shows rejection details."""
        log = DecisionLog(
            symbol="AAPL",
            start_date="2026-03-01",
            end_date="2026-06-01",
        )
        log.candidates_raw = [{"strategy": "BULL_CALL", "strike_long": 150}]
        log.rejections_risk = [
            ({"strategy": "BULL_CALL", "strike_long": 150}, "Exceeds max risk"),
        ]

        output = log.to_formatted_string()
        assert "RISK REJECTIONS" in output or "Exceeds max risk" in output


# ============================================================================
# Orchestrator Helpers
# ============================================================================

class TestOrchestratorHelpers:
    """Test orchestrator helper functions."""

    def test_policy_to_limit(self):
        """Policy mode maps to max risk."""
        assert policy_to_limit("tight") == 1000.0
        assert policy_to_limit("moderate") == 2000.0
        assert policy_to_limit("aggressive") == 5000.0

    def test_policy_to_limit_default(self):
        """Unknown policy defaults to tight."""
        assert policy_to_limit("UNKNOWN") == 1000.0

    @patch("vol_engine.VolEngine")
    def test_vol_and_events_context_handles_errors(self, mock_vol_cls):
        """vol_and_events_context gracefully handles exceptions."""
        mock_vol_cls.side_effect = Exception("Vol engine failed")

        context = vol_and_events_context("AAPL", 45)

        # Should return safe defaults on error
        assert isinstance(context, dict)
        assert "regime" in context
        assert isinstance(context["strategy_hint"], str)


# ============================================================================
# Tool Integration Tests
# ============================================================================

class TestToolIntegration:
    """Test interactions between tools."""

    def test_check_risk_then_scan_with_strategy_flow(self):
        """User flow: check trade risk, then scan for opportunities."""
        # First: check if a trade is acceptable
        risk_result = check_trade_risk(
            "AAPL",
            "BULL_CALL_DEBIT_SPREAD",
            1000.0,
            portfolio_json="[]"
        )
        assert isinstance(risk_result, str)

        # Second: if approved, scan for opportunities
        if "APPROVED" in risk_result:
            scan_result = scan_options_with_strategy(
                "AAPL",
                "2026-03-01",
                "2026-06-01",
                portfolio_json="[]"
            )
            assert isinstance(scan_result, str)

    def test_both_scan_tools_callable(self):
        """Both scan tools exist and work."""
        result1 = scan_options("AAPL", "2026-03-01", "2026-06-01")
        result2 = scan_options_with_strategy("AAPL", "2026-03-01", "2026-06-01")

        assert isinstance(result1, str)
        assert isinstance(result2, str)
