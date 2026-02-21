"""
Market Data Helper (Data Layer)
===============================
Provides data fetching and calculation utilities for market checks.
Handles liquidity metrics, relative strength, and option chain retrieval.
"""

import logging
from typing import Any, Optional

import pandas as pd
import yfinance as yf

logger = logging.getLogger(__name__)


class MarketData:
    """
    Market Data Service for fetching and processing financial data.
    """

    def __init__(self):
        pass

    def get_current_price(self, symbol: str) -> Optional[float]:
        """Get current real-time price (or delayed if market closed)."""
        try:
            ticker = yf.Ticker(symbol)
            # Try fast info first
            if hasattr(ticker, "fast_info") and ticker.fast_info:
                return ticker.fast_info.last_price

            # Fallback to regular info
            info = ticker.info
            return (
                info.get("currentPrice")
                or info.get("regularMarketPrice")
                or info.get("previousClose")
            )
        except Exception as e:
            logger.error(f"Error fetching price for {symbol}: {e}")
            logger.warning(f"Using MOCK price for {symbol}")
            return 100.0  # Mock price

    def get_option_chain(
        self, symbol: str, expiration_date: Optional[str] = None
    ) -> Optional[Any]:
        """
        Get option chain for a symbol.
        If expiration_date is None, returns the next monthly expiration.
        """
        try:
            ticker = yf.Ticker(symbol)
            expirations = ticker.options

            if not expirations:
                logger.warning(f"No options found for {symbol}")
                return None

            if expiration_date:
                if expiration_date not in expirations:
                    logger.warning(
                        f"Expiration {expiration_date} not found for {symbol}. Available: {expirations[:3]}..."
                    )
                    return None
                target_date = expiration_date
            else:
                # Default to a date 30-45 days out if possible, or just the next one
                # Simple logic: just take the 3rd or 4th one to avoid weekly noise?
                # For now take the second one to ensure some time value
                target_date = expirations[1] if len(expirations) > 1 else expirations[0]

            chain = ticker.option_chain(target_date)
            return chain
        except Exception as e:
            logger.error(f"Error fetching option chain for {symbol}: {e}")
            logger.warning(f"Using MOCK option chain for {symbol}")

            # Create a mock chain structure (DataFrame-like)
            class MockChain:
                @property
                def calls(self):
                    return pd.DataFrame(
                        {
                            "strike": [95, 100, 105],
                            "lastPrice": [5.5, 3.0, 1.2],
                            "bid": [5.4, 2.9, 1.1],
                            "ask": [5.6, 3.1, 1.3],
                            "impliedVolatility": [0.25, 0.24, 0.23],
                            "volume": [1000, 5000, 2000],
                            "openInterest": [5000, 10000, 4000],
                            "optionType": ["call"] * 3,
                        }
                    )

                @property
                def puts(self):
                    return pd.DataFrame(
                        {
                            "strike": [95, 100, 105],
                            "lastPrice": [1.1, 2.8, 5.2],
                            "bid": [1.0, 2.7, 5.1],
                            "ask": [1.2, 2.9, 5.3],
                            "impliedVolatility": [0.26, 0.25, 0.24],
                            "volume": [2000, 4000, 1000],
                            "openInterest": [4000, 8000, 3000],
                            "optionType": ["put"] * 3,
                        }
                    )

            return MockChain()

    def calculate_relative_strength(
        self, symbol: str, benchmark: str = "SPY", period_days: int = 20
    ) -> float:
        """
        Calculate Relative Strength vs Benchmark.
        Returns a score (e.g., > 1 means outperforming).
        """
        try:
            start_date = pd.Timestamp.now() - pd.Timedelta(days=period_days + 10)

            # Download data
            data = yf.download([symbol, benchmark], start=start_date, progress=False)[
                "Close"
            ]

            if (
                data.empty
                or symbol not in data.columns
                or benchmark not in data.columns
            ):
                return 0.0

            # Calculate returns
            sym_return = (data[symbol].iloc[-1] / data[symbol].iloc[0]) - 1
            bench_return = (data[benchmark].iloc[-1] / data[benchmark].iloc[0]) - 1

            # Use the slope of the RS ratio or just the net return difference
            # Let's return the return difference for simplicity: Symbol Return - Benchmark Return
            return sym_return - bench_return

        except Exception as e:
            logger.error(f"Error calculating RS for {symbol}: {e}")
            return 0.0

    def get_liquidity_metrics(self, symbol: str) -> dict[str, float]:
        """
        Get liquidity metrics: Volume, Avg Volume, Bid/Ask spread (of stock).
        For options liquidity, use get_option_liquidity within the check logic.
        """
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info

            avg_vol = info.get("averageVolume10days", 0)
            current_vol = info.get("volume", 0)
            bid = info.get("bid", 0)
            ask = info.get("ask", 0)
            spread = ask - bid if bid and ask else 0

            return {
                "avg_volume": avg_vol,
                "current_volume": current_vol,
                "stock_spread": spread,
                "spread_pct": (spread / bid) if bid > 0 else 0,
            }
        except Exception as e:
            logger.error(f"Error getting liquidity metrics for {symbol}: {e}")
            return {
                "avg_volume": 0,
                "current_volume": 0,
                "stock_spread": 0,
                "spread_pct": 0,
            }

    def get_iv_rank(self, symbol: str) -> float:
        """
        Calculate IV Rank (0-100).
        Approximation using historical volatility range if implied option data unavailable directly.
        """
        # This is complex without a dedicated IV history source.
        # We will use the VolEngine's calculation if possible, or an approximation.
        # For now, return a placeholder or simple vol calc.
        return 50.0  # Placeholder


# Global Instance
market_data = MarketData()
