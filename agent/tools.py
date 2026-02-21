"""
Agent Tools — Phase 2 Integration
==================================
Three tool surface: simple scan, orchestrated scan, risk check.
"""

import json
import logging
from strands.tools import tool
from options_scanner import find_cheapest_options
from orchestrator import full_scan_with_orchestration
from risk_engine import RiskEngine

logger = logging.getLogger(__name__)


# ============================================================================
# TOOL 1: scan_options (SIMPLE — unchanged from Phase 1)
# ============================================================================


@tool
def scan_options(symbol: str, start_date: str, end_date: str, top_n: int = 5) -> str:
    """
    Find and rank the best liquid options contracts for a symbol within an expiration window.

    Uses Black-Scholes Greeks (delta, gamma, theta, vega) and ranks contracts by a
    bang-for-buck score (delta exposure per dollar of premium and theta decay).

    **Phase 1 behavior:** Simple wrapper, no risk gating, no orchestration.

    Args:
        symbol: Stock ticker (e.g., 'AAPL')
        start_date: Earliest expiration date to consider (YYYY-MM-DD)
        end_date: Latest expiration date to consider (YYYY-MM-DD)
        top_n: Number of top results to return (default 5)

    Returns:
        A formatted table of ranked contracts, or an error string.
    """
    try:
        return find_cheapest_options(symbol, start_date, end_date, top_n)
    except ValueError as e:
        return f"Error: {e}"
    except Exception:
        return f"Error scanning options for {symbol}"


# ============================================================================
# TOOL 2: scan_options_with_strategy (ORCHESTRATED — Phase 2)
# ============================================================================


@tool
def scan_options_with_strategy(
    symbol: str,
    start_date: str,
    end_date: str,
    top_n: int = 5,
    portfolio_json: str = "[]",
    policy_mode: str = "tight",
) -> str:
    """
    Full Phase 2 orchestration: Events → Vol → Risk → Correlation → Decision Log.

    Integrates all Phase 1 engines (Risk, Vol, Events) into a single desk-style workflow.
    Returns a DecisionLog artifact showing exactly why each contract was accepted or rejected.

    Args:
        symbol: Stock ticker (e.g., 'AAPL')
        start_date: Earliest expiration date (YYYY-MM-DD)
        end_date: Latest expiration date (YYYY-MM-DD)
        top_n: Number of top contracts to return (default 5)
        portfolio_json: JSON string of current portfolio positions (default: empty)
            Example: '[{"symbol": "MSFT", "max_loss": 500}, ...]'
        policy_mode: Risk policy ("tight"=$1000 max, "moderate"=$2000, "aggressive"=$5000)

    Returns:
        DecisionLog as formatted string with:
        - Vol regime detected
        - Blocking events (earnings, macro)
        - Raw candidates generated
        - Candidates accepted (passed risk & correlation)
        - Candidates rejected (with reasons)
        - Final top N picks
    """
    try:
        # Parse portfolio JSON
        portfolio = json.loads(portfolio_json) if portfolio_json.strip() else []

        # Run orchestration
        decision_log = full_scan_with_orchestration(
            symbol=symbol,
            start_date=start_date,
            end_date=end_date,
            top_n=top_n,
            portfolio=portfolio,
            policy_mode=policy_mode,
        )

        return decision_log.to_formatted_string()

    except json.JSONDecodeError as e:
        return f"Error: Invalid portfolio JSON: {e}"
    except ValueError as e:
        return f"Error: {e}"
    except Exception as e:
        logger.error(f"Orchestration failed for {symbol}: {e}", exc_info=True)
        return f"Error during orchestration: {type(e).__name__}: {e}"


# ============================================================================
# TOOL 3: check_trade_risk (RISK GATE ONLY)
# ============================================================================


@tool
def check_trade_risk(
    symbol: str,
    strategy: str,
    max_loss: float,
    portfolio_json: str = "[]",
) -> str:
    """
    Quick risk validation: Check if a proposed trade fits your risk policy.

    Use this before committing to a trade to verify it passes:
    - Per-trade max loss limit
    - Sector concentration cap
    - Drawdown circuit breaker

    Args:
        symbol: Stock ticker (e.g., 'AAPL')
        strategy: Strategy type (e.g., 'BULL_CALL_DEBIT_SPREAD', 'IRON_CONDOR')
        max_loss: Maximum loss if trade goes wrong (in $)
        portfolio_json: JSON string of current positions (default: empty)

    Returns:
        Approval status + detailed reasoning.
    """
    try:
        portfolio = json.loads(portfolio_json) if portfolio_json.strip() else []

        engine = RiskEngine()

        trade = {
            "symbol": symbol,
            "strategy_type": strategy,
            "max_loss": max_loss,  # In dollars (option premium × 100 shares/contract × quantity)
            # Note: RiskEngine resolves sector via SECTOR_MAP[symbol]; don't pass sector
        }

        rejected, reason = engine.should_reject_trade(trade, portfolio, {})

        if rejected:
            return f"❌ REJECTED: {reason}"
        else:
            return f"✅ APPROVED: Trade fits risk profile. Max loss: ${max_loss:.2f}"

    except json.JSONDecodeError as e:
        return f"Error: Invalid portfolio JSON: {e}"
    except Exception as e:
        logger.error(f"Risk check failed: {e}", exc_info=True)
        return f"Error during risk check: {type(e).__name__}: {e}"
