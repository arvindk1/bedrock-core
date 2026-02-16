"""
Tests for Standardized Reason Codes Utility
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "agent"))

from reason_codes import (
    format_reason_code,
    parse_reason_code,
    is_structured_reason,
    validate_reason_code,
    extract_reason_summary,
    GATE_RISK,
    GATE_EVENT,
    GATE_GATEKEEP,
    GATE_CORRELATION,
    Rules,
)


class TestFormatReasonCode:
    """Test formatting reason codes"""

    def test_format_risk_reject_no_max_loss(self):
        code = format_reason_code(
            gate=GATE_RISK,
            rule=Rules.Risk.NO_MAX_LOSS,
            context={"symbol": "AAPL", "strategy": "BULL_CALL"},
        )
        assert code == "RISK_REJECT|rule=NO_MAX_LOSS|symbol=AAPL|strategy=BULL_CALL"

    def test_format_risk_reject_max_loss_exceeded(self):
        code = format_reason_code(
            gate=GATE_RISK,
            rule=Rules.Risk.MAX_LOSS_EXCEEDED,
            context={"symbol": "AAPL", "proposed": 1500, "limit": 1000, "excess_pct": 50},
        )
        assert "RISK_REJECT|rule=MAX_LOSS_EXCEEDED" in code
        assert "proposed=1500" in code
        assert "limit=1000" in code

    def test_format_with_no_context(self):
        code = format_reason_code(gate=GATE_RISK, rule=Rules.Risk.NO_MAX_LOSS)
        assert code == "RISK_REJECT|rule=NO_MAX_LOSS"

    def test_format_with_empty_context(self):
        code = format_reason_code(gate=GATE_RISK, rule=Rules.Risk.NO_MAX_LOSS, context={})
        assert code == "RISK_REJECT|rule=NO_MAX_LOSS"

    def test_format_with_boolean_values(self):
        code = format_reason_code(
            gate=GATE_RISK,
            rule=Rules.Risk.NO_MAX_LOSS,
            context={"halted": True, "active": False},
        )
        assert "halted=true" in code
        assert "active=false" in code

    def test_format_with_none_values(self):
        code = format_reason_code(
            gate=GATE_RISK,
            rule=Rules.Risk.NO_MAX_LOSS,
            context={"note": None},
        )
        assert "note=null" in code

    def test_format_correlation_reject(self):
        code = format_reason_code(
            gate=GATE_CORRELATION,
            rule=Rules.Correlation.CORRELATION_BREACH,
            context={"candidate": "AAPL", "vs": "MSFT", "corr": 0.78, "threshold": 0.70},
        )
        assert "CORR_REJECT|rule=CORRELATION_BREACH" in code
        assert "candidate=AAPL" in code
        assert "corr=0.78" in code


class TestParseReasonCode:
    """Test parsing reason codes"""

    def test_parse_simple_code(self):
        code = "RISK_REJECT|rule=NO_MAX_LOSS|symbol=AAPL"
        parsed = parse_reason_code(code)
        assert parsed["gate"] == "RISK_REJECT"
        assert parsed["rule"] == "NO_MAX_LOSS"
        assert parsed["context"]["symbol"] == "AAPL"

    def test_parse_with_multiple_context_fields(self):
        code = "RISK_REJECT|rule=MAX_LOSS_EXCEEDED|symbol=AAPL|proposed=1500|limit=1000"
        parsed = parse_reason_code(code)
        assert parsed["context"]["symbol"] == "AAPL"
        assert parsed["context"]["proposed"] == 1500
        assert parsed["context"]["limit"] == 1000

    def test_parse_with_float_values(self):
        code = "CORR_REJECT|rule=CORRELATION_BREACH|corr=0.78|threshold=0.70"
        parsed = parse_reason_code(code)
        assert abs(parsed["context"]["corr"] - 0.78) < 0.01
        assert abs(parsed["context"]["threshold"] - 0.70) < 0.01

    def test_parse_with_boolean_values(self):
        code = "RISK_REJECT|rule=NO_MAX_LOSS|halted=true|active=false"
        parsed = parse_reason_code(code)
        assert parsed["context"]["halted"] is True
        assert parsed["context"]["active"] is False

    def test_parse_with_null_values(self):
        code = "RISK_REJECT|rule=NO_MAX_LOSS|note=null"
        parsed = parse_reason_code(code)
        assert parsed["context"]["note"] is None

    def test_parse_empty_string(self):
        parsed = parse_reason_code("")
        assert parsed["gate"] == "UNKNOWN"
        assert parsed["rule"] == "UNKNOWN"
        assert parsed["context"] == {}

    def test_parse_invalid_format(self):
        parsed = parse_reason_code("not a valid code")
        assert parsed["gate"] == "UNKNOWN"
        assert parsed["rule"] == "UNKNOWN"

    def test_parse_roundtrip(self):
        """Format → Parse → Format should be identical"""
        original_context = {"symbol": "AAPL", "proposed": 1500, "limit": 1000}
        code = format_reason_code(GATE_RISK, Rules.Risk.MAX_LOSS_EXCEEDED, original_context)
        parsed = parse_reason_code(code)
        code2 = format_reason_code(GATE_RISK, Rules.Risk.MAX_LOSS_EXCEEDED, parsed["context"])
        assert code == code2


class TestIsStructuredReason:
    """Test detection of structured vs free-text reasons"""

    def test_structured_format_detected(self):
        assert is_structured_reason("RISK_REJECT|rule=MAX_LOSS_EXCEEDED|proposed=1500") is True

    def test_free_text_not_detected(self):
        assert is_structured_reason("Rejected: max loss exceeds limit") is False

    def test_empty_string_not_structured(self):
        assert is_structured_reason("") is False

    def test_none_not_structured(self):
        assert is_structured_reason(None) is False


class TestValidateReasonCode:
    """Test validation of reason codes"""

    def test_valid_code(self):
        code = format_reason_code(GATE_RISK, Rules.Risk.NO_MAX_LOSS)
        assert validate_reason_code(code) is True

    def test_invalid_gate_name(self):
        assert validate_reason_code("INVALID_GATE|rule=SOMETHING") is False

    def test_missing_rule(self):
        assert validate_reason_code("RISK_REJECT|something=value") is False

    def test_empty_string(self):
        assert validate_reason_code("") is False

    def test_none(self):
        assert validate_reason_code(None) is False


class TestExtractReasonSummary:
    """Test human-readable summary extraction"""

    def test_summary_max_loss_exceeded(self):
        code = format_reason_code(
            GATE_RISK,
            Rules.Risk.MAX_LOSS_EXCEEDED,
            {"proposed": 1500, "limit": 1000},
        )
        summary = extract_reason_summary(code)
        assert "1500" in summary
        assert "1000" in summary

    def test_summary_sector_cap(self):
        code = format_reason_code(
            GATE_RISK,
            Rules.Risk.SECTOR_CAP,
            {"sector": "TECHNOLOGY", "used_pct": 125},
        )
        summary = extract_reason_summary(code)
        assert "TECHNOLOGY" in summary
        assert "125" in summary

    def test_summary_drawdown_halt(self):
        code = format_reason_code(
            GATE_RISK,
            Rules.Risk.DRAWDOWN_HALT,
            {"loss_pct": 2.5, "limit": 2.0},
        )
        summary = extract_reason_summary(code)
        assert "2.5" in summary
        assert "2.0" in summary

    def test_summary_liquidity(self):
        code = format_reason_code(
            GATE_GATEKEEP,
            Rules.Gatekeep.LIQUIDITY,
            {"impact_pct": 3.2, "threshold": 2.0},
        )
        summary = extract_reason_summary(code)
        assert "3.2" in summary
        assert "2.0" in summary

    def test_summary_correlation_breach(self):
        code = format_reason_code(
            GATE_CORRELATION,
            Rules.Correlation.CORRELATION_BREACH,
            {"vs": "MSFT", "corr": 0.78, "threshold": 0.70},
        )
        summary = extract_reason_summary(code)
        assert "MSFT" in summary
        assert "0.78" in summary

    def test_summary_fallback_to_raw(self):
        """Free-text reason returns as-is"""
        raw = "Some free text reason"
        summary = extract_reason_summary(raw)
        assert summary == raw


class TestRuleConstants:
    """Test rule constant definitions"""

    def test_event_rules(self):
        assert Rules.Event.EARNINGS == "EARNINGS"
        assert Rules.Event.FOMC == "FOMC"
        assert Rules.Event.CPI == "CPI"
        assert Rules.Event.JOBS_REPORT == "JOBS_REPORT"

    def test_risk_rules(self):
        assert Rules.Risk.NO_MAX_LOSS == "NO_MAX_LOSS"
        assert Rules.Risk.MAX_LOSS_EXCEEDED == "MAX_LOSS_EXCEEDED"
        assert Rules.Risk.SECTOR_CAP == "SECTOR_CAP"
        assert Rules.Risk.DRAWDOWN_HALT == "DRAWDOWN_HALT"

    def test_gatekeep_rules(self):
        assert Rules.Gatekeep.LIQUIDITY == "LIQUIDITY"
        assert Rules.Gatekeep.SPREAD_TOO_WIDE == "SPREAD_TOO_WIDE"
        assert Rules.Gatekeep.IV_PENALTY == "IV_PENALTY"
        assert Rules.Gatekeep.LOW_SCORE == "LOW_SCORE"

    def test_correlation_rules(self):
        assert Rules.Correlation.CORRELATION_BREACH == "CORRELATION_BREACH"
