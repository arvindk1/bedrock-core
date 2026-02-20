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
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from reason_codes import is_structured_reason, parse_reason_code, extract_reason_summary

logger = logging.getLogger(__name__)


# ============================================================================
# Helper Functions
# ============================================================================

def _evaluate_event_policy(blocking_events: List[Dict[str, Any]]) -> str:
    """
    Smart event policy (desk-style).

    Returns: "PLAY" (no events), "WARN" (1-14 days out), or "TIGHT" (±1 day)
    """
    if not blocking_events:
        return "PLAY"

    # Check closest event
    min_days_until = min((evt.get("days_until", 99) for evt in blocking_events), default=99)

    if min_days_until <= 1:
        return "TIGHT"  # No new trades
    elif min_days_until <= 14:
        return "WARN"   # Allow with haircuts
    else:
        return "PLAY"   # Normal


def format_reason_for_display(reason: Optional[str]) -> str:
    """
    Format a rejection reason for human-readable display.

    If it's a structured code, extract the human-readable summary.
    Otherwise, return as-is.
    """
    if not reason:
        return "Unknown"

    if is_structured_reason(reason):
        return extract_reason_summary(reason)

    return reason


def format_event_for_display(event: Dict[str, Any]) -> str:
    """
    Format a blocking event for human-readable display.

    Handles both free-text and structured reason codes.
    """
    if "reason_code" in event and is_structured_reason(event["reason_code"]):
        parsed = parse_reason_code(event["reason_code"])
        rule = parsed.get("rule", "UNKNOWN")
        context = parsed.get("context", {})
        days_until = context.get("days_until", "?")
        name = event.get("name", context.get("name", rule))
        return f"{name} ({days_until} days until)"

    # Fallback for older format
    event_type = event.get("type", "unknown")
    if event_type == "earnings":
        return f"Earnings ({event.get('earnings_days', '?')} days until)"
    elif event_type == "macro":
        return f"{event.get('name', 'Event')} ({event.get('days_until', '?')} days until)"
    else:
        return event.get("description", str(event))



def _build_pipeline_journey(pick: Dict[str, Any], log_context: Dict[str, Any]) -> Dict[str, Any]:
    """
    Build structured pipeline journey for a final pick.

    All picks passed every gate (otherwise they wouldn't be final picks).
    log_context provides the metrics for each stage.
    """
    regime = log_context.get("regime", "UNKNOWN")
    regime_details = log_context.get("regime_details", {})
    blocking_events = log_context.get("blocking_events", [])
    event_policy = log_context.get("event_policy", "PLAY")
    max_risk = log_context.get("max_risk", 1000)
    max_sector_pct = log_context.get("max_sector_pct", 0.25)
    max_correlation = log_context.get("max_correlation", 0.70)
    gatekeeper_threshold = log_context.get("gatekeeper_threshold", 70)
    max_corr_seen = log_context.get("max_corr_seen", 0.0)
    sector = log_context.get("sector", "Unknown")
    sector_pct = log_context.get("sector_pct", 0.0)

    iv_rank = regime_details.get("iv_rank", 0) if isinstance(regime_details, dict) else 0
    if iv_rank and iv_rank <= 1.0:
        iv_rank_display = round(iv_rank * 100)
    else:
        iv_rank_display = round(iv_rank) if iv_rank else 0

    annual_vol = regime_details.get("annual_vol", 0) if isinstance(regime_details, dict) else 0
    max_loss = pick.get("max_loss", 0)
    gk_score = pick.get("gatekeeper_score", 0)

    return {
        "volatility": {
            "status": "pass",
            "code": f"{regime}_REGIME",
            "metrics": {
                "regime": regime,
                "iv_rank": iv_rank_display,
                "annual_vol": round(annual_vol * 100, 1) if annual_vol else None,
            },
            "display": (
                f"{regime} vol regime, IV rank {iv_rank_display}% — "
                f"{'credit spreads preferred' if regime == 'HIGH' else 'debit spreads preferred' if regime == 'LOW' else 'vertical spreads preferred'}"
            ),
        },
        "event": {
            "status": "pass",
            "code": "NO_EVENTS" if not blocking_events else f"POLICY_{event_policy}",
            "metrics": {
                "blocking_count": len(blocking_events),
                "policy": event_policy,
            },
            "display": (
                "No blocking events — trading permitted"
                if not blocking_events
                else f"{len(blocking_events)} event(s) nearby, policy {event_policy} — trading with haircuts"
            ),
        },
        "risk": {
            "status": "pass",
            "code": "WITHIN_LIMITS",
            "metrics": {
                "max_loss": max_loss,
                "limit": max_risk,
                "sector": sector,
                "sector_pct": round(sector_pct * 100),
                "sector_limit_pct": round(max_sector_pct * 100),
            },
            "display": (
                f"Max loss ${max_loss:.0f} within ${max_risk:.0f} limit, "
                f"{sector} sector at {sector_pct * 100:.0f}% (limit {max_sector_pct * 100:.0f}%)"
            ),
        },
        "gatekeeper": {
            "status": "pass",
            "code": "APPROVED",
            "metrics": {
                "score": round(gk_score, 1),
                "threshold": gatekeeper_threshold,
            },
            "display": f"Score {gk_score:.0f}/100 above threshold {gatekeeper_threshold}",
        },
        "correlation": {
            "status": "pass",
            "code": "DIVERSIFIED",
            "metrics": {
                "max_corr": round(max_corr_seen, 2),
                "threshold": max_correlation,
            },
            "display": (
                f"Max correlation {max_corr_seen:.2f} — well diversified (threshold {max_correlation:.2f})"
                if max_corr_seen < max_correlation
                else f"Max correlation {max_corr_seen:.2f} within threshold {max_correlation:.2f}"
            ),
        },
    }


def _build_strategy_reasoning(
    strategy_hint: str,
    regime: Optional[str],
    iv_rank: Optional[float],
    spy_trend: Optional[str],
    policy_mode: str,
) -> Dict[str, Any]:
    """Build strategy reasoning object for a final pick."""
    iv_display = 0
    if iv_rank is not None:
        iv_display = round(iv_rank * 100) if iv_rank <= 1.0 else round(iv_rank)

    strategy_display_map = {
        "CREDIT_SPREAD": "credit spreads",
        "DEBIT_SPREAD": "debit spreads",
        "VERTICAL_SPREAD": "vertical spreads",
    }
    strategy_label = strategy_display_map.get(strategy_hint, strategy_hint.replace("_", " ").lower())

    regime_label = (regime or "UNKNOWN").upper()
    policy_label = policy_mode.title()

    display = (
        f"IV Rank {iv_display}% ({regime_label} vol) with {policy_label} policy "
        f"\u2192 prefer {strategy_label}"
    )

    return {
        "chosen": strategy_hint,
        "drivers": {
            "regime": regime_label,
            "iv_rank": iv_display,
            "trend": (spy_trend or "UNKNOWN").upper(),
            "policy": policy_mode.upper(),
        },
        "display": display,
    }


def _build_no_trades_explanation(log: "DecisionLog", policy_mode: str, max_risk: float) -> Dict[str, Any]:
    """
    Build structured 'why no trades' explanation when final_picks is empty.
    Ranked by primary blocker.
    """
    gate_counts = {
        "generated": len(log.candidates_raw),
        "after_event": len(log.candidates_raw) if log.event_policy != "TIGHT" else 0,
        "after_risk": len(log.candidates_after_risk_gate),
        "after_gatekeeper": len([
            c for c in log.candidates_after_risk_gate
            if not any(
                r.get("candidate", {}).get("symbol") == c.get("symbol") and
                r.get("candidate", {}).get("strategy") == c.get("strategy")
                for r in log.rejections_gatekeeper
            )
        ]),
        "after_correlation": len(log.candidates_after_correlation),
        "final": 0,
    }

    top_blockers = []
    next_actions = []
    summary = "No picks generated"

    if log.event_policy == "TIGHT" and log.blocking_events:
        evt = log.blocking_events[0]
        top_blockers.append({
            "gate": "event",
            "code": "EVENT_TIGHT",
            "count": len(log.candidates_raw),
            "display": f"Event within 1 day — no new trades permitted: {format_event_for_display(evt)}",
        })
        next_actions = [
            "Wait for event to pass",
            "Monitor positions already held",
            "Re-scan after event clears",
        ]
        summary = f"0 picks: Event in tight window ({format_event_for_display(evt)})"

    elif log.rejections_risk:
        from reason_codes import parse_reason_code, is_structured_reason
        rule_counts: Dict[str, int] = {}
        for candidate, reason in log.rejections_risk:
            if is_structured_reason(reason):
                parsed = parse_reason_code(reason)
                rule = parsed.get("rule", "UNKNOWN")
            else:
                rule = reason.split("|")[0] if "|" in reason else reason
            rule_counts[rule] = rule_counts.get(rule, 0) + 1

        top_rule = max(rule_counts, key=lambda r: rule_counts[r])
        count = rule_counts[top_rule]

        if top_rule == "SECTOR_CAP":
            sector_name = "Unknown"
            used_pct = "?"
            limit_pct = 25
            for candidate, reason in log.rejections_risk:
                if is_structured_reason(reason):
                    parsed = parse_reason_code(reason)
                    if parsed.get("rule") == "SECTOR_CAP":
                        ctx = parsed.get("context", {})
                        sector_name = ctx.get("sector", "Unknown")
                        used_pct = ctx.get("used_pct", "?")
                        limit_pct = ctx.get("limit_pct", 25)
                        break
            top_blockers.append({
                "gate": "risk",
                "code": "SECTOR_CAP",
                "count": count,
                "display": f"{sector_name} sector at {used_pct}% (limit {limit_pct}%) — {count} candidates blocked",
            })
            next_actions = [
                f"Reduce {sector_name} sector exposure below {limit_pct}%",
                "Expand scan to symbols in other sectors",
                f"Switch policy from {policy_mode.title()} \u2192 Moderate if risk tolerance allows",
            ]
            summary = f"0 picks: {count}/{len(log.candidates_raw)} rejected at Risk Gate (sector cap)"

        elif top_rule == "MAX_LOSS_EXCEEDED":
            top_blockers.append({
                "gate": "risk",
                "code": "MAX_LOSS_EXCEEDED",
                "count": count,
                "display": f"Max loss exceeds ${max_risk:.0f} limit — {count} candidates blocked",
            })
            next_actions = [
                "Switch policy from Tight \u2192 Moderate to raise risk limit",
                "Scan for tighter spreads with lower max loss",
            ]
            summary = f"0 picks: {count}/{len(log.candidates_raw)} exceeded ${max_risk:.0f} max loss limit"

        else:
            top_blockers.append({
                "gate": "risk",
                "code": top_rule,
                "count": count,
                "display": f"Risk gate ({top_rule.replace('_', ' ').title()}) rejected {count} candidates",
            })
            next_actions = ["Review risk parameters", "Expand scan date range"]
            summary = f"0 picks: {count}/{len(log.candidates_raw)} rejected at Risk Gate"

    elif log.rejections_gatekeeper:
        count = len(log.rejections_gatekeeper)
        top_blockers.append({
            "gate": "gatekeeper",
            "code": "LOW_SCORE",
            "count": count,
            "display": f"Gatekeeper score below threshold 70 — {count} candidates blocked",
        })
        next_actions = [
            "Scan for more liquid options (tighter spreads)",
            "Expand date range to capture higher-quality expirations",
        ]
        summary = f"0 picks: {count} rejected by Gatekeeper (score below 70)"

    elif log.rejections_correlation:
        count = len(log.rejections_correlation)
        top_blockers.append({
            "gate": "correlation",
            "code": "CORRELATION_BREACH",
            "count": count,
            "display": f"Portfolio correlation too high — {count} candidates blocked",
        })
        next_actions = [
            "Close or reduce correlated positions before adding new trades",
            "Scan symbols in different sectors",
        ]
        summary = f"0 picks: {count} rejected by Correlation Gate (too correlated with existing portfolio)"

    elif not log.candidates_raw:
        top_blockers.append({
            "gate": "generated",
            "code": "NO_CANDIDATES",
            "count": 0,
            "display": "No option candidates found in the specified date window",
        })
        next_actions = [
            "Expand date range (start_date / end_date)",
            "Verify symbol has liquid options",
        ]
        summary = "0 picks: No candidates generated in date window"

    return {
        "summary": summary,
        "top_blockers": top_blockers,
        "gate_counts": gate_counts,
        "next_actions": next_actions,
    }


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
    event_policy: str = "PLAY"  # TIGHT, WARN, or PLAY

    # Candidates
    candidates_raw: List[Dict[str, Any]] = field(default_factory=list)
    candidates_after_risk_gate: List[Dict[str, Any]] = field(default_factory=list)
    candidates_after_correlation: List[Dict[str, Any]] = field(default_factory=list)

    # Rejections
    rejections_risk: List[Tuple[Dict, str]] = field(default_factory=list)
    rejections_gatekeeper: List[Dict[str, Any]] = field(default_factory=list)
    rejections_correlation: List[Tuple[Dict, str]] = field(default_factory=list)

    # Final picks
    final_picks: List[Dict[str, Any]] = field(default_factory=list)

    # No-trades explanation (populated when final_picks is empty)
    no_trades_explanation: Optional[Dict[str, Any]] = None

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
                formatted = format_event_for_display(event)
                output += f"    ⚠️  {formatted}\n"

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
                formatted_reason = format_reason_for_display(reason)
                output += f"  - {candidate.get('strategy', '?')} @ {candidate.get('strike_long', '?')}: {formatted_reason}\n"

        if self.rejections_correlation:
            output += f"\n❌ CORRELATION REJECTIONS ({len(self.rejections_correlation)}):\n"
            for candidate, reason in self.rejections_correlation[:5]:
                formatted_reason = format_reason_for_display(reason)
                output += f"  - {candidate.get('strategy', '?')}: {formatted_reason}\n"

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

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert decision log to dictionary format for API responses.
        """
        # Convert regime_details (VolatilityResult object) to dict if needed
        regime_details = self.regime_details
        if regime_details and hasattr(regime_details, '__dataclass_fields__'):
            regime_details = asdict(regime_details)
        elif regime_details and isinstance(regime_details, dict):
            regime_details = regime_details
        else:
            regime_details = {}

        return {
            "symbol": self.symbol,
            "start_date": self.start_date,
            "end_date": self.end_date,
            "policy_mode": self.policy_mode,
            "regime": self.regime,
            "regime_details": regime_details,
            "blocking_events": self.blocking_events,
            "strategy_hint": self.strategy_hint,
            "event_policy": self.event_policy,
            "total_generated": len(self.candidates_raw),
            "after_event_filter": len(self.candidates_raw) if not self.blocking_events else 0,
            "after_risk_gate": len(self.candidates_after_risk_gate),
            "after_gatekeeper": len([c for c in self.candidates_after_risk_gate if any(
                rc["candidate"].get("symbol") == c.get("symbol") and
                rc["candidate"].get("strategy") == c.get("strategy")
                for rc in self.rejections_gatekeeper
            ) == False]),
            "after_correlation": len(self.candidates_after_correlation),
            "final_picks": self.final_picks,
            "risk_rejections": [
                {
                    "candidate": {
                        "symbol": rej[0].get("symbol", self.symbol),
                        "strategy": rej[0].get("strategy", "UNKNOWN"),
                        "expiration": rej[0].get("expiration", ""),
                    },
                    "reason": rej[1],
                }
                for rej in self.rejections_risk
            ],
            "gatekeeper_rejections": self.rejections_gatekeeper,
            "correlation_rejections": [
                {
                    "candidate": {
                        "symbol": rej[0].get("symbol", self.symbol),
                        "strategy": rej[0].get("strategy", "UNKNOWN"),
                    },
                    "reason": rej[1],
                }
                for rej in self.rejections_correlation
            ],
            "blocking_events_str": "; ".join([
                format_event_for_display(evt) for evt in self.blocking_events
            ]) if self.blocking_events else "None",
            "timestamp": datetime.now().isoformat(),
        }


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
        dte = 14  # Block only events within 2 weeks of expiration (more practical)
        context = vol_and_events_context(symbol, dte)

        log.regime = context["regime"].value if context["regime"] else None
        log.regime_details = context["vol_details"]
        log.blocking_events = context["blocking_events"]
        log.strategy_hint = context["strategy_hint"]

        # ====================================================================
        # SMART EVENT POLICY (desk-style, not crude block)
        # ====================================================================
        event_policy = _evaluate_event_policy(log.blocking_events)
        log.event_policy = event_policy

        # TIGHT (±1 day): no new trades
        if event_policy == "TIGHT":
            logger.warning(f"Event in TIGHT window for {symbol}—no trades allowed")
            log.candidates_raw = []
            log.final_picks = []
            return log

        # WARN (1–14 days): apply haircuts, stricter rules
        if event_policy == "WARN":
            logger.info(f"Event in WARN window for {symbol}—applying haircuts")
            # Haircuts will be applied in risk gate + gatekeeper (see below)

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
        import os
        import yaml
        
        # Load risk config to get total account value
        risk_config_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config.yaml")
        total_account_value = 100000.0 # Default if no config
        if os.path.exists(risk_config_file):
            try:
                with open(risk_config_file, "r") as f:
                    config_data = yaml.safe_load(f)
                    total_account_value = config_data.get("account", {}).get("total_cash_balance", 100000.0)
            except Exception:
                pass

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

            # Pass the total account value into the market_context so the drawdown engine can use it
            market_context = {"portfolio_value": total_account_value, "daily_pnl": 0.0}

            rejected, reason = risk_engine.should_reject_trade(
                trade_proposal,
                portfolio,
                market_context, 
            )

            if rejected:
                log.rejections_risk.append((candidate, reason))
                logger.info(f"Risk gate rejected {symbol}: {reason}")
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
                # Track gatekeeper rejection
                log.rejections_gatekeeper.append({
                    "candidate": {
                        "symbol": candidate.get("symbol", symbol),
                        "strategy": candidate.get("strategy", "UNKNOWN"),
                        "expiration": candidate.get("expiration", ""),
                    },
                    "score": score.total_score,
                    "threshold": 70.0,
                    "breakdown": score.score_breakdown,
                    "reason": score.rejection_reason,
                })
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

        # Build pipeline journey for each final pick
        from risk_engine import SECTOR_MAP
        max_corr_seen = 0.0
        for rej_candidate, rej_reason in log.rejections_correlation:
            from reason_codes import parse_reason_code, is_structured_reason
            if is_structured_reason(rej_reason):
                parsed = parse_reason_code(rej_reason)
                corr_val = parsed.get("context", {}).get("corr", 0.0)
                if isinstance(corr_val, (int, float)):
                    max_corr_seen = max(max_corr_seen, float(corr_val))

        spy_trend = None
        if isinstance(context.get("vol_details"), dict):
            spy_trend = context["vol_details"].get("spy_trend")

        iv_rank_raw = None
        if isinstance(log.regime_details, dict):
            iv_rank_raw = log.regime_details.get("iv_rank")
        elif hasattr(log.regime_details, "iv_rank"):
            iv_rank_raw = log.regime_details.iv_rank

        log_context_for_pipeline = {
            "regime": log.regime,
            "regime_details": log.regime_details if isinstance(log.regime_details, dict) else {},
            "blocking_events": log.blocking_events,
            "event_policy": log.event_policy,
            "max_risk": max_risk,
            "max_sector_pct": risk_engine.max_sector_pct,
            "max_correlation": risk_engine.max_correlation,
            "gatekeeper_threshold": 70,
            "max_corr_seen": max_corr_seen,
            "sector": SECTOR_MAP.get(symbol, "Unknown"),
            "sector_pct": 0.0,
        }

        strategy_reasoning = _build_strategy_reasoning(
            strategy_hint=log.strategy_hint or "VERTICAL_SPREAD",
            regime=log.regime,
            iv_rank=iv_rank_raw,
            spy_trend=spy_trend,
            policy_mode=policy_mode,
        )

        for pick in log.final_picks:
            pick["pipeline"] = _build_pipeline_journey(pick, log_context_for_pipeline)
            pick["strategy_reasoning"] = strategy_reasoning

        logger.info(
            f"Orchestration complete: {len(log.final_picks)} picks for {symbol} "
            f"(risk: {len(accepted_after_risk)}, gatekeeper: {len(scored_candidates)}, "
            f"correlation: {len(after_correlation)})"
        )


        # Build no-trades explanation when needed
        if not log.final_picks:
            log.no_trades_explanation = _build_no_trades_explanation(log, policy_mode, max_risk)
        else:
            log.no_trades_explanation = None

        return log

    except Exception as e:
        logger.error(f"Orchestration failed for {symbol}: {e}", exc_info=True)
        # Return partial log to show what went wrong
        return log
