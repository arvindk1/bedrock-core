"""
Tests for vol_engine.py — VolEngine core structure & historical volatility.
"""

import sys
import os
from datetime import datetime
from unittest.mock import patch, MagicMock

import numpy as np
import pandas as pd
import pytest

# Bare import path (matches container layout)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "agent"))

from vol_engine import VolEngine, VolatilityResult, VolatilityModel, VolRegime


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_price_series(n=252, start=100, annual_vol=0.25):
    """Generate synthetic price series with known volatility."""
    np.random.seed(42)
    daily_vol = annual_vol / np.sqrt(252)
    daily_returns = np.random.normal(0, daily_vol, n)
    prices = [start]
    for r in daily_returns:
        prices.append(prices[-1] * np.exp(r))
    return np.array(prices)


def _mock_yf_history(prices):
    """Create a mock yfinance history DataFrame with business day index."""
    n = len(prices)
    dates = pd.bdate_range(start="2025-01-02", periods=n)
    df = pd.DataFrame({"Close": prices}, index=dates)
    return df


# ---------------------------------------------------------------------------
# TestVolEngineInit
# ---------------------------------------------------------------------------

class TestVolEngineInit:
    def test_default_construction(self):
        engine = VolEngine()
        assert engine.default_history_days == 252
        assert engine.ewma_lambda == 0.94

    def test_custom_params(self):
        engine = VolEngine(default_history_days=120, ewma_lambda=0.97)
        assert engine.default_history_days == 120
        assert engine.ewma_lambda == 0.97


# ---------------------------------------------------------------------------
# TestHistoricalVolatility
# ---------------------------------------------------------------------------

class TestHistoricalVolatility:
    @patch("vol_engine.yf.Ticker")
    def test_historical_vol_calculation(self, mock_ticker_cls):
        prices = _make_price_series(n=252, start=100, annual_vol=0.25)
        mock_ticker = MagicMock()
        mock_ticker.history.return_value = _mock_yf_history(prices)
        mock_ticker_cls.return_value = mock_ticker

        engine = VolEngine()
        result = engine.calculate_volatility("SPY", model=VolatilityModel.HISTORICAL)

        assert isinstance(result, VolatilityResult)
        assert result.model_used == VolatilityModel.HISTORICAL
        assert 0.15 <= result.annual_volatility <= 0.40
        assert result.data_points > 200

    @patch("vol_engine.yf.Ticker")
    def test_insufficient_data_raises(self, mock_ticker_cls):
        prices = _make_price_series(n=5, start=100, annual_vol=0.25)
        mock_ticker = MagicMock()
        mock_ticker.history.return_value = _mock_yf_history(prices)
        mock_ticker_cls.return_value = mock_ticker

        engine = VolEngine()
        with pytest.raises(ValueError, match="Insufficient"):
            engine.calculate_volatility("SPY", model=VolatilityModel.HISTORICAL)


# ---------------------------------------------------------------------------
# TestVolRegime
# ---------------------------------------------------------------------------

class TestVolRegime:
    def test_regime_enum_values(self):
        assert VolRegime.LOW.value == "low"
        assert VolRegime.MEDIUM.value == "medium"
        assert VolRegime.HIGH.value == "high"
