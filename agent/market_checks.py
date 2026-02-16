"""
Scored Gatekeeper (Market Checks) — Phase 2 Viability Scoring
==============================================================
Pre-filter for candidate spreads: liquidity + spreads + strategy alignment scoring.

NOTE: This is NOT a final risk gate. Use RiskEngine for hard rejections.
This module scores viability (soft gate) for presentation to orchestrator.

Architecture:
- EventLoader handles hard block on earnings/macro
- RiskEngine handles hard block on concentration/drawdown
- ScoredGatekeeper scores "how good is this option contract/spread?" (soft scoring)
"""

import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

from event_loader import EventLoader
from market_data import MarketData
from vol_engine import VolEngine, VolatilityModel
from reason_codes import Rules, format_reason_code, GATE_GATEKEEP

logger = logging.getLogger(__name__)


@dataclass
class TradeScore:
    """Trade viability score and report."""

    symbol: str
    strategy: str
    total_score: float  # 0-100
    is_approved: bool
    rejection_reason: Optional[str]
    reason_code: Optional[str] = None  # Structured reason code (GATEKEEP_REJECT|rule=...)
    warnings: List[str] = None
    score_breakdown: Dict[str, float] = None
    details: Dict[str, Any] = None

    def __post_init__(self):
        if self.warnings is None:
            self.warnings = []
        if self.score_breakdown is None:
            self.score_breakdown = {}
        if self.details is None:
            self.details = {}


class ScoredGatekeeper:
    """
    Soft pre-filter for option spreads: liquidity, spreads, regime alignment.

    This is NOT a hard risk gate. Use RiskEngine for concentration/drawdown.

    Responsibility:
    ✅ Liquidity: Can we execute this spread without excessive slippage?
    ✅ Spreads: Are bid/ask spreads tight enough?
    ✅ Regime: Is the strategy aligned with current vol regime?
    ❌ Risk: NOT our job — that's RiskEngine (hard gate in orchestrator)
    ❌ Earnings: NOT our job — that's EventLoader (hard gate in orchestrator)
    """

    def __init__(self):
        self.vol_engine = VolEngine()
        self.market_data = MarketData()
        self.event_loader = EventLoader()

    def check_trade(self, trade_proposal: Dict[str, Any]) -> TradeScore:
        """
        Score a proposed trade's viability (liquidity, spreads, regime alignment).

        Args:
            trade_proposal: Dict containing:
                - symbol: str
                - strategy_type: str (BULL_CALL_DEBIT_SPREAD, etc.)
                - expiration_date: str (YYYY-MM-DD)
                - legs: List[Dict] with side, strike, type, bid, ask, open_interest
                - (optional) max_loss: float

        Returns:
            TradeScore with soft approval (scoring-based, not hard rejection)
        """
        symbol = trade_proposal.get("symbol")
        strategy = trade_proposal.get("strategy_type", "UNKNOWN")
        expiration = trade_proposal.get("expiration_date")

        logger.info(f"🛡️ Gatekeeper scoring {strategy} on {symbol} exp {expiration}")

        score = 100.0
        warnings = []
        details = {}
        breakdown = {"Starting Score": 100.0}

        # ====================================================================
        # 1. Liquidity Check (Phase-2 Spec)
        # ====================================================================
        liq_score, liq_reason, liq_penalty = self._check_liquidity(trade_proposal)
        details["liquidity_score"] = liq_score
        details["liquidity_reason"] = liq_reason

        if liq_penalty > 0:
            score -= liq_penalty
            breakdown["Liquidity Penalty"] = -liq_penalty
            if liq_reason:
                warnings.append(liq_reason)

        # ====================================================================
        # 2. Spread Check (Phase-2 Spec)
        # ====================================================================
        spread_ok, spread_reason, spread_penalty = self._check_spreads(trade_proposal)

        if not spread_ok or spread_penalty > 0:
            score -= spread_penalty
            breakdown["Spread Penalty"] = -spread_penalty
            if spread_reason:
                warnings.append(spread_reason)

        # ====================================================================
        # 3. Volatility Regime Alignment (Soft Scoring)
        # ====================================================================
        try:
            vol_result = self.vol_engine.calculate_volatility(symbol, model=VolatilityModel.HYBRID)
            details["volatility"] = vol_result

            is_credit_strategy = any(s in strategy.upper() for s in ["CONDOR", "CREDIT", "SHORT"])
            is_debit_strategy = any(s in strategy.upper() for s in ["DEBIT", "LONG", "BUY"])

            iv_annual = vol_result.annual_volatility

            # If selling premium in low vol, penalize
            if is_credit_strategy and iv_annual < 0.20:
                penalty = 15
                score -= penalty
                breakdown["Low IV Penalty (Credit Strat)"] = -penalty
                iv_warning = format_reason_code(
                    gate=GATE_GATEKEEP,
                    rule=Rules.Gatekeep.IV_PENALTY,
                    context={
                        "symbol": symbol,
                        "strategy": strategy,
                        "condition": "low_vol_credit",
                        "iv": round(iv_annual, 3),
                        "threshold": 0.20,
                    },
                )
                warnings.append(iv_warning)

            # If buying premium in high vol, penalize
            if is_debit_strategy and iv_annual > 0.50:
                penalty = 15
                score -= penalty
                breakdown["High IV Penalty (Debit Strat)"] = -penalty
                iv_warning = format_reason_code(
                    gate=GATE_GATEKEEP,
                    rule=Rules.Gatekeep.IV_PENALTY,
                    context={
                        "symbol": symbol,
                        "strategy": strategy,
                        "condition": "high_vol_debit",
                        "iv": round(iv_annual, 3),
                        "threshold": 0.50,
                    },
                )
                warnings.append(iv_warning)

        except Exception as e:
            logger.warning(f"Vol check failed: {e}")
            warnings.append("Volatility check skipped (data unavailable)")

        # ====================================================================
        # Final Decision (Soft Approval Threshold)
        # ====================================================================
        min_passing_score = 70.0
        is_approved = score >= min_passing_score

        # Generate structured reason code on rejection
        reason_code = None
        if not is_approved:
            reason_code = format_reason_code(
                gate=GATE_GATEKEEP,
                rule=Rules.Gatekeep.LOW_SCORE,
                context={
                    "symbol": symbol,
                    "strategy": strategy,
                    "score": round(score, 1),
                    "threshold": min_passing_score,
                    "deficit": round(min_passing_score - score, 1),
                },
            )

        return TradeScore(
            symbol=symbol,
            strategy=strategy,
            total_score=score,
            is_approved=is_approved,
            rejection_reason=None
            if is_approved
            else f"Score {score:.0f} below threshold {min_passing_score}",
            reason_code=reason_code,
            warnings=warnings,
            score_breakdown=breakdown,
            details=details,
        )

    def _check_liquidity(self, trade_proposal: Dict[str, Any]) -> Tuple[float, Optional[str], float]:
        """
        Check liquidity using Phase-2 spec: min Open Interest as proxy capacity.

        NOTE: OI is a practical proxy for liquidity, not perfect. Ideal would be min(OI, 10*Volume)
        or NBBO depth, but yfinance doesn't reliably provide those. OI works for small traders.

        Liquidity capacity = min(OI) across all legs (in contracts)
        Target size = 1 spread (100 shares = 1 contract)
        Pass if market_impact < 2% of available liquidity

        Returns:
            (liquidity_score: 0-100, reason: str|None, penalty: 0-50)
        """
        legs = trade_proposal.get("legs", [])
        if not legs:
            reason = format_reason_code(
                gate=GATE_GATEKEEP,
                rule=Rules.Gatekeep.LIQUIDITY,
                context={
                    "symbol": trade_proposal.get("symbol", "?"),
                    "reason": "no_legs",
                    "impact_pct": 0,
                    "threshold": 2.0,
                },
            )
            return 50.0, reason, 20  # Unknown liquidity, light penalty

        # Compute liquidity capacity from OI (proxy): min OI across all legs
        min_oi = float("inf")
        has_oi = False

        for leg in legs:
            oi = leg.get("open_interest", 0)
            if oi > 0:
                min_oi = min(min_oi, oi)
                has_oi = True

        if not has_oi or min_oi == float("inf"):
            reason = format_reason_code(
                gate=GATE_GATEKEEP,
                rule=Rules.Gatekeep.LIQUIDITY,
                context={
                    "symbol": trade_proposal.get("symbol", "?"),
                    "reason": "no_oi_data",
                    "impact_pct": 100,
                    "threshold": 2.0,
                },
            )
            return 0.0, reason, 50  # Hard penalty

        # Liquidity capacity = min_oi (contracts directly)
        # Target size = 1 contract (100 shares)
        # Market impact = (target_size / capacity) * 100%
        target_size = 1  # 1 contract
        market_impact_pct = (target_size / min_oi) * 100

        # 2% threshold enforced
        if market_impact_pct > 2.0:
            penalty = min(30, int(market_impact_pct / 2))  # Escalate penalty
            reason = format_reason_code(
                gate=GATE_GATEKEEP,
                rule=Rules.Gatekeep.LIQUIDITY,
                context={
                    "symbol": trade_proposal.get("symbol", "?"),
                    "impact_pct": round(market_impact_pct, 1),
                    "threshold": 2.0,
                    "min_oi": int(min_oi),
                },
            )
            return (
                max(0, 100 - penalty),
                reason,
                penalty,
            )

        # Good liquidity: score based on min_oi (capacity in contracts)
        # 100+ contracts → score 100, 50 contracts → score 50, etc.
        score = min(100, int(min_oi / 100 * 100))  # Cap at 100
        return score, None, 0

    def _check_spreads(self, trade_proposal: Dict[str, Any]) -> Tuple[bool, Optional[str], float]:
        """
        Check bid/ask spreads using Phase-2 spec: Ask - Bid < max(0.05, 0.01 * Bid).

        For spreads, check all legs and use worst-case.

        Returns:
            (is_acceptable: bool, reason: str|None, penalty: 0-30)
        """
        legs = trade_proposal.get("legs", [])
        if not legs:
            return True, None, 0  # No legs = no spread check needed

        worst_spread_pct = 0.0
        worst_leg = None
        worst_bid = 0

        for i, leg in enumerate(legs):
            bid = leg.get("bid", 0)
            ask = leg.get("ask", 0)

            if bid <= 0 or ask <= 0:
                continue  # Skip if no bid/ask

            spread_dollars = ask - bid
            spread_threshold = max(0.05, 0.01 * bid)

            if spread_dollars > spread_threshold:
                spread_pct = spread_dollars / bid if bid > 0 else 0
                if spread_pct > worst_spread_pct:
                    worst_spread_pct = spread_pct
                    worst_leg = i
                    worst_bid = bid

        if worst_spread_pct == 0:
            return True, None, 0  # No spreads or all acceptable

        # Spread is too wide
        penalty = min(30, int(worst_spread_pct * 100))  # Scale penalty
        reason = format_reason_code(
            gate=GATE_GATEKEEP,
            rule=Rules.Gatekeep.SPREAD_TOO_WIDE,
            context={
                "symbol": trade_proposal.get("symbol", "?"),
                "leg": worst_leg,
                "spread_pct": round(worst_spread_pct * 100, 1),
                "bid": round(worst_bid, 2),
                "threshold": 1.0,  # default threshold in percentage
            },
        )
        return False, reason, penalty
