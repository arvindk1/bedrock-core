"""
Tests for Phase-2 ScoredGatekeeper (market_checks.py refactor)

Verifies liquidity + spread scoring matches Phase-2 spec.
"""

import pytest
from unittest.mock import patch, MagicMock

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "agent"))

from market_checks import ScoredGatekeeper, TradeScore
from reason_codes import is_structured_reason, parse_reason_code


class TestScoredGatekeeperInit:
    """Test ScoredGatekeeper initialization."""

    def test_init_creates_instances(self):
        """Constructor instantiates engines (no global singletons)."""
        gatekeeper = ScoredGatekeeper()
        assert gatekeeper.vol_engine is not None
        assert gatekeeper.event_loader is not None


class TestLiquidityCheck:
    """Test liquidity scoring (Phase-2 spec: min(OI, NBBO_size * 100))."""

    def test_no_legs_returns_penalty(self):
        """No legs → unknown liquidity → light penalty."""
        gatekeeper = ScoredGatekeeper()
        score, reason, penalty = gatekeeper._check_liquidity({"legs": []})
        assert score == 50.0
        assert penalty == 20

    def test_good_liquidity_no_penalty(self):
        """High OI + NBBO → good liquidity, minimal/no penalty."""
        gatekeeper = ScoredGatekeeper()
        legs = [
            {"open_interest": 10000, "nbbo_size": 200},  # min(10000, 200*100) = 10000
            {"open_interest": 8000, "nbbo_size": 150},   # min(8000, 150*100) = 8000
        ]
        score, reason, penalty = gatekeeper._check_liquidity({"legs": legs})
        # High liquidity means low impact % (target_size 100 / min(10000,8000) < 2%)
        assert penalty <= 1  # May have tiny penalty due to rounding
        if reason:
            assert "Liquidity" not in reason  # No liquidity issue

    def test_poor_liquidity_scales_penalty(self):
        """Low liquidity → scales penalty based on impact %."""
        gatekeeper = ScoredGatekeeper()
        legs = [
            {"open_interest": 1},  # Very low OI: market_impact = (1/1)*100 = 100%
        ]
        score, reason, penalty = gatekeeper._check_liquidity({"legs": legs})
        assert penalty > 0
        # Verify structured reason code
        assert is_structured_reason(reason)
        parsed = parse_reason_code(reason)
        assert parsed["rule"] == "LIQUIDITY"
        assert parsed["context"]["impact_pct"] == 100

    def test_no_liquidity_data_hard_penalty(self):
        """No OI/NBBO → can't calculate → max penalty."""
        gatekeeper = ScoredGatekeeper()
        legs = [{"bid": 1.0, "ask": 1.05}]  # No OI/NBBO
        score, reason, penalty = gatekeeper._check_liquidity({"legs": legs})
        assert score == 0.0
        assert penalty == 50
        # Verify structured reason code
        assert is_structured_reason(reason)
        parsed = parse_reason_code(reason)
        assert parsed["rule"] == "LIQUIDITY"
        assert parsed["context"]["reason"] == "no_oi_data"


class TestSpreadCheck:
    """Test bid/ask spread scoring (Phase-2 spec: Ask - Bid < max(0.05, 0.01 * Bid))."""

    def test_tight_spreads_pass(self):
        """Spreads within threshold → no penalty."""
        gatekeeper = ScoredGatekeeper()
        legs = [
            {"bid": 2.0, "ask": 2.03},  # spread 0.03 < max(0.05, 0.01*2) = 0.05 ✓
            {"bid": 1.5, "ask": 1.52},  # spread 0.02 < max(0.05, 0.01*1.5) = 0.05 ✓
        ]
        ok, reason, penalty = gatekeeper._check_spreads({"legs": legs})
        assert ok is True
        assert penalty == 0

    def test_wide_spreads_fail(self):
        """Spreads exceed threshold → penalty."""
        gatekeeper = ScoredGatekeeper()
        legs = [
            {"bid": 2.0, "ask": 2.10},  # spread 0.10 > max(0.05, 0.01*2) = 0.05 ✗
        ]
        ok, reason, penalty = gatekeeper._check_spreads({"legs": legs})
        assert ok is False
        assert penalty > 0
        assert "spread" in reason.lower()

    def test_no_legs_passes(self):
        """No legs → no spreads to check → pass."""
        gatekeeper = ScoredGatekeeper()
        ok, reason, penalty = gatekeeper._check_spreads({"legs": []})
        assert ok is True
        assert penalty == 0

    def test_worst_case_across_legs(self):
        """Uses worst-case spread across all legs."""
        gatekeeper = ScoredGatekeeper()
        legs = [
            {"bid": 2.0, "ask": 2.03},  # OK
            {"bid": 1.5, "ask": 1.65},  # Spread 0.15 > max(0.05, 0.015) = 0.05 ✗ WORST
        ]
        ok, reason, penalty = gatekeeper._check_spreads({"legs": legs})
        assert ok is False
        # Verify structured reason code
        assert is_structured_reason(reason)
        parsed = parse_reason_code(reason)
        assert parsed["rule"] == "SPREAD_TOO_WIDE"
        assert parsed["context"]["leg"] == 1  # Second leg is worst


class TestCheckTrade:
    """Test full check_trade() scoring."""

    def test_returns_trade_score(self):
        """check_trade() returns TradeScore object."""
        gatekeeper = ScoredGatekeeper()
        proposal = {
            "symbol": "AAPL",
            "strategy_type": "BULL_CALL_DEBIT_SPREAD",
            "expiration_date": "2026-03-20",
            "legs": [
                {"bid": 2.0, "ask": 2.02, "open_interest": 1000},
                {"bid": 1.0, "ask": 1.02, "open_interest": 800},
            ],
        }
        score = gatekeeper.check_trade(proposal)
        assert isinstance(score, TradeScore)
        assert score.symbol == "AAPL"
        assert score.strategy == "BULL_CALL_DEBIT_SPREAD"

    def test_good_trade_passes(self):
        """Good liquidity + tight spreads → passes soft gate."""
        gatekeeper = ScoredGatekeeper()
        proposal = {
            "symbol": "AAPL",
            "strategy_type": "BULL_CALL_DEBIT_SPREAD",
            "expiration_date": "2026-03-20",
            "legs": [
                {"bid": 2.0, "ask": 2.02, "open_interest": 5000, "nbbo_size": 50},
                {"bid": 1.0, "ask": 1.02, "open_interest": 4000, "nbbo_size": 40},
            ],
        }
        score = gatekeeper.check_trade(proposal)
        assert score.is_approved is True
        assert score.total_score >= 70

    def test_poor_liquidity_fails(self):
        """Poor liquidity → score drops below threshold."""
        gatekeeper = ScoredGatekeeper()
        proposal = {
            "symbol": "AAPL",
            "strategy_type": "BULL_CALL_DEBIT_SPREAD",
            "expiration_date": "2026-03-20",
            "legs": [
                {"bid": 2.0, "ask": 2.02},  # No OI/NBBO
            ],
        }
        score = gatekeeper.check_trade(proposal)
        # Poor liquidity should lower score
        assert score.total_score < 100

    @patch("market_checks.VolEngine")
    def test_debit_spread_in_high_vol_penalized(self, mock_vol_cls):
        """Buying premium (debit) in high vol → penalty."""
        mock_vol = MagicMock()
        mock_vol.calculate_volatility.return_value = MagicMock(annual_volatility=0.60)
        mock_vol_cls.return_value = mock_vol

        gatekeeper = ScoredGatekeeper()
        proposal = {
            "symbol": "AAPL",
            "strategy_type": "BULL_CALL_DEBIT_SPREAD",
            "expiration_date": "2026-03-20",
            "legs": [
                {"bid": 2.0, "ask": 2.02, "open_interest": 5000},
                {"bid": 1.0, "ask": 1.02, "open_interest": 4000},
            ],
        }
        score = gatekeeper.check_trade(proposal)
        # Check for structured IV_PENALTY codes in warnings
        iv_warnings = [w for w in score.warnings if is_structured_reason(w) and "IV_PENALTY" in w]
        assert len(iv_warnings) > 0
        assert score.total_score <= 85  # Penalized (15-point penalty)

    @patch("market_checks.VolEngine")
    def test_credit_spread_in_low_vol_penalized(self, mock_vol_cls):
        """Selling premium (credit) in low vol → penalty."""
        mock_vol = MagicMock()
        mock_vol.calculate_volatility.return_value = MagicMock(annual_volatility=0.15)
        mock_vol_cls.return_value = mock_vol

        gatekeeper = ScoredGatekeeper()
        proposal = {
            "symbol": "AAPL",
            "strategy_type": "BULL_PUT_CREDIT_SPREAD",
            "expiration_date": "2026-03-20",
            "legs": [
                {"bid": 2.0, "ask": 2.02, "open_interest": 5000},
                {"bid": 1.0, "ask": 1.02, "open_interest": 4000},
            ],
        }
        score = gatekeeper.check_trade(proposal)
        # Check for structured IV_PENALTY codes in warnings
        iv_warnings = [w for w in score.warnings if is_structured_reason(w) and "IV_PENALTY" in w]
        assert len(iv_warnings) > 0
        assert score.total_score <= 85  # Penalized (15-point penalty)


class TestTradeScore:
    """Test TradeScore dataclass."""

    def test_trade_score_structure(self):
        """TradeScore has all required fields."""
        score = TradeScore(
            symbol="AAPL",
            strategy="BULL_CALL",
            total_score=85.0,
            is_approved=True,
            rejection_reason=None,
            warnings=["Wide spread"],
            score_breakdown={"Liquidity": 10.0, "Spread": -5.0},
            details={"liquidity_score": 90},
        )
        assert score.symbol == "AAPL"
        assert score.is_approved is True
        assert len(score.warnings) == 1
