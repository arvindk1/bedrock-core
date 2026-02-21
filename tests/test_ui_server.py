"""Tests for the UI server /api/scan endpoint."""
import json
from unittest.mock import patch, MagicMock

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    from ui.server import app
    return TestClient(app)


class TestScanEndpoint:
    """Tests for POST /api/scan."""

    def test_scan_success(self, client):
        """Test successful scan returns decision log structure."""
        resp = client.post("/api/scan", json={
            "symbol": "AAPL",
            "start_date": "2026-03-01",
            "end_date": "2026-04-01",
            "top_n": 5,
        })
        assert resp.status_code == 200
        data = resp.json()
        # Check dashboard response structure
        assert "regime" in data
        assert "spyTrend" in data
        assert "macroRisk" in data
        assert "policyMode" in data
        assert "gateFunnel" in data
        assert "picks" in data
        assert "rejections" in data
        assert "decisionLog" in data

    def test_scan_returns_gate_funnel(self, client):
        """Test that scan returns proper gate funnel data."""
        resp = client.post("/api/scan", json={
            "symbol": "NVDA",
            "start_date": "2026-03-01",
            "end_date": "2026-06-01",
            "top_n": 5,
        })
        assert resp.status_code == 200
        data = resp.json()
        funnel = data["gateFunnel"]
        assert "generated" in funnel
        assert "afterRisk" in funnel
        assert "afterGatekeeper" in funnel
        assert "afterCorrelation" in funnel
        assert "final" in funnel


class TestConfigEndpoint:
    """Tests for GET /api/config."""

    def test_config_endpoint_returns_account_balance(self, client):
        """GET /api/config -> 200, account.total_cash_balance present and > 0."""
        resp = client.get("/api/config")
        assert resp.status_code == 200
        data = resp.json()
        assert "account" in data
        assert "total_cash_balance" in data["account"]
        assert data["account"]["total_cash_balance"] > 0

    def test_config_endpoint_returns_policy_limits(self, client):
        """GET /api/config -> policy_limits keys are present and positive numbers."""
        resp = client.get("/api/config")
        assert resp.status_code == 200
        data = resp.json()
        assert "policy_limits" in data
        assert "tight" in data["policy_limits"]
        assert "moderate" in data["policy_limits"]
        assert "aggressive" in data["policy_limits"]
        assert isinstance(data["policy_limits"]["tight"], (int, float))
        assert data["policy_limits"]["tight"] > 0


class TestStaticFiles:
    """Tests for static file serving."""

    def test_index_page_loads(self, client):
        resp = client.get("/")
        assert resp.status_code == 200
        assert "text/html" in resp.headers["content-type"]
        assert "Option Scanner" in resp.text


class TestMarketSnapshot:
    """Tests for GET /api/market/snapshot/{symbol}."""

    def test_market_snapshot_returns_live_regime(self, client):
        """vol_engine.detect_regime is called and its result appears in volatility.regime."""
        from agent.vol_engine import VolRegime, VolatilityResult, VolatilityModel
        from datetime import datetime

        mock_regime = VolRegime.HIGH
        mock_vol_result = VolatilityResult(
            annual_volatility=0.42,
            daily_volatility=0.026,
            model_used=VolatilityModel.HYBRID,
            confidence_score=0.85,
            data_points=252,
            calculation_date=datetime(2026, 2, 20),
        )
        mock_iv_rank = 0.81

        with patch("ui.server.vol_engine.detect_regime", return_value=mock_regime), \
             patch("ui.server.vol_engine.calculate_volatility", return_value=mock_vol_result), \
             patch("ui.server.vol_engine.calculate_iv_rank", return_value=mock_iv_rank):
            resp = client.get("/api/market/snapshot/AAPL")

        assert resp.status_code == 200
        data = resp.json()
        assert "volatility" in data
        assert data["volatility"]["regime"] == "high"
        assert data["volatility"]["annual"] == pytest.approx(0.42, rel=1e-3)
        assert data["volatility"]["daily"] == pytest.approx(0.026, rel=1e-3)
        assert data["volatility"]["iv_rank"] == pytest.approx(0.81, rel=1e-3)

    def test_market_snapshot_no_fake_values(self, client):
        """relative_strength must NOT be present in the snapshot response."""
        from agent.vol_engine import VolRegime, VolatilityResult, VolatilityModel
        from datetime import datetime

        mock_vol_result = VolatilityResult(
            annual_volatility=0.30,
            daily_volatility=0.019,
            model_used=VolatilityModel.HISTORICAL,
            confidence_score=0.80,
            data_points=252,
            calculation_date=datetime(2026, 2, 20),
        )

        with patch("ui.server.vol_engine.detect_regime", return_value=VolRegime.MEDIUM), \
             patch("ui.server.vol_engine.calculate_volatility", return_value=mock_vol_result), \
             patch("ui.server.vol_engine.calculate_iv_rank", return_value=0.50):
            resp = client.get("/api/market/snapshot/SPY")

        assert resp.status_code == 200
        data = resp.json()
        assert "relative_strength" not in data

    def test_market_snapshot_change_pct_computed(self, client):
        """change_pct should be computed from yfinance 2-day history."""
        import pandas as pd
        from unittest.mock import patch, MagicMock

        # Build a 2-row DataFrame mimicking yf.Ticker.history(period="2d")
        mock_history = pd.DataFrame(
            {"Close": [200.0, 210.0]},
            index=pd.date_range("2026-02-19", periods=2)
        )
        mock_ticker = MagicMock()
        mock_ticker.history.return_value = mock_history

        with patch("ui.server.yf.Ticker", return_value=mock_ticker), \
             patch("ui.server.market_data.get_current_price", return_value=210.0), \
             patch("ui.server.market_data.get_liquidity_metrics", side_effect=Exception("skip")), \
             patch("ui.server.vol_engine.detect_regime", side_effect=Exception("skip")), \
             patch("ui.server.vol_engine.calculate_volatility", side_effect=Exception("skip")), \
             patch("ui.server.vol_engine.calculate_iv_rank", side_effect=Exception("skip")), \
             patch("ui.server.vol_engine.calculate_expected_move", side_effect=Exception("skip")), \
             patch("ui.server.event_loader.get_blocking_events", return_value=[]):
            resp = client.get("/api/market/snapshot/AAPL")

        assert resp.status_code == 200
        data = resp.json()
        assert data["change_pct"] is not None
        # (210 - 200) / 200 * 100 = 5.0
        assert abs(data["change_pct"] - 5.0) < 0.01
