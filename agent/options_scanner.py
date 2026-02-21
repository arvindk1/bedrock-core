"""
Options Scanner (Policy-Based Router)
=====================================
Smart options scanner with regime-based strategy selection.
Filters for professional-grade setups (DTE 35-50, Delta 30-50, Liquidity).
"""

import math
import logging
from datetime import datetime
from typing import Optional, Any

import pandas as pd
import yfinance as yf
from scipy.stats import norm

# Integration with our engines
from vol_engine import VolEngine, VolatilityModel
from market_data import MarketData

logger = logging.getLogger(__name__)

# Constants for "Smart" Filtering
MIN_DTE = 30
MAX_DTE = 60  # Sweet spot for theta/gamma balance
TARGET_DELTA_MIN = 0.25
TARGET_DELTA_MAX = 0.55
# Loosened liquidity constraints for testing/demo purposes
# (In production, these would be externalized to config and set higher)
MIN_LIQUIDITY_OI = 10
MIN_LIQUIDITY_VOL = 10


class OptionsScanner:
    """
    Professional Options Scanner.
    Routes strategies based on volatility regime and filters for high-probability setups.
    """

    def __init__(self):
        self.vol_engine = VolEngine()
        self.market_data = MarketData()

    def scan_opportunities(
        self, symbol: str, strategy_preference: Optional[str] = None
    ) -> list[dict]:
        """
        Scan for option opportunities based on market regime.

        Uses VolEngine.detect_regime() (short vs long vol + IV rank) to route strategies:
        - LOW: debit spreads (buy cheap premium)
        - HIGH: credit spreads (sell expensive premium)
        - MEDIUM: neutral spreads

        Args:
            symbol: Stock ticker
            strategy_preference: Optional override (e.g. "IRON_CONDOR")

        Returns:
            List of trade dictionaries
        """
        # 1. Determine Regime using Phase-2 detector (short vs long vol + IV rank)
        from vol_engine import VolRegime

        try:
            regime = self.vol_engine.detect_regime(symbol)
            vol_result = self.vol_engine.calculate_volatility(
                symbol, model=VolatilityModel.HYBRID
            )
        except Exception as e:
            logger.warning(
                f"Vol regime detection failed for {symbol}: {e}. Using neutral default."
            )
            regime = VolRegime.MEDIUM

            # Safe default: treat as medium vol if calculation fails
            class SafeVolResult:
                annual_volatility = 0.30

            vol_result = SafeVolResult()

        current_price = self.market_data.get_current_price(symbol)
        if not current_price:
            logger.error(f"Could not get price for {symbol}")
            return []

        # Route strategy based on detected regime
        strategy_to_scan = strategy_preference
        if not strategy_to_scan:
            if regime == VolRegime.HIGH:
                strategy_to_scan = "CREDIT_SPREAD"  # Sell expensive premium
            elif regime == VolRegime.LOW:
                strategy_to_scan = "DEBIT_SPREAD"  # Buy cheap premium
            else:
                strategy_to_scan = "VERTICAL_SPREAD"  # Neutral

        logger.info(
            f"🔎 Scanning {symbol}: Regime={regime.value}, Vol={vol_result.annual_volatility:.1%}, Strategy={strategy_to_scan}"
        )

        # 2. Fetch Chains
        expiry = self._find_optimal_expiration(symbol)
        if not expiry:
            return []

        chain = self.market_data.get_option_chain(symbol, expiry)
        if chain is None:
            return []

        # 3. Find Candidates
        # NOTE: Phase 2 MVP = Call Spreads Only (Debit & Credit)
        # TODO: Add put credit spreads, iron condors in Phase 2.5
        candidates = []

        if "SPREAD" in strategy_to_scan:
            # Phase-2: Generates call spreads (vertical spreads)
            # TODO: Route strategy_to_scan to appropriate generator (call vs put)
            candidates = self._find_vertical_spreads(
                symbol, current_price, chain, expiry, strategy_to_scan
            )
        elif "CONDOR" in strategy_to_scan:
            # Placeholder for Condor logic (Phase 2.5+)
            pass

        return candidates

    def _find_optimal_expiration(self, symbol: str) -> Optional[str]:
        """Find expiration date closest to 45 DTE."""
        try:
            ticker = yf.Ticker(symbol)
            expirations = ticker.options
            if not expirations:
                return None

            today = datetime.now().date()
            best_exp = None
            min_diff = 999

            for exp in expirations:
                exp_date = datetime.strptime(exp, "%Y-%m-%d").date()
                days_to = (exp_date - today).days

                if MIN_DTE <= days_to <= MAX_DTE:
                    # Prefer monthly usage if possible (logic to check 3rd friday could be added)
                    return exp

                # Fallback to closest within reason
                diff = abs(days_to - 45)
                if diff < min_diff and days_to > 20:
                    min_diff = diff
                    best_exp = exp

            return best_exp
        except Exception as e:
            logger.error(f"Error finding expiration for {symbol}: {e}")
            # Fallback to a mock date ~45 days out
            fallback = (datetime.now() + pd.Timedelta(days=45)).strftime("%Y-%m-%d")
            logger.warning(f"Using fallback expiration {fallback} for {symbol}")
            return fallback

    def _find_vertical_spreads(
        self, symbol: str, spot: float, chain: Any, expiry: str, strategy: str
    ) -> list[dict]:
        """Find vertical spreads matching delta criteria."""
        calls = chain.calls
        puts = chain.puts
        r = 0.04  # Risk free

        opportunities = []

        # Determine direction based on simple trend or assumption
        # (Scanner usually needs directional input, assume Bullish for Long Calls/Put Credit, Bearish for Puts)
        # For now, we return 'best' of both sides.

        # Bullish Spreads (Long Call Spread or Short Put Spread)
        # Target Short Deltas ~30, Long Deltas ~50+ for Debit
        # Target Short Deltas ~30, Long Deltas ~10 for Credit

        # Calculate Greeks for all first? Or just iterate.
        # Check liquidity first
        calls = calls[
            (calls["volume"] >= MIN_LIQUIDITY_VOL)
            & (calls["openInterest"] >= MIN_LIQUIDITY_OI)
        ]
        puts = puts[
            (puts["volume"] >= MIN_LIQUIDITY_VOL)
            & (puts["openInterest"] >= MIN_LIQUIDITY_OI)
        ]

        days_to = (
            datetime.strptime(expiry, "%Y-%m-%d").date() - datetime.now().date()
        ).days
        # T uses calendar days (365) for Black-Scholes option pricing
        # Note: Vol engine uses trading days (252) for annualized volatility—different conventions are correct
        T = days_to / 365.0

        # Scan Calls (Bullish)
        for _, long_leg in calls.iterrows():
            # Approx Delta check using simple moneyness if delta not in data
            # deep ITM = delta 1, ATM = 0.5.
            # We need greeks.
            iv = long_leg.get("impliedVolatility", 0)
            if iv == 0:
                continue

            greeks = self._calculate_greeks(spot, long_leg["strike"], T, r, iv, "call")
            delta = greeks["delta"]

            if 0.40 <= delta <= 0.60:  # ATM/ITM for Debit Spread Anchor
                # Find Short Leg (OTM, lower delta)
                for _, short_leg in calls.iterrows():
                    if short_leg["strike"] > long_leg["strike"]:
                        iv_s = short_leg.get("impliedVolatility", 0)
                        greeks_s = self._calculate_greeks(
                            spot, short_leg["strike"], T, r, iv_s, "call"
                        )

                        if 0.20 <= greeks_s["delta"] <= 0.35:
                            # Valid Debit Spread Candidate
                            width = short_leg["strike"] - long_leg["strike"]

                            # ============================================================
                            # PHASE 2: Enrich legs with option-level liquidity fields
                            # (Required by ScoredGatekeeper for bid/ask/OI scoring)
                            # ============================================================
                            long_leg_enriched = {
                                "side": "buy",
                                "strike": float(long_leg["strike"]),
                                "type": "call",
                                "delta": float(delta),
                                # Phase-2 fields (for gatekeeper liquidity/spread checks)
                                "bid": float(long_leg.get("bid", 0)),
                                "ask": float(long_leg.get("ask", 0)),
                                "open_interest": int(long_leg.get("openInterest", 0)),
                                "volume": int(long_leg.get("volume", 0)),
                                "last_price": float(long_leg.get("lastPrice", 0)),
                                "implied_volatility": float(
                                    long_leg.get("impliedVolatility", 0)
                                ),
                            }

                            short_leg_enriched = {
                                "side": "sell",
                                "strike": float(short_leg["strike"]),
                                "type": "call",
                                "delta": float(greeks_s["delta"]),
                                # Phase-2 fields
                                "bid": float(short_leg.get("bid", 0)),
                                "ask": float(short_leg.get("ask", 0)),
                                "open_interest": int(short_leg.get("openInterest", 0)),
                                "volume": int(short_leg.get("volume", 0)),
                                "last_price": float(short_leg.get("lastPrice", 0)),
                                "implied_volatility": float(
                                    short_leg.get("impliedVolatility", 0)
                                ),
                            }

                            # ============================================================
                            # SANITY CHECK: Drop candidates with garbage quotes (0/NaN bid/ask)
                            # yfinance can return 0 or NaN for illiquid options
                            # ============================================================
                            if (
                                long_leg_enriched["bid"] <= 0
                                or long_leg_enriched["ask"] <= 0
                                or short_leg_enriched["bid"] <= 0
                                or short_leg_enriched["ask"] <= 0
                            ):
                                logger.debug(
                                    f"Skipping {symbol} spread: garbage quotes (bid/ask = 0 or missing)"
                                )
                                continue

                            net_debit = (
                                long_leg["ask"] - short_leg["bid"]
                            )  # Conservative
                            details = {
                                "symbol": symbol,
                                "strategy": "BULL_CALL_DEBIT_SPREAD",
                                "expiration": expiry,
                                "legs": [long_leg_enriched, short_leg_enriched],
                                # Phase-2 Ready Fields
                                "width": width,
                                "spread_width": width,  # Explicit for clarity
                                "cost": net_debit,
                                "net_debit": net_debit,
                                "max_loss": net_debit
                                * 100,  # Contract multiplier (100 shares/contract)
                                "max_profit": width - net_debit,
                                "breakeven": long_leg["strike"]
                                + net_debit,  # For debit calls
                                "dte": days_to,
                                "description": f"Long {long_leg['strike']} / Short {short_leg['strike']} Call Spread",
                            }
                            # Basic filtering: Risk/Reward
                            if (
                                details["cost"] > 0
                                and details["max_profit"] / details["cost"] > 1.5
                            ):
                                opportunities.append(details)

        return opportunities

    def _calculate_greeks(self, S, K, T, r, sigma, option_type="call"):
        """Calculate Black-Scholes Greeks."""
        if T <= 0 or sigma <= 0 or S <= 0 or K <= 0:
            return {"delta": 0, "gamma": 0, "theta": 0, "vega": 0}

        sqrt_T = math.sqrt(T)
        d1 = (math.log(S / K) + (r + sigma**2 / 2) * T) / (sigma * sqrt_T)
        if option_type == "call":
            delta = norm.cdf(d1)
        else:
            delta = norm.cdf(d1) - 1

        return {"delta": delta}


# ============================================================================
# PHASE 2: generate_candidates (raw, no risk gating)
# ============================================================================


def generate_candidates(
    symbol: str,
    start_date: str,
    end_date: str,
) -> list[dict[str, Any]]:
    """
    Generate raw candidate spreads within expiration window (NO risk gating).

    Used by orchestrator for Phase 2 workflow.

    Args:
        symbol: Stock ticker
        start_date: Earliest expiration (YYYY-MM-DD)
        end_date: Latest expiration (YYYY-MM-DD)

    Returns:
        List of candidate dicts with fields:
        - symbol, strategy, expiration, dte
        - legs: [{"bid", "ask", "open_interest", "volume", "side", "strike", "delta", ...}]
        - cost, max_loss, max_profit, net_debit, breakeven
        - spread_width, width, description
    """
    try:
        start = datetime.strptime(start_date, "%Y-%m-%d").date()
        end = datetime.strptime(end_date, "%Y-%m-%d").date()

        if start > end:
            logger.error(f"Invalid date range: {start_date} > {end_date}")
            return []

        # Get current price
        ticker = yf.Ticker(symbol)
        current_data = ticker.history(period="1d")
        if current_data.empty:
            logger.error(f"No price data for {symbol}")
            return []

        current_price = float(current_data["Close"].iloc[-1])

        # Get expirations in window
        expirations = ticker.options or []
        valid_expirations = []
        for exp in expirations:
            try:
                exp_date = datetime.strptime(exp, "%Y-%m-%d").date()
                if start <= exp_date <= end:
                    valid_expirations.append(exp)
            except ValueError:
                continue

        if not valid_expirations:
            logger.warning(
                f"No expirations for {symbol} between {start_date} and {end_date}"
            )
            return []

        # Scan each expiration
        opportunities = []
        scanner = OptionsScanner()

        for expiry in valid_expirations:
            try:
                chain = scanner.market_data.get_option_chain(symbol, expiry)
                if chain is None:
                    continue

                dte = (
                    datetime.strptime(expiry, "%Y-%m-%d").date() - datetime.now().date()
                ).days
                spreads = scanner._find_vertical_spreads(
                    symbol, current_price, chain, expiry, "DEBIT_SPREAD"
                )

                for spread in spreads:
                    # Add computed fields for gating
                    spread["cost"] = spread.get("cost", 0)
                    spread["max_loss"] = spread["cost"]  # Debit spread max loss is cost
                    spread["strategy_type"] = spread.get("strategy", "UNKNOWN")
                    spread["dte"] = dte

                opportunities.extend(spreads)

            except Exception as e:
                logger.warning(f"Error scanning {symbol} {expiry}: {e}")
                continue

        logger.info(f"Generated {len(opportunities)} candidates for {symbol}")
        return opportunities

    except Exception as e:
        logger.error(f"generate_candidates failed for {symbol}: {e}")
        return []


# ============================================================================
# PHASE 1: find_cheapest_options (simple wrapper with risk gating)
# ============================================================================


def find_cheapest_options(
    symbol: str,
    start_date: str,
    end_date: str,
    top_n: int = 5,
    portfolio: Optional[list[dict[str, Any]]] = None,
    market_context: Optional[dict[str, Any]] = None,
) -> str:
    """
    Find and rank the best liquid options contracts within expiration window.

    Integrates risk gating: rejects trades that breach risk limits.

    Args:
        symbol: Stock ticker
        start_date: Earliest expiration (YYYY-MM-DD)
        end_date: Latest expiration (YYYY-MM-DD)
        top_n: Number of top results to return
        portfolio: Current portfolio positions for risk checks
        market_context: Market state (daily_pnl, portfolio_value, etc.)

    Returns:
        Formatted string with ranked contracts and risk summary
    """
    from risk_engine import RiskEngine

    try:
        # Initialize engines
        scanner = OptionsScanner()
        risk_engine = RiskEngine()

        # Parse expiration window
        start = datetime.strptime(start_date, "%Y-%m-%d").date()
        end = datetime.strptime(end_date, "%Y-%m-%d").date()

        if start > end:
            return f"Error: start_date {start_date} is after end_date {end_date}"

        # Get current price for context
        ticker = yf.Ticker(symbol)
        current_data = ticker.history(period="1d")
        if current_data.empty:
            return f"Error: No price data found for {symbol}"

        current_price = float(current_data["Close"].iloc[-1])

        # Scan for opportunities (use default strategy for now)
        opportunities = []

        # Get expiration dates within window
        expirations = ticker.options
        valid_expirations = []
        for exp in expirations:
            exp_date = datetime.strptime(exp, "%Y-%m-%d").date()
            if start <= exp_date <= end:
                valid_expirations.append(exp)

        if not valid_expirations:
            return (
                f"No expirations found for {symbol} between {start_date} and {end_date}"
            )

        # Scan each expiration
        for expiry in valid_expirations:
            chain = scanner.market_data.get_option_chain(symbol, expiry)
            if chain is None:
                continue

            dte = (
                datetime.strptime(expiry, "%Y-%m-%d").date() - datetime.now().date()
            ).days
            spreads = scanner._find_vertical_spreads(
                symbol, current_price, chain, expiry, "DEBIT_SPREAD"
            )

            for spread in spreads:
                # ✅ RISK GATE: Check if trade fits risk profile
                trade_candidate = {
                    "symbol": symbol,
                    "max_loss": spread["cost"],  # Debit spread max loss is the cost
                    "strategy_type": spread["strategy"],
                    "sector": symbol,  # Will be resolved by RiskEngine
                    "dte": dte,
                    "strike_long": spread["legs"][0]["strike"],
                    "strike_short": spread["legs"][1]["strike"],
                }

                rejected, reason = risk_engine.should_reject_trade(
                    trade_candidate, portfolio or [], market_context
                )

                if rejected:
                    logger.debug(
                        f"Trade rejected: {symbol} {spread['strategy']} @ {spread['legs'][0]['strike']} - {reason}"
                    )
                    spread["_rejected"] = reason
                else:
                    spread["_risk_pass"] = True

                opportunities.append(spread)

        # Filter to only accepted trades
        accepted = [op for op in opportunities if op.get("_risk_pass")]
        rejected = [op for op in opportunities if "_rejected" in op]

        if not accepted:
            msg = f"No opportunities passed risk checks for {symbol}\n"
            if rejected:
                msg += f"\n{len(rejected)} contracts rejected for risk:\n"
                for r in rejected[:3]:
                    msg += f"  - {r['strategy']} @ {r['legs'][0]['strike']}: {r['_rejected']}\n"
            return msg

        # Sort by profit/cost ratio
        accepted = sorted(
            accepted,
            key=lambda x: x["max_profit"] / x["cost"] if x["cost"] > 0 else 0,
            reverse=True,
        )

        # Format output
        output = f"\n{'=' * 80}\n"
        output += f"TOP {min(top_n, len(accepted))} OPPORTUNITIES FOR {symbol}\n"
        output += f"Current Price: ${current_price:.2f} | Risk Engine: ACTIVE\n"
        output += f"Passed Risk Checks: {len(accepted)} | Rejected: {len(rejected)}\n"
        output += f"{'=' * 80}\n\n"

        for i, opp in enumerate(accepted[:top_n], 1):
            output += f"{i}. {opp['strategy']} (Exp: {opp['expiration']})\n"
            output += f"   Long:  ${opp['legs'][0]['strike']:.2f} Call | Delta: {opp['legs'][0]['delta']:.2f}\n"
            output += f"   Short: ${opp['legs'][1]['strike']:.2f} Call | Delta: {opp['legs'][1]['delta']:.2f}\n"
            output += f"   Cost: ${opp['cost']:.2f} | Max Profit: ${opp['max_profit']:.2f} | R/R: {opp['max_profit'] / opp['cost']:.2f}x\n"
            output += f"   {opp['description']}\n\n"

        if rejected:
            output += f"\n📋 REJECTED ({len(rejected)} total):\n"
            for r in rejected[:5]:
                output += f"  ❌ {r['strategy']} @ {r['legs'][0]['strike']}: {r['_rejected']}\n"

        output += "\n⚠️  Disclaimer: Informational only, not financial advice.\n"
        return output

    except ValueError as e:
        return f"Error: {e}"
    except Exception as e:
        return f"Error scanning options for {symbol}: {type(e).__name__}: {e}"


# Global Instance (for backward compatibility if needed)
options_scanner = OptionsScanner()
