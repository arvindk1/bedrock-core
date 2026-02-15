"""
Options Scanner (Policy-Based Router)
=====================================
Smart options scanner with regime-based strategy selection.
Filters for professional-grade setups (DTE 35-50, Delta 30-50, Liquidity).
"""

import math
import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any

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
MIN_LIQUIDITY_OI = 500
MIN_LIQUIDITY_VOL = 100

class OptionsScanner:
    """
    Professional Options Scanner.
    Routes strategies based on volatility regime and filters for high-probability setups.
    """

    def __init__(self):
        self.vol_engine = VolEngine()
        self.market_data = MarketData()

    async def scan_opportunities(self, symbol: str, strategy_preference: Optional[str] = None) -> List[Dict]:
        """
        Scan for option opportunities based on market regime.

        Args:
            symbol: Stock ticker
            strategy_preference: Optional override (e.g. "IRON_CONDOR")

        Returns:
            List of trade dictionaries
        """
        # 1. Determine Regime
        vol_result = self.vol_engine.calculate_volatility(symbol, model=VolatilityModel.HYBRID)
        iv_rank = self.market_data.get_iv_rank(symbol) # approximation or from vol engine

        current_price = self.market_data.get_current_price(symbol)
        if not current_price:
            logger.error(f"Could not get price for {symbol}")
            return []

        # Simple Regime Logic
        # Low Vol (IV < 30% or Rank < 30) -> Debit Strategies (Long Vega)
        # High Vol (IV > 50% or Rank > 50) -> Credit Strategies (Short Vega)
        is_high_vol = vol_result.annual_volatility > 0.40
        is_low_vol = vol_result.annual_volatility < 0.25

        strategy_to_scan = strategy_preference
        if not strategy_to_scan:
            if is_high_vol:
                strategy_to_scan = "CREDIT_SPREAD" # or IRON_CONDOR if neutral
            elif is_low_vol:
                strategy_to_scan = "DEBIT_SPREAD" # or CALENDAR
            else:
                strategy_to_scan = "VERTICAL_SPREAD" # Default

        logger.info(f"🔎 Scanning {symbol}: Vol={vol_result.annual_volatility:.1%}, Strategy={strategy_to_scan}")

        # 2. Fetch Chains
        expiry = self._find_optimal_expiration(symbol)
        if not expiry:
            return []

        chain = self.market_data.get_option_chain(symbol, expiry)
        if chain is None:
            return []

        # 3. Find Candidates
        candidates = []

        if "SPREAD" in strategy_to_scan:
            candidates = self._find_vertical_spreads(symbol, current_price, chain, expiry, strategy_to_scan)
        elif "CONDOR" in strategy_to_scan:
            # Placeholder for Condor logic
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

    def _find_vertical_spreads(self, symbol: str, spot: float, chain: Any, expiry: str, strategy: str) -> List[Dict]:
        """Find vertical spreads matching delta criteria."""
        calls = chain.calls
        puts = chain.puts
        r = 0.04 # Risk free

        opportunities = []

        # Determine direction based on simple trend or assumption
        # (Scanner usually needs directional input, assume Bullish for Long Calls/Put Credit, Bearish for Puts)
        # For now, we return 'best' of both sides.

        # Bullish Spreads (Long Call Spread or Short Put Spread)
        # Target Short Deltas ~30, Long Deltas ~50+ for Debit
        # Target Short Deltas ~30, Long Deltas ~10 for Credit

        # Calculate Greeks for all first? Or just iterate.
        # Check liquidity first
        calls = calls[(calls["volume"] >= MIN_LIQUIDITY_VOL) & (calls["openInterest"] >= MIN_LIQUIDITY_OI)]
        puts = puts[(puts["volume"] >= MIN_LIQUIDITY_VOL) & (puts["openInterest"] >= MIN_LIQUIDITY_OI)]

        days_to = (datetime.strptime(expiry, "%Y-%m-%d").date() - datetime.now().date()).days
        T = days_to / 365.0

        # Scan Calls (Bullish)
        for _, long_leg in calls.iterrows():
            # Approx Delta check using simple moneyness if delta not in data
            # deep ITM = delta 1, ATM = 0.5.
            # We need greeks.
            iv = long_leg.get("impliedVolatility", 0)
            if iv == 0: continue

            greeks = self._calculate_greeks(spot, long_leg["strike"], T, r, iv, "call")
            delta = greeks["delta"]

            if 0.40 <= delta <= 0.60: # ATM/ITM for Debit Spread Anchor
                # Find Short Leg (OTM, lower delta)
                for _, short_leg in calls.iterrows():
                    if short_leg["strike"] > long_leg["strike"]:
                        iv_s = short_leg.get("impliedVolatility", 0)
                        greeks_s = self._calculate_greeks(spot, short_leg["strike"], T, r, iv_s, "call")

                        if 0.20 <= greeks_s["delta"] <= 0.35:
                            # Valid Debit Spread Candidate
                            width = short_leg["strike"] - long_leg["strike"]
                            details = {
                                "symbol": symbol,
                                "strategy": "BULL_CALL_DEBIT_SPREAD",
                                "expiration": expiry,
                                "legs": [
                                    {"side": "buy", "strike": long_leg["strike"], "type": "call", "delta": delta},
                                    {"side": "sell", "strike": short_leg["strike"], "type": "call", "delta": greeks_s["delta"]}
                                ],
                                "width": width,
                                "cost": long_leg["ask"] - short_leg["bid"], # Conservative
                                "max_profit": width - (long_leg["ask"] - short_leg["bid"]),
                                "description": f"Long {long_leg['strike']} / Short {short_leg['strike']} Call Spread"
                            }
                            # Basic filtering: Risk/Reward
                            if details["cost"] > 0 and details["max_profit"] / details["cost"] > 1.5:
                                opportunities.append(details)

        return opportunities

    def _calculate_greeks(self, S, K, T, r, sigma, option_type="call"):
        """Calculate Black-Scholes Greeks."""
        if T <= 0 or sigma <= 0 or S <= 0 or K <= 0:
            return {"delta": 0, "gamma": 0, "theta": 0, "vega": 0}

        sqrt_T = math.sqrt(T)
        d1 = (math.log(S / K) + (r + sigma**2 / 2) * T) / (sigma * sqrt_T)
        d2 = d1 - sigma * sqrt_T

        n_d1 = norm.pdf(d1)

        if option_type == "call":
            delta = norm.cdf(d1)
        else:
            delta = norm.cdf(d1) - 1

        return {"delta": delta}

# Global Instance
options_scanner = OptionsScanner()
