"""Tests for POST /api/trade/execute endpoint."""
import json
from unittest.mock import patch, MagicMock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool


# ---------------------------------------------------------------------------
# In-memory DB fixture shared across tests in this module
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def in_memory_session_factory():
    """
    Shared in-memory SQLite DB with StaticPool (same connection reused)
    so every SessionLocal() call within a test sees the same data.
    """
    import sys, os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

    from db.models import Base, Portfolio

    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    TestSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    # Seed a default portfolio
    db = TestSession()
    try:
        portfolio = Portfolio(name="TestPortfolio", total_cash_balance=100000.0)
        db.add(portfolio)
        db.commit()
    finally:
        db.close()

    return TestSession


@pytest.fixture
def client_with_db(in_memory_session_factory):
    """TestClient with server's SessionLocal patched to the in-memory DB."""
    from ui.server import app
    with patch("ui.server.SessionLocal", in_memory_session_factory), \
         patch("ui.server.seed", return_value=None):
        yield TestClient(app)


# ---------------------------------------------------------------------------
# Helper: build a minimal valid trade execute payload
# ---------------------------------------------------------------------------

def _trade_payload(**overrides):
    payload = {
        "symbol": "AAPL",
        "strategy": "BULL_CALL_SPREAD",
        "expiration_date": "2026-03-21",
        "quantity": 1,
        "cost_basis": 250.0,
        "max_profit": 500.0,
        "max_loss": 250.0,
        "is_credit": False,
        "delta": 0.45,
        "gamma": 0.05,
        "theta": -0.10,
        "vega": 0.20,
    }
    payload.update(overrides)
    return payload


# ---------------------------------------------------------------------------
# Approved trade — position saved and success response returned
# ---------------------------------------------------------------------------

class TestTradeExecuteApproved:
    """POST /api/trade/execute when gatekeeper approves the trade."""

    def test_trade_execute_approved_saves_position(self, client_with_db, in_memory_session_factory):
        """Mock gatekeeper to approve; assert position saved to in-memory DB and response correct."""
        from agent.market_checks import TradeScore

        approved_score = TradeScore(
            symbol="AAPL",
            strategy="BULL_CALL_SPREAD",
            total_score=87.0,
            is_approved=True,
            rejection_reason=None,
            warnings=[],
            score_breakdown={"Starting Score": 100.0, "Liquidity Penalty": -13.0},
        )

        with patch("ui.server.gatekeeper.check_trade", return_value=approved_score):
            resp = client_with_db.post("/api/trade/execute", json=_trade_payload())

        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "executed"
        assert "position_id" in data
        assert isinstance(data["position_id"], int)
        assert data["symbol"] == "AAPL"
        assert data["strategy"] == "BULL_CALL_SPREAD"
        assert data["gatekeeper_score"] == 87.0
        assert "Position opened" in data["message"]

    def test_trade_execute_position_persisted_in_db(self, client_with_db, in_memory_session_factory):
        """Position is actually present in the DB after a successful execute call."""
        from agent.market_checks import TradeScore
        from db.models import Position

        approved_score = TradeScore(
            symbol="MSFT",
            strategy="IRON_CONDOR",
            total_score=92.0,
            is_approved=True,
            rejection_reason=None,
        )

        payload = _trade_payload(symbol="MSFT", strategy="IRON_CONDOR", quantity=2)

        with patch("ui.server.gatekeeper.check_trade", return_value=approved_score):
            resp = client_with_db.post("/api/trade/execute", json=payload)

        assert resp.status_code == 200
        position_id = resp.json()["position_id"]

        # Verify record exists in DB
        db = in_memory_session_factory()
        try:
            pos = db.query(Position).filter(Position.id == position_id).first()
            assert pos is not None
            assert pos.symbol == "MSFT"
            assert pos.strategy == "IRON_CONDOR"
            assert pos.quantity == 2
            assert pos.status == "open"
            assert pos.days_held == 0
        finally:
            db.close()

    def test_trade_execute_decision_audit_saved(self, client_with_db, in_memory_session_factory):
        """A DecisionAudit row is created for each successful execute call."""
        from agent.market_checks import TradeScore
        from db.models import DecisionAudit

        approved_score = TradeScore(
            symbol="NVDA",
            strategy="SHORT_PUT_SPREAD",
            total_score=78.0,
            is_approved=True,
            rejection_reason=None,
        )

        payload = _trade_payload(symbol="NVDA", strategy="SHORT_PUT_SPREAD")

        with patch("ui.server.gatekeeper.check_trade", return_value=approved_score):
            resp = client_with_db.post("/api/trade/execute", json=payload)

        assert resp.status_code == 200

        db = in_memory_session_factory()
        try:
            audit = (
                db.query(DecisionAudit)
                .filter(DecisionAudit.symbol == "NVDA")
                .order_by(DecisionAudit.id.desc())
                .first()
            )
            assert audit is not None
            assert audit.policy_mode == "manual"
            assert audit.picks_count == 1
            log = json.loads(audit.decision_log_json)
            assert log["action"] == "manual_execute"
            assert log["gatekeeper_score"] == 78.0
        finally:
            db.close()

    def test_trade_execute_message_includes_quantity(self, client_with_db):
        """Response message includes symbol, strategy, and quantity."""
        from agent.market_checks import TradeScore

        approved_score = TradeScore(
            symbol="AAPL",
            strategy="BULL_CALL_SPREAD",
            total_score=85.0,
            is_approved=True,
            rejection_reason=None,
        )

        payload = _trade_payload(quantity=3)

        with patch("ui.server.gatekeeper.check_trade", return_value=approved_score):
            resp = client_with_db.post("/api/trade/execute", json=payload)

        assert resp.status_code == 200
        msg = resp.json()["message"]
        assert "AAPL" in msg
        assert "BULL_CALL_SPREAD" in msg
        assert "x3" in msg


# ---------------------------------------------------------------------------
# Rejected trade — 422 with proper body, no position saved
# ---------------------------------------------------------------------------

class TestTradeExecuteRejected:
    """POST /api/trade/execute when gatekeeper rejects the trade."""

    def test_trade_execute_rejected_returns_422(self, client_with_db):
        """Mock gatekeeper to reject; assert 422 and approved == False in response."""
        from agent.market_checks import TradeScore

        rejected_score = TradeScore(
            symbol="AAPL",
            strategy="BULL_CALL_SPREAD",
            total_score=55.0,
            is_approved=False,
            rejection_reason="Score 55 below threshold 70",
        )

        with patch("ui.server.gatekeeper.check_trade", return_value=rejected_score):
            resp = client_with_db.post("/api/trade/execute", json=_trade_payload())

        assert resp.status_code == 422
        data = resp.json()
        assert data["approved"] is False
        assert "reason" in data
        assert "score" in data

    def test_trade_execute_rejected_reason_populated(self, client_with_db):
        """Rejection reason is forwarded verbatim from the score card."""
        from agent.market_checks import TradeScore

        rejection_msg = "Score 60 below threshold 70"
        rejected_score = TradeScore(
            symbol="AAPL",
            strategy="BULL_CALL_SPREAD",
            total_score=60.0,
            is_approved=False,
            rejection_reason=rejection_msg,
        )

        with patch("ui.server.gatekeeper.check_trade", return_value=rejected_score):
            resp = client_with_db.post("/api/trade/execute", json=_trade_payload())

        assert resp.status_code == 422
        data = resp.json()
        assert data["reason"] == rejection_msg
        assert data["score"] == 60.0

    def test_trade_execute_rejected_no_position_saved(self, client_with_db, in_memory_session_factory):
        """When rejected, no new Position row is written to the DB."""
        from agent.market_checks import TradeScore
        from db.models import Position

        # Count positions before
        db = in_memory_session_factory()
        count_before = db.query(Position).count()
        db.close()

        rejected_score = TradeScore(
            symbol="XOM",
            strategy="COVERED_CALL",
            total_score=40.0,
            is_approved=False,
            rejection_reason="Score 40 below threshold 70",
        )

        payload = _trade_payload(symbol="XOM", strategy="COVERED_CALL")

        with patch("ui.server.gatekeeper.check_trade", return_value=rejected_score):
            resp = client_with_db.post("/api/trade/execute", json=payload)

        assert resp.status_code == 422

        db = in_memory_session_factory()
        count_after = db.query(Position).count()
        db.close()

        assert count_after == count_before, "No new position should be saved on rejection"


# ---------------------------------------------------------------------------
# Sector map resolution
# ---------------------------------------------------------------------------

class TestTradeExecuteSectorMap:
    """SECTOR_MAP fallback logic for sector field."""

    def test_trade_execute_uses_sector_map_when_sector_not_provided(
        self, client_with_db, in_memory_session_factory
    ):
        """Sector is set from SECTOR_MAP when not provided in the request."""
        from agent.market_checks import TradeScore
        from db.models import Position

        approved_score = TradeScore(
            symbol="JPM",
            strategy="BULL_CALL_SPREAD",
            total_score=80.0,
            is_approved=True,
            rejection_reason=None,
        )

        # No sector in payload — should be resolved from SECTOR_MAP
        payload = _trade_payload(symbol="JPM", strategy="BULL_CALL_SPREAD")
        # Remove sector explicitly to ensure it's absent
        payload.pop("sector", None)

        with patch("ui.server.gatekeeper.check_trade", return_value=approved_score):
            resp = client_with_db.post("/api/trade/execute", json=payload)

        assert resp.status_code == 200
        position_id = resp.json()["position_id"]

        db = in_memory_session_factory()
        try:
            pos = db.query(Position).filter(Position.id == position_id).first()
            assert pos is not None
            # JPM maps to "Financials" in SECTOR_MAP
            assert pos.sector == "Financials"
        finally:
            db.close()

    def test_trade_execute_uses_sector_map_for_known_tech_symbol(
        self, client_with_db, in_memory_session_factory
    ):
        """SECTOR_MAP correctly returns 'Technology' for NVDA when sector omitted."""
        from agent.market_checks import TradeScore
        from db.models import Position

        approved_score = TradeScore(
            symbol="NVDA",
            strategy="BULL_CALL_SPREAD",
            total_score=82.0,
            is_approved=True,
            rejection_reason=None,
        )

        payload = _trade_payload(symbol="NVDA", strategy="BULL_CALL_SPREAD")
        payload.pop("sector", None)

        with patch("ui.server.gatekeeper.check_trade", return_value=approved_score):
            resp = client_with_db.post("/api/trade/execute", json=payload)

        assert resp.status_code == 200
        position_id = resp.json()["position_id"]

        db = in_memory_session_factory()
        try:
            pos = db.query(Position).filter(Position.id == position_id).first()
            assert pos is not None
            assert pos.sector == "Technology"
        finally:
            db.close()

    def test_trade_execute_unknown_symbol_defaults_to_unknown_sector(
        self, client_with_db, in_memory_session_factory
    ):
        """Symbols not in SECTOR_MAP get sector='Unknown'."""
        from agent.market_checks import TradeScore
        from db.models import Position

        approved_score = TradeScore(
            symbol="XYZQ",
            strategy="BULL_CALL_SPREAD",
            total_score=75.0,
            is_approved=True,
            rejection_reason=None,
        )

        payload = _trade_payload(symbol="XYZQ", strategy="BULL_CALL_SPREAD")
        payload.pop("sector", None)

        with patch("ui.server.gatekeeper.check_trade", return_value=approved_score):
            resp = client_with_db.post("/api/trade/execute", json=payload)

        assert resp.status_code == 200
        position_id = resp.json()["position_id"]

        db = in_memory_session_factory()
        try:
            pos = db.query(Position).filter(Position.id == position_id).first()
            assert pos is not None
            assert pos.sector == "Unknown"
        finally:
            db.close()

    def test_trade_execute_explicit_sector_overrides_sector_map(
        self, client_with_db, in_memory_session_factory
    ):
        """When sector is explicitly provided in request, it takes priority over SECTOR_MAP."""
        from agent.market_checks import TradeScore
        from db.models import Position

        approved_score = TradeScore(
            symbol="AAPL",
            strategy="BULL_CALL_SPREAD",
            total_score=88.0,
            is_approved=True,
            rejection_reason=None,
        )

        # AAPL maps to "Technology" in SECTOR_MAP, but we pass "Custom Sector"
        payload = _trade_payload(symbol="AAPL", strategy="BULL_CALL_SPREAD", sector="Custom Sector")

        with patch("ui.server.gatekeeper.check_trade", return_value=approved_score):
            resp = client_with_db.post("/api/trade/execute", json=payload)

        assert resp.status_code == 200
        position_id = resp.json()["position_id"]

        db = in_memory_session_factory()
        try:
            pos = db.query(Position).filter(Position.id == position_id).first()
            assert pos is not None
            assert pos.sector == "Custom Sector"
        finally:
            db.close()


# ---------------------------------------------------------------------------
# Input validation
# ---------------------------------------------------------------------------

class TestTradeExecuteValidation:
    """Input validation for POST /api/trade/execute."""

    def test_symbol_is_uppercased(self, client_with_db):
        """Symbol is normalised to uppercase by the field validator."""
        from agent.market_checks import TradeScore

        approved_score = TradeScore(
            symbol="AAPL",
            strategy="BULL_CALL_SPREAD",
            total_score=85.0,
            is_approved=True,
            rejection_reason=None,
        )

        payload = _trade_payload(symbol="aapl")

        with patch("ui.server.gatekeeper.check_trade", return_value=approved_score):
            resp = client_with_db.post("/api/trade/execute", json=payload)

        assert resp.status_code == 200
        assert resp.json()["symbol"] == "AAPL"

    def test_missing_required_fields_returns_422(self, client_with_db):
        """Missing required fields (cost_basis, etc.) yields Pydantic 422."""
        resp = client_with_db.post("/api/trade/execute", json={"symbol": "AAPL"})
        assert resp.status_code == 422
