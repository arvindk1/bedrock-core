"""Tests for GET /api/portfolio/risk and GET /api/portfolio/positions endpoints."""

import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool


# ---------------------------------------------------------------------------
# In-memory DB fixture (StaticPool keeps the same connection so :memory: works)
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def in_memory_session_factory():
    """
    Create an in-memory SQLite DB with a StaticPool (shared connection) so
    that every SessionLocal() call within a test sees the same data.
    """
    import sys
    import os

    sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

    from db.models import Base, Portfolio, Position

    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,  # <-- key: reuse the same in-memory connection
    )
    Base.metadata.create_all(bind=engine)
    TestSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    # Seed once for the module
    db = TestSession()
    try:
        portfolio = Portfolio(name="TestPortfolio", total_cash_balance=100000.0)
        db.add(portfolio)
        db.flush()

        positions = [
            Position(
                portfolio_id=portfolio.id,
                symbol="AAPL",
                strategy="BULL_CALL_SPREAD",
                quantity=2,
                cost_basis=250.0,
                current_mark=285.0,
                unrealized_pnl=70.0,
                max_profit=480.0,
                max_loss=520.0,
                delta=0.65,
                gamma=0.12,
                theta=-0.08,
                vega=-0.15,
                sector="Technology",
                is_credit=False,
                expiration_date="2026-03-21",
                days_held=12,
                status="open",
            ),
            Position(
                portfolio_id=portfolio.id,
                symbol="NVDA",
                strategy="SHORT_CALL_SPREAD",
                quantity=3,
                cost_basis=180.0,
                current_mark=162.0,
                unrealized_pnl=54.0,
                max_profit=180.0,
                max_loss=270.0,
                delta=-0.45,
                gamma=-0.08,
                theta=0.18,
                vega=-0.25,
                sector="Technology",
                is_credit=True,
                expiration_date="2026-03-14",
                days_held=8,
                status="open",
            ),
            Position(
                portfolio_id=portfolio.id,
                symbol="JPM",
                strategy="IRON_CONDOR",
                quantity=1,
                cost_basis=150.0,
                current_mark=155.0,
                unrealized_pnl=5.0,
                max_profit=150.0,
                max_loss=350.0,
                delta=0.05,
                gamma=-0.02,
                theta=0.25,
                vega=-0.30,
                sector="Finance",
                is_credit=True,
                expiration_date="2026-04-17",
                days_held=5,
                status="open",
            ),
            Position(
                portfolio_id=portfolio.id,
                symbol="XOM",
                strategy="COVERED_CALL",
                quantity=1,
                cost_basis=130.0,
                current_mark=105.0,
                unrealized_pnl=-16.0,
                max_profit=130.0,
                max_loss=0.0,
                delta=0.60,
                gamma=0.08,
                theta=0.20,
                vega=-0.19,
                sector="Energy",
                is_credit=True,
                expiration_date="2026-03-21",
                days_held=15,
                status="open",
            ),
            # Closed position — must NOT appear in risk calculations
            Position(
                portfolio_id=portfolio.id,
                symbol="MSFT",
                strategy="BULL_CALL_SPREAD",
                quantity=1,
                cost_basis=200.0,
                current_mark=180.0,
                unrealized_pnl=-20.0,
                max_profit=300.0,
                max_loss=200.0,
                delta=0.50,
                gamma=0.05,
                theta=-0.05,
                vega=-0.10,
                sector="Technology",
                is_credit=False,
                expiration_date="2026-02-01",
                days_held=30,
                status="closed",
            ),
        ]
        db.add_all(positions)
        db.commit()
    finally:
        db.close()

    return TestSession


@pytest.fixture
def client_with_db(in_memory_session_factory):
    """Return a TestClient with the server's SessionLocal patched to the in-memory DB."""
    from ui.server import app

    # Also patch seed() so the auto-seed path doesn't open the real DB
    with (
        patch("ui.server.SessionLocal", in_memory_session_factory),
        patch("ui.server.seed", return_value=None),
    ):
        yield TestClient(app)


# ---------------------------------------------------------------------------
# Tests: GET /api/portfolio/risk
# ---------------------------------------------------------------------------


class TestPortfolioRiskEndpoint:
    """Tests for GET /api/portfolio/risk with live DB data."""

    def test_portfolio_risk_uses_db_positions(self, client_with_db):
        """total_capital_at_risk must be non-zero when DB has open positions."""
        resp = client_with_db.get("/api/portfolio/risk")
        assert resp.status_code == 200
        data = resp.json()
        assert "total_capital_at_risk" in data
        # AAPL: abs(250*2)=500, NVDA: abs(180*3)=540, JPM: abs(150*1)=150, XOM: abs(130*1)=130
        # Total = 1320
        assert data["total_capital_at_risk"] > 0
        assert data["total_capital_at_risk"] == pytest.approx(1320.0, rel=1e-3)

    def test_portfolio_risk_excludes_closed_positions(self, client_with_db):
        """Closed positions (MSFT) must NOT be included in risk metrics."""
        resp = client_with_db.get("/api/portfolio/risk")
        assert resp.status_code == 200
        data = resp.json()
        # MSFT (closed) cost_basis=200, quantity=1 → abs(200*1)=200
        # If closed positions were included: total = 1520, not 1320
        assert data["total_capital_at_risk"] == pytest.approx(1320.0, rel=1e-3)

    def test_portfolio_risk_sector_exposure_computed(self, client_with_db):
        """sector_exposure must be derived from actual DB positions."""
        resp = client_with_db.get("/api/portfolio/risk")
        assert resp.status_code == 200
        data = resp.json()

        assert "sector_exposure" in data
        sectors = {s["name"]: s for s in data["sector_exposure"]}

        # Technology: AAPL(500) + NVDA(540) = 1040 / 1320 ≈ 0.788
        assert "Technology" in sectors
        tech = sectors["Technology"]
        assert tech["value"] == pytest.approx(1040 / 1320, rel=1e-2)
        assert tech["limit"] > 0  # limit from APP_CONFIG

        # Technology exceeds default limit of 0.25 → critical
        assert tech["status"] == "critical"

        # Finance: JPM(150) / 1320 ≈ 0.114 → normal
        assert "Finance" in sectors
        fin = sectors["Finance"]
        assert fin["value"] == pytest.approx(150 / 1320, rel=1e-2)
        assert fin["status"] == "normal"

        # Energy: XOM(130) / 1320 ≈ 0.098 → normal
        assert "Energy" in sectors
        nrg = sectors["Energy"]
        assert nrg["value"] == pytest.approx(130 / 1320, rel=1e-2)
        assert nrg["status"] == "normal"

    def test_portfolio_risk_alerts_for_critical_sectors(self, client_with_db):
        """Alerts list must include an entry for Technology (critical)."""
        resp = client_with_db.get("/api/portfolio/risk")
        assert resp.status_code == 200
        data = resp.json()
        assert "alerts" in data
        # Technology is critical → should generate a concentration alert
        critical_alerts = [a for a in data["alerts"] if a.get("severity") == "critical"]
        assert len(critical_alerts) >= 1
        tech_alert = next(
            (a for a in critical_alerts if "Technology" in a.get("message", "")),
            None,
        )
        assert tech_alert is not None, "Expected a critical alert for Technology sector"
        assert "recommendation" in tech_alert

    def test_portfolio_risk_net_delta_computed(self, client_with_db):
        """net_delta must be sum of (delta * quantity * 100) for open positions."""
        resp = client_with_db.get("/api/portfolio/risk")
        assert resp.status_code == 200
        data = resp.json()
        assert "net_delta" in data

        # AAPL: 0.65 * 2 * 100 = 130
        # NVDA: -0.45 * 3 * 100 = -135
        # JPM: 0.05 * 1 * 100 = 5
        # XOM: 0.60 * 1 * 100 = 60
        # Sum = 130 - 135 + 5 + 60 = 60
        assert data["net_delta"] == pytest.approx(60.0, abs=0.1)

    def test_portfolio_risk_daily_drawdown_computed(self, client_with_db):
        """daily_drawdown must be sum of unrealized_pnl for open positions."""
        resp = client_with_db.get("/api/portfolio/risk")
        assert resp.status_code == 200
        data = resp.json()
        assert "daily_drawdown" in data

        # AAPL: 70, NVDA: 54, JPM: 5, XOM: -16 → total = 113
        assert data["daily_drawdown"] == pytest.approx(113.0, abs=0.1)

    def test_portfolio_risk_max_risk_per_trade_from_config(self, client_with_db):
        """max_risk_per_trade must come from APP_CONFIG policy_limits.tight."""
        from ui.server import APP_CONFIG

        resp = client_with_db.get("/api/portfolio/risk")
        assert resp.status_code == 200
        data = resp.json()
        assert "max_risk_per_trade" in data
        expected = APP_CONFIG["policy_limits"]["tight"]
        assert data["max_risk_per_trade"] == expected

    def test_portfolio_risk_returns_500_on_db_error(self):
        """If the DB session raises an exception, endpoint must return 500."""
        from ui.server import app

        broken_session = MagicMock()
        broken_session.return_value.query.side_effect = RuntimeError("DB exploded")

        with patch("ui.server.SessionLocal", broken_session):
            test_client = TestClient(app, raise_server_exceptions=False)
            resp = test_client.get("/api/portfolio/risk")

        assert resp.status_code == 500
        data = resp.json()
        assert "error" in data


# ---------------------------------------------------------------------------
# Tests: GET /api/portfolio/positions
# ---------------------------------------------------------------------------


class TestPortfolioPositionsEndpoint:
    """Tests for GET /api/portfolio/positions."""

    def test_portfolio_positions_endpoint(self, client_with_db):
        """GET /api/portfolio/positions returns a list with at least 1 position."""
        resp = client_with_db.get("/api/portfolio/positions")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) >= 1

    def test_portfolio_positions_only_open(self, client_with_db):
        """Positions endpoint must return only open positions."""
        resp = client_with_db.get("/api/portfolio/positions")
        assert resp.status_code == 200
        data = resp.json()
        # Only 4 open positions in our fixture (MSFT is closed)
        assert len(data) == 4
        for pos in data:
            assert pos["status"] == "open"

    def test_portfolio_positions_required_fields(self, client_with_db):
        """Each position must contain the required display fields."""
        required_fields = {
            "id",
            "symbol",
            "strategy",
            "quantity",
            "cost_basis",
            "current_mark",
            "unrealized_pnl",
            "max_profit",
            "max_loss",
            "delta",
            "gamma",
            "theta",
            "vega",
            "sector",
            "is_credit",
            "expiration_date",
            "days_held",
            "status",
        }
        resp = client_with_db.get("/api/portfolio/positions")
        assert resp.status_code == 200
        data = resp.json()
        for pos in data:
            missing = required_fields - set(pos.keys())
            assert not missing, (
                f"Position {pos.get('symbol')} missing fields: {missing}"
            )

    def test_portfolio_positions_numeric_fields_rounded(self, client_with_db):
        """cost_basis, current_mark, unrealized_pnl must be floats rounded to 2 dp."""
        resp = client_with_db.get("/api/portfolio/positions")
        assert resp.status_code == 200
        data = resp.json()
        for pos in data:
            for field in ("cost_basis", "current_mark", "unrealized_pnl"):
                val = pos[field]
                if val is not None:
                    assert isinstance(val, (int, float))
                    # Value rounded to 2 decimal places should equal itself
                    assert round(val, 2) == val

    def test_portfolio_positions_symbols_present(self, client_with_db):
        """Verify that known open symbols appear in the response."""
        resp = client_with_db.get("/api/portfolio/positions")
        assert resp.status_code == 200
        data = resp.json()
        symbols = {pos["symbol"] for pos in data}
        assert "AAPL" in symbols
        assert "NVDA" in symbols
        # MSFT is closed, must NOT appear
        assert "MSFT" not in symbols

    def test_portfolio_positions_returns_500_on_db_error(self):
        """If the DB session raises an exception, endpoint must return 500."""
        from ui.server import app

        broken_session = MagicMock()
        broken_session.return_value.query.side_effect = RuntimeError("DB exploded")

        with patch("ui.server.SessionLocal", broken_session):
            test_client = TestClient(app, raise_server_exceptions=False)
            resp = test_client.get("/api/portfolio/positions")

        assert resp.status_code == 500
        data = resp.json()
        assert "error" in data
