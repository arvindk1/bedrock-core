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

    @patch("ui.server.invoke_agent")
    def test_scan_success(self, mock_invoke, client):
        mock_invoke.return_value = {
            "status": "success",
            "output": "Call $295 (exp 2026-03-27) - Score 3.34"
        }
        resp = client.post("/api/scan", json={
            "symbol": "AAPL",
            "start_date": "2026-03-01",
            "end_date": "2026-04-01",
            "top_n": 5,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "success"
        assert "295" in data["output"]

    def test_scan_missing_symbol(self, client):
        resp = client.post("/api/scan", json={
            "symbol": "",
            "start_date": "2026-03-01",
            "end_date": "2026-04-01",
        })
        assert resp.status_code == 422 or resp.status_code == 400

    def test_scan_invalid_dates(self, client):
        resp = client.post("/api/scan", json={
            "symbol": "AAPL",
            "start_date": "2026-04-01",
            "end_date": "2026-03-01",
        })
        assert resp.status_code == 422

    @patch("ui.server.invoke_agent")
    def test_scan_agent_error(self, mock_invoke, client):
        mock_invoke.side_effect = Exception("Runtime unavailable")
        resp = client.post("/api/scan", json={
            "symbol": "AAPL",
            "start_date": "2026-03-01",
            "end_date": "2026-04-01",
        })
        assert resp.status_code == 502
        assert "error" in resp.json()["status"]


class TestStaticFiles:
    """Tests for static file serving."""

    def test_index_page_loads(self, client):
        resp = client.get("/")
        assert resp.status_code == 200
        assert "text/html" in resp.headers["content-type"]
        assert "Options Scanner" in resp.text
