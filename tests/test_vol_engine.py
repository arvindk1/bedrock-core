"""
Tests for vol_engine.py — VolEngine core structure & historical volatility.
"""

import sys
import os
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


# ---------------------------------------------------------------------------
# TestGARCH
# ---------------------------------------------------------------------------


class TestGARCH:
    @patch("vol_engine.yf.Ticker")
    def test_garch_with_sufficient_data(self, mock_ticker_cls):
        prices = _make_price_series(n=500, start=100, annual_vol=0.30)
        mock_ticker = MagicMock()
        mock_ticker.history.return_value = _mock_yf_history(prices)
        mock_ticker_cls.return_value = mock_ticker

        engine = VolEngine()
        result = engine.calculate_volatility("SPY", model=VolatilityModel.GARCH)

        assert isinstance(result, VolatilityResult)
        assert result.model_used in (VolatilityModel.GARCH, VolatilityModel.HISTORICAL)
        assert result.annual_volatility > 0

    @patch("vol_engine.yf.Ticker")
    def test_garch_fallback_on_insufficient_data(self, mock_ticker_cls):
        # 10 prices → 9 returns, insufficient for both GARCH (100) and
        # historical fallback (20), so ValueError propagates.
        prices = _make_price_series(n=10, start=100, annual_vol=0.30)
        mock_ticker = MagicMock()
        mock_ticker.history.return_value = _mock_yf_history(prices)
        mock_ticker_cls.return_value = mock_ticker

        engine = VolEngine()
        with pytest.raises(ValueError, match="Insufficient"):
            engine.calculate_volatility("SPY", model=VolatilityModel.GARCH)


# ---------------------------------------------------------------------------
# TestEWMA
# ---------------------------------------------------------------------------


class TestEWMA:
    @patch("vol_engine.yf.Ticker")
    def test_ewma_calculation(self, mock_ticker_cls):
        prices = _make_price_series(n=100, start=100, annual_vol=0.20)
        mock_ticker = MagicMock()
        mock_ticker.history.return_value = _mock_yf_history(prices)
        mock_ticker_cls.return_value = mock_ticker

        engine = VolEngine()
        result = engine.calculate_volatility("SPY", model=VolatilityModel.EWMA)

        assert result.model_used == VolatilityModel.EWMA
        assert result.annual_volatility > 0
        assert "ewma_lambda" in result.additional_metrics


# ---------------------------------------------------------------------------
# TestHybrid
# ---------------------------------------------------------------------------


class TestHybrid:
    @patch("vol_engine.yf.Ticker")
    def test_hybrid_uses_multiple_models(self, mock_ticker_cls):
        prices = _make_price_series(n=500, start=100, annual_vol=0.25)
        mock_ticker = MagicMock()
        mock_ticker.history.return_value = _mock_yf_history(prices)
        mock_ticker_cls.return_value = mock_ticker

        engine = VolEngine()
        result = engine.calculate_volatility("SPY", model=VolatilityModel.HYBRID)

        assert result.model_used == VolatilityModel.HYBRID
        assert result.additional_metrics["model_count"] >= 2


# ---------------------------------------------------------------------------
# TestRegimeDetection
# ---------------------------------------------------------------------------


class TestRegimeDetection:
    @patch("vol_engine.yf.Ticker")
    def test_detect_regime_returns_valid_enum(self, mock_ticker_cls):
        prices = _make_price_series(n=300, start=100, annual_vol=0.25)
        mock_ticker = MagicMock()
        mock_ticker.history.return_value = _mock_yf_history(prices)
        mock_ticker_cls.return_value = mock_ticker

        engine = VolEngine()
        regime = engine.detect_regime("SPY")

        assert isinstance(regime, VolRegime)
        assert regime in (VolRegime.LOW, VolRegime.MEDIUM, VolRegime.HIGH)


# ---------------------------------------------------------------------------
# TestIVRank
# ---------------------------------------------------------------------------


class TestIVRank:
    @patch("vol_engine.yf.Ticker")
    def test_iv_rank_returns_0_to_100(self, mock_ticker_cls):
        prices = _make_price_series(n=300, start=100, annual_vol=0.25)
        mock_ticker = MagicMock()
        mock_ticker.history.return_value = _mock_yf_history(prices)
        mock_ticker_cls.return_value = mock_ticker

        engine = VolEngine()
        rank = engine.calculate_iv_rank("SPY")

        assert 0 <= rank <= 1.0

    @patch("vol_engine.yf.Ticker")
    def test_iv_rank_fallback_on_error(self, mock_ticker_cls):
        # n=30 → 31 prices → 30 returns (passes min_points=30), but only
        # 1 rolling window (< 2), so the method returns the 0.5 fallback.
        prices = _make_price_series(n=30, start=100, annual_vol=0.25)
        mock_ticker = MagicMock()
        mock_ticker.history.return_value = _mock_yf_history(prices)
        mock_ticker_cls.return_value = mock_ticker

        engine = VolEngine()
        rank = engine.calculate_iv_rank("SPY")

        assert rank == 0.5


# ---------------------------------------------------------------------------
# TestExpectedMove
# ---------------------------------------------------------------------------


class TestExpectedMove:
    @patch("vol_engine.yf.Ticker")
    def test_expected_move_structure(self, mock_ticker_cls):
        prices = _make_price_series(n=500, start=100, annual_vol=0.25)
        mock_ticker = MagicMock()
        mock_ticker.history.return_value = _mock_yf_history(prices)
        mock_ticker_cls.return_value = mock_ticker

        engine = VolEngine()
        result = engine.calculate_expected_move("SPY", current_price=200, days=45)

        assert "expected_move_dollars" in result
        assert result["upper_target"] > 200
        assert result["lower_target"] < 200
        assert result["confidence"] == 0.68

    @patch("vol_engine.yf.Ticker")
    def test_expected_move_higher_confidence_wider_range(self, mock_ticker_cls):
        prices = _make_price_series(n=500, start=100, annual_vol=0.25)
        mock_ticker = MagicMock()
        mock_ticker.history.return_value = _mock_yf_history(prices)
        mock_ticker_cls.return_value = mock_ticker

        engine = VolEngine()
        move_68 = engine.calculate_expected_move(
            "SPY", current_price=200, days=45, confidence=0.68
        )
        move_95 = engine.calculate_expected_move(
            "SPY", current_price=200, days=45, confidence=0.95
        )

        assert move_95["expected_move_dollars"] > move_68["expected_move_dollars"]
