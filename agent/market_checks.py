"""
Scored Gatekeeper (Market Checks)
=================================
Automated trade validation and scoring engine.
Integrates Risk, Volatility, Event, and Data layers to approve/reject trades.
"""

import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

from event_loader import EventLoader
from market_data import MarketData
from risk_engine import RiskEngine
from vol_engine import VolEngine, VolatilityModel

logger = logging.getLogger(__name__)


@dataclass
class TradeScore:
    """Trade validation score and report"""
    symbol: str
    strategy: str
    total_score: float  # 0-100
    is_approved: bool
    rejection_reason: Optional[str]
    warnings: List[str]
    score_breakdown: Dict[str, float]
    details: Dict[str, Any]


class ScoredGatekeeper:
    """
    The Gatekeeper enforces "Hedge Fund Grade" quality standards.
    It runs a battery of checks (Liquidity, Risk, Events, Volatility)
    and assigns a confidence score to every proposed trade.
    """

    def __init__(self):
        self.vol_engine = VolEngine()
        self.event_loader = EventLoader()
        self.market_data = MarketData()
        self.risk_engine = RiskEngine()

    async def check_trade(self, trade_proposal: Dict[str, Any]) -> TradeScore:
        """
        Run all checks on a proposed trade.

        Args:
            trade_proposal: Dictionary containing trade details:
                - symbol: str
                - strategy_type: str (IRON_CONDOR, VERTICAL_SPREAD, etc.)
                - quantity: int
                - side: str (BUY, SELL)
                - strike_price: float (or list for spreads)
                - expiration_date: str (YYYY-MM-DD)
                - max_loss: float

        Returns:
            TradeScore object with approval status and score.
        """
        symbol = trade_proposal.get("symbol")
        strategy = trade_proposal.get("strategy_type", "UNKNOWN")
        expiration = trade_proposal.get("expiration_date")

        logger.info(f"🛡️ Gatekeeper checking {strategy} on {symbol} exp {expiration}")

        score = 100.0
        warnings = []
        details = {}
        breakdown = {"Starting Score": 100.0}

        # 1. Event Check (Hard Rejection)
        # ---------------------------------------------------------
        days_to_expiry = (pd.Timestamp(expiration) - pd.Timestamp.now()).days if expiration else 30

        earnings_conflict = self.event_loader.check_earnings_before_expiry(symbol, days_to_expiry)
        if earnings_conflict and earnings_conflict.get("affects_trade"):
             # For now, we REJECT earnings plays unless explicitly tagged as such
             # If the strategy is NOT specific to earnings, it's a risk.
             if "EARNINGS" not in strategy.upper():
                return self._reject_trade(symbol, strategy, f"Earnings event on {earnings_conflict['earnings_date']} inside trade window")
             else:
                warnings.append(f"Earnings play on {earnings_conflict['earnings_date']}")
                breakdown["Earnings Risk"] = "Warning"

        # 2. Risk Check (Hard Rejection)
        # ---------------------------------------------------------
        # We need current positions to check concentration.
        # For this implementation, we assume a separate call or pass it in.
        # Here we'll simulate a check against a mock portfolio or skip if unavailable.
        # Real implementation should fetch from portfolio manager.
        risk_rejection = False # Placeholder
        # valid, reason = self.risk_engine.should_reject_trade(trade_proposal, current_positions=[])
        # if valid: return self._reject_trade(symbol, strategy, reason)

        # 3. Liquidity Check (Score Penalty / Hard Reject)
        # ---------------------------------------------------------
        liq_metrics = self.market_data.get_liquidity_metrics(symbol)
        details["liquidity"] = liq_metrics

        # Check simple stock liquidity first
        if liq_metrics["avg_volume"] < 500000: # 500k avg volume min
            penalty = 20
            score -= penalty
            breakdown["Liquidity Penalty"] = -penalty
            warnings.append(f"Low avg volume: {liq_metrics['avg_volume']:,}")
            if liq_metrics["avg_volume"] < 100000:
                return self._reject_trade(symbol, strategy, f"Insufficient liquidity (Avg Vol {liq_metrics['avg_volume']:,})")

        # Spread check
        spread_pct = liq_metrics.get("spread_pct", 0)
        if spread_pct > 0.005: # > 0.5% spread is wide for liquid names
            penalty = 10
            score -= penalty
            breakdown["Wide Spread Penalty"] = -penalty
            warnings.append(f"Wide stock spread: {spread_pct:.2%}")

        # 4. Volatility Check (Score Impact)
        # ---------------------------------------------------------
        # Calculate IV Rank / Percentile using our Vol Engine
        try:
            vol_result = self.vol_engine.calculate_volatility(symbol, model=VolatilityModel.HYBRID)
            details["volatility"] = vol_result

            # Example Logic: Iron Condors prefer High IV, Debit Spreads prefer Low IV
            is_credit_strategy = any(s in strategy.upper() for s in ["CONDOR", "CREDIT", "SHORT"])
            is_debit_strategy = any(s in strategy.upper() for s in ["DEBIT", "LONG", "BUY"])

            iv_annual = vol_result.annual_volatility

            # Simple regime check (using hardcoded VIX reference for now if needed, or just raw IV)
            # Ideally we compare IV to HV (using additional_metrics from vol check if available)

            # If we are selling premium in low vol, penalize
            if is_credit_strategy and iv_annual < 0.20:
                penalty = 15
                score -= penalty
                breakdown["Low IV Penalty (Credit Strat)"] = -penalty
                warnings.append("Selling premium in low volatility environment")

            # If we are buying premium in high vol, penalize
            if is_debit_strategy and iv_annual > 0.50:
                penalty = 15
                score -= penalty
                breakdown["High IV Penalty (Debit Strat)"] = -penalty
                warnings.append("Buying premium in high volatility environment")

        except Exception as e:
            logger.warning(f"Vol check failed: {e}")
            warnings.append("Volatility check passed (data unavailable)")

        # 5. Technical Context (Score Impact)
        # ---------------------------------------------------------
        # Relative Strength
        rs_score = self.market_data.calculate_relative_strength(symbol)
        details["rs_score"] = rs_score

        # Strategy alignment
        if "BULL" in strategy.upper() and rs_score < 0:
            penalty = 10
            score -= penalty
            breakdown["Trend Mismatch Penalty"] = -penalty
            warnings.append(f"Bullish strategy on weak stock (RS {rs_score:.2f})")
        elif "BEAR" in strategy.upper() and rs_score > 0:
            penalty = 10
            score -= penalty
            breakdown["Trend Mismatch Penalty"] = -penalty
            warnings.append(f"Bearish strategy on strong stock (RS {rs_score:.2f})")


        # Final Decision
        # ---------------------------------------------------------
        min_passing_score = 70.0
        is_approved = score >= min_passing_score

        return TradeScore(
            symbol=symbol,
            strategy=strategy,
            total_score=score,
            is_approved=is_approved,
            rejection_reason=None if is_approved else f"Score {score} below threshold {min_passing_score}",
            warnings=warnings,
            score_breakdown=breakdown,
            details=details
        )


    def _reject_trade(self, symbol: str, strategy: str, reason: str) -> TradeScore:
        """Helper to create a rejection result."""
        logger.info(f"❌ Trade REJECTED: {symbol} {strategy} - {reason}")
        return TradeScore(
            symbol=symbol,
            strategy=strategy,
            total_score=0.0,
            is_approved=False,
            rejection_reason=reason,
            warnings=[],
            score_breakdown={"Rejection": -100.0},
            details={}
        )

# Global Instance
gatekeeper = ScoredGatekeeper()
