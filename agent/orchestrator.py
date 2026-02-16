"""
Orchestrator — Phase 2 Integration Engine
==========================================
Coordinates Vol, Events, Risk, and Correlation engines into a unified workflow.

This module:
1. Routes vol regime detection
2. Checks for blocking events
3. Generates scanner candidates
4. Applies risk gating
5. Applies correlation gating
6. Logs all decisions in DecisionLog artifact
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


# ============================================================================
# Decision Log Artifact
# ============================================================================

@dataclass
class DecisionLog:
    """
    Artifact capturing all decisions made during orchestration.

    Useful for:
    - Backtesting analysis
    - Understanding why a contract was rejected
    - Auditing the system behavior
    - Fine-tuning thresholds
    """

    symbol: str
    start_date: str
    end_date: str
    policy_mode: str = "tight"

    # Vol & Events Context
    regime: Optional[str] = None
    regime_details: Dict[str, Any] = field(default_factory=dict)
    blocking_events: List[Dict[str, Any]] = field(default_factory=list)
    strategy_hint: Optional[str] = None

    # Candidates
    candidates_raw: List[Dict[str, Any]] = field(default_factory=list)
    candidates_after_risk_gate: List[Dict[str, Any]] = field(default_factory=list)
    candidates_after_correlation: List[Dict[str, Any]] = field(default_factory=list)

    # Rejections
    rejections_risk: List[Tuple[Dict, str]] = field(default_factory=list)
    rejections_correlation: List[Tuple[Dict, str]] = field(default_factory=list)

    # Final picks
    final_picks: List[Dict[str, Any]] = field(default_factory=list)

    def to_formatted_string(self) -> str:
        """Convert decision log to human-readable output for agent."""
        output = f"\n{'='*80}\n"
        output += f"📊 DECISION LOG: {self.symbol}\n"
        output += f"{'='*80}\n"

        # Vol & Events
        output += f"\n🔍 CONTEXT:\n"
        output += f"  Regime: {self.regime or 'Unknown'}\n"
        output += f"  Strategy Hint: {self.strategy_hint or 'None'}\n"
        output += f"  Blocking Events: {len(self.blocking_events)}\n"

        if self.blocking_events:
            for event in self.blocking_events:
                output += f"    ⚠️  {event.get('description', event)}\n"

        # Candidates Flow
        output += f"\n📈 CANDIDATES:\n"
        output += f"  Generated: {len(self.candidates_raw)}\n"
        output += f"  After Risk Gate: {len(self.candidates_after_risk_gate)}\n"
        output += f"  After Correlation: {len(self.candidates_after_correlation)}\n"
        output += f"  Final Picks: {len(self.final_picks)}\n"

        # Rejections
        if self.rejections_risk:
            output += f"\n❌ RISK REJECTIONS ({len(self.rejections_risk)}):\n"
            for candidate, reason in self.rejections_risk[:5]:
                output += f"  - {candidate.get('strategy', '?')} @ {candidate.get('strike_long', '?')}: {reason}\n"

        if self.rejections_correlation:
            output += f"\n❌ CORRELATION REJECTIONS ({len(self.rejections_correlation)}):\n"
            for candidate, reason in self.rejections_correlation[:5]:
                output += f"  - {candidate.get('strategy', '?')}: {reason}\n"

        # Final picks
        if self.final_picks:
            output += f"\n✅ TOP PICKS:\n"
            for i, pick in enumerate(self.final_picks[:5], 1):
                output += f"  {i}. {pick.get('strategy', '?')} (Exp: {pick.get('expiration', '?')})\n"
                legs = pick.get('legs', [])
                if legs:
                    for j, leg in enumerate(legs):
                        side = leg.get('side', '?').upper()
                        strike = leg.get('strike', '?')
                        delta = leg.get('delta', 0)
                        output += f"     {side} ${strike:.2f} | Δ {delta:.2f}\n"
                output += f"     Cost: ${pick.get('cost', 0):.2f} | Max Profit: ${pick.get('max_profit', 0):.2f}\n\n"
        else:
            if self.blocking_events:
                output += f"\n⚠️  No opportunities: Blocking events prevent trading.\n"
            elif self.rejections_risk:
                output += f"\n⚠️  No opportunities: All candidates rejected by risk gate.\n"
            elif self.rejections_correlation:
                output += f"\n⚠️  No opportunities: All candidates rejected by correlation gate.\n"
            else:
                output += f"\n⚠️  No opportunities: No candidates generated in window.\n"

        output += f"\n{'='*80}\n"
        output += f"⚠️  Disclaimer: Informational only, not financial advice.\n"
        output += f"{'='*80}\n"

        return output


# ============================================================================
# Vol & Events Context
# ============================================================================

def vol_and_events_context(symbol: str, dte: int) -> Dict[str, Any]:
    """
    Determine vol regime and check for blocking events.

    Returns:
        {
            "regime": VolRegime enum,
            "vol_details": vol_result dict,
            "blocking_events": list of events,
            "strategy_hint": "DEBIT_SPREAD" | "CREDIT_SPREAD" | "VERTICAL_SPREAD"
        }
    """
    from vol_engine import VolEngine, VolRegime
    from event_loader import EventLoader

    try:
        vol_engine = VolEngine()
        event_loader = EventLoader()

        # Vol regime
        regime = vol_engine.detect_regime(symbol)
        vol_details = vol_engine.calculate_volatility(symbol)

        # Events
        blocking = event_loader.get_blocking_events(symbol, dte)

        # Strategy hint based on regime
        if regime == VolRegime.LOW:
            strategy_hint = "DEBIT_SPREAD"  # Buy premium cheap
        elif regime == VolRegime.HIGH:
            strategy_hint = "CREDIT_SPREAD"  # Sell premium expensive
        else:
            strategy_hint = "VERTICAL_SPREAD"  # Neutral

        logger.info(
            f"Vol/Events context for {symbol}: regime={regime.value}, "
            f"events={len(blocking)}, strategy={strategy_hint}"
        )

        return {
            "regime": regime,
            "vol_details": vol_details,
            "blocking_events": blocking,
            "strategy_hint": strategy_hint,
        }

    except Exception as e:
        logger.warning(f"Vol/events context failed for {symbol}: {e}")
        return {
            "regime": None,
            "vol_details": {},
            "blocking_events": [],
            "strategy_hint": "VERTICAL_SPREAD",
        }


# ============================================================================
# Main Orchestration
# ============================================================================

def policy_to_limit(mode: str) -> float:
    """Map policy mode to max risk per trade."""
    limits = {
        "tight": 1000.0,
        "moderate": 2000.0,
        "aggressive": 5000.0,
    }
    return limits.get(mode, 1000.0)


def full_scan_with_orchestration(
    symbol: str,
    start_date: str,
    end_date: str,
    top_n: int = 5,
    portfolio: Optional[List[Dict[str, Any]]] = None,
    policy_mode: str = "tight",
) -> DecisionLog:
    """
    Full Phase 2 orchestration: "Desk Flow" for options discovery.

    ORCHESTRATION PIPELINE:
    1. Events Check → Blocking events (earnings, macro) stop flow
    2. Vol Regime Detection → Strategy hint (debit/credit/vertical)
    3. Candidate Scan → Raw spreads with Phase-2 enrichment
    4. Risk Gate → Reject on concentration/drawdown
    5. ScoredGatekeeper → Soft scoring (liquidity + spreads + regime alignment)
    6. Correlation Gate → Filter by portfolio diversification
    7. Final Ranking → Sort by gatekeeper score + profit/cost ratio

    Args:
        symbol: Ticker
        start_date, end_date: Expiration window (YYYY-MM-DD)
        top_n: Return top N contracts
        portfolio: List of current positions for risk/correlation checks
        policy_mode: "tight" (1K), "moderate" (2K), or "aggressive" (5K) max risk per trade

    Returns:
        DecisionLog with: regime, blocking_events, candidates at each gate, final_picks, rejections
    """
    from options_scanner import generate_candidates
    from risk_engine import RiskEngine

    portfolio = portfolio or []
    log = DecisionLog(
        symbol=symbol,
        start_date=start_date,
        end_date=end_date,
        policy_mode=policy_mode,
    )

    try:
        # ====================================================================
        # TASK 2+3: Get Vol regime and check for blocking events
        # ====================================================================
        dte = 45  # Default to 45 DTE for context window
        context = vol_and_events_context(symbol, dte)

        log.regime = context["regime"].value if context["regime"] else None
        log.regime_details = context["vol_details"]
        log.blocking_events = context["blocking_events"]
        log.strategy_hint = context["strategy_hint"]

        # Hard block if earnings or macro event in window
        if log.blocking_events:
            logger.warning(f"Blocking events detected for {symbol}: {log.blocking_events}")
            # Don't generate candidates at all if there are blocking events
            log.candidates_raw = []
            log.final_picks = []
            return log

        # ====================================================================
        # BASE: Generate raw candidates (no gating)
        # ====================================================================
        from options_scanner import generate_candidates

        candidates = generate_candidates(symbol, start_date, end_date)
        log.candidates_raw = candidates

        if not candidates:
            logger.info(f"No candidates generated for {symbol}")
            return log

        # ====================================================================
        # TASK 1: Apply Risk Gate
        # ====================================================================
        from risk_engine import RiskEngine

        max_risk = policy_to_limit(policy_mode)
        risk_engine = RiskEngine(max_risk_per_trade=max_risk)

        accepted_after_risk = []
        for candidate in candidates:
            # Normalize candidate fields for risk gating
            trade_proposal = {
                "symbol": candidate.get("symbol", symbol),
                "strategy_type": candidate.get("strategy", "UNKNOWN"),
                "max_loss": candidate.get("max_loss", 0),  # Already × 100 (dollars)
                # Note: Don't pass sector—RiskEngine resolves via SECTOR_MAP[symbol]
            }

            rejected, reason = risk_engine.should_reject_trade(
                trade_proposal,
                portfolio,
                {},  # market_context (no drawdown check for now)
            )

            if rejected:
                log.rejections_risk.append((candidate, reason))
                logger.debug(f"Risk gate rejected {symbol}: {reason}")
            else:
                accepted_after_risk.append(candidate)

        log.candidates_after_risk_gate = accepted_after_risk

        if not accepted_after_risk:
            logger.info(f"No candidates passed risk gate for {symbol}")
            log.final_picks = []
            return log

        # ====================================================================
        # GATEKEEPER SCORING (Phase-2): Liquidity + Spreads + Regime
        # ====================================================================
        from market_checks import ScoredGatekeeper

        gatekeeper = ScoredGatekeeper()
        scored_candidates = []

        for candidate in accepted_after_risk:
            # Normalize candidate fields for gatekeeper
            trade_proposal = {
                "symbol": candidate.get("symbol", symbol),
                "strategy_type": candidate.get("strategy", "UNKNOWN"),
                "expiration_date": candidate.get("expiration", ""),
                "legs": candidate.get("legs", []),
            }

            score = gatekeeper.check_trade(trade_proposal)

            if score.is_approved:
                candidate["gatekeeper_score"] = score.total_score
                candidate["gatekeeper_warnings"] = score.warnings
                scored_candidates.append(candidate)
            else:
                logger.debug(f"Gatekeeper rejected {symbol}: {score.rejection_reason}")

        if not scored_candidates:
            logger.info(f"No candidates passed gatekeeper for {symbol}")
            log.final_picks = []
            return log

        # ====================================================================
        # TASK 4: Correlation Gate (Portfolio Diversification Check)
        # ====================================================================
        from correlation_gate import CorrelationGate

        corr_gate = CorrelationGate()
        after_correlation, corr_rejections = corr_gate.filter_candidates(
            scored_candidates, portfolio
        )

        log.candidates_after_correlation = after_correlation
        log.rejections_correlation = corr_rejections

        if not after_correlation:
            logger.info(f"No candidates passed correlation gate for {symbol}")
            log.final_picks = []
            return log

        # ====================================================================
        # Sort and return top N
        # ====================================================================
        # Sort by gatekeeper score (primary) + profit/cost ratio (secondary)
        final = sorted(
            after_correlation,
            key=lambda x: (
                -x.get("gatekeeper_score", 0),  # Higher score first (negate for descending)
                -(x.get("max_profit", 0) / x.get("cost", 1) if x.get("cost", 0) > 0 else 0),
            ),
        )

        log.final_picks = final[:top_n]
        logger.info(
            f"Orchestration complete: {len(log.final_picks)} picks for {symbol} "
            f"(risk: {len(accepted_after_risk)}, gatekeeper: {len(scored_candidates)}, "
            f"correlation: {len(after_correlation)})"
        )

        return log

    except Exception as e:
        logger.error(f"Orchestration failed for {symbol}: {e}", exc_info=True)
        # Return partial log to show what went wrong
        return log
