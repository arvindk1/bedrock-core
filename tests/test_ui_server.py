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
