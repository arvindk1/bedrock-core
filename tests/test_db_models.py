"""Tests for the SQLite data layer: Portfolio, Position, DecisionAudit models."""

import pytest
import sys
import os

# Ensure project root is on the path so `db` package can be imported
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker

from db.models import Base, Portfolio, Position, DecisionAudit


# ---------------------------------------------------------------------------
# Shared in-memory DB fixture
# ---------------------------------------------------------------------------


@pytest.fixture()
def in_memory_engine():
    """Return a fresh in-memory SQLite engine with all tables created."""
    engine = create_engine(
        "sqlite:///:memory:", connect_args={"check_same_thread": False}
    )
    Base.metadata.create_all(bind=engine)
    yield engine
    engine.dispose()


@pytest.fixture()
def db_session(in_memory_engine):
    """Return a SQLAlchemy session bound to the in-memory engine."""
    Session = sessionmaker(bind=in_memory_engine)
    session = Session()
    yield session
    session.close()


# ---------------------------------------------------------------------------
# Test: init_db creates all expected tables
# ---------------------------------------------------------------------------


def test_init_db_creates_tables(in_memory_engine):
    """init_db() equivalent: Base.metadata.create_all creates all three tables."""
    inspector = inspect(in_memory_engine)
    table_names = inspector.get_table_names()

    assert "portfolios" in table_names, "portfolios table should be created"
    assert "positions" in table_names, "positions table should be created"
    assert "decision_audits" in table_names, "decision_audits table should be created"


def test_portfolios_table_columns(in_memory_engine):
    """portfolios table has the expected columns."""
    inspector = inspect(in_memory_engine)
    cols = {c["name"] for c in inspector.get_columns("portfolios")}

    assert "id" in cols
    assert "name" in cols
    assert "total_cash_balance" in cols
    assert "created_at" in cols


def test_positions_table_columns(in_memory_engine):
    """positions table has all expected columns including Greeks and metadata."""
    inspector = inspect(in_memory_engine)
    cols = {c["name"] for c in inspector.get_columns("positions")}

    required = {
        "id",
        "portfolio_id",
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
        "open_date",
        "expiration_date",
        "days_held",
        "status",
    }
    assert required.issubset(cols), f"Missing columns: {required - cols}"


def test_decision_audits_table_columns(in_memory_engine):
    """decision_audits table has all expected columns."""
    inspector = inspect(in_memory_engine)
    cols = {c["name"] for c in inspector.get_columns("decision_audits")}

    required = {
        "id",
        "portfolio_id",
        "symbol",
        "scan_timestamp",
        "policy_mode",
        "regime",
        "picks_count",
        "decision_log_json",
    }
    assert required.issubset(cols), f"Missing columns: {required - cols}"


# ---------------------------------------------------------------------------
# Test: seeding creates the expected portfolio and positions
# ---------------------------------------------------------------------------


def _run_seed(db_session):
    """Run the seed logic against an existing session (replicates seed.py logic)."""

    if db_session.query(Portfolio).count() > 0:
        return  # already seeded

    portfolio = Portfolio(name="Default", total_cash_balance=100000.0)
    db_session.add(portfolio)
    db_session.flush()

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
            symbol="UNH",
            strategy="PUT_CREDIT_SPREAD",
            quantity=2,
            cost_basis=120.0,
            current_mark=110.0,
            unrealized_pnl=20.0,
            max_profit=120.0,
            max_loss=380.0,
            delta=0.15,
            gamma=-0.05,
            theta=0.12,
            vega=-0.10,
            sector="Healthcare",
            is_credit=True,
            expiration_date="2026-03-28",
            days_held=4,
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
    ]
    db_session.add_all(positions)
    db_session.commit()


def test_seed_creates_portfolio_and_positions(db_session):
    """Seeding an empty DB produces exactly 1 portfolio and 5 positions."""
    _run_seed(db_session)

    portfolio_count = db_session.query(Portfolio).count()
    position_count = db_session.query(Position).count()

    assert portfolio_count == 1, f"Expected 1 portfolio, got {portfolio_count}"
    assert position_count == 5, f"Expected 5 positions, got {position_count}"


def test_seed_idempotent(db_session):
    """Running seed twice does not duplicate data."""
    _run_seed(db_session)
    _run_seed(db_session)

    assert db_session.query(Portfolio).count() == 1
    assert db_session.query(Position).count() == 5


def test_seed_portfolio_defaults(db_session):
    """Seeded portfolio has correct name and cash balance."""
    _run_seed(db_session)

    portfolio = db_session.query(Portfolio).first()
    assert portfolio.name == "Default"
    assert portfolio.total_cash_balance == 100000.0


# ---------------------------------------------------------------------------
# Test: individual position field values
# ---------------------------------------------------------------------------


def test_position_fields_aapl(db_session):
    """Seeded AAPL position has correct symbol, strategy, and sector."""
    _run_seed(db_session)

    aapl = db_session.query(Position).filter_by(symbol="AAPL").first()
    assert aapl is not None, "AAPL position should exist"
    assert aapl.strategy == "BULL_CALL_SPREAD"
    assert aapl.sector == "Technology"
    assert aapl.is_credit is False
    assert aapl.quantity == 2
    assert aapl.cost_basis == 250.0
    assert aapl.unrealized_pnl == 70.0
    assert aapl.delta == pytest.approx(0.65)
    assert aapl.expiration_date == "2026-03-21"
    assert aapl.status == "open"


def test_position_fields_nvda(db_session):
    """Seeded NVDA SHORT_CALL_SPREAD is correctly marked as a credit spread."""
    _run_seed(db_session)

    nvda = db_session.query(Position).filter_by(symbol="NVDA").first()
    assert nvda is not None
    assert nvda.strategy == "SHORT_CALL_SPREAD"
    assert nvda.is_credit is True
    assert nvda.theta == pytest.approx(0.18)
    assert nvda.sector == "Technology"


def test_position_fields_jpm(db_session):
    """Seeded JPM IRON_CONDOR position has Finance sector."""
    _run_seed(db_session)

    jpm = db_session.query(Position).filter_by(symbol="JPM").first()
    assert jpm is not None
    assert jpm.strategy == "IRON_CONDOR"
    assert jpm.sector == "Finance"
    assert jpm.is_credit is True


def test_position_relationship_to_portfolio(db_session):
    """Position.portfolio back-reference returns the parent Portfolio."""
    _run_seed(db_session)

    aapl = db_session.query(Position).filter_by(symbol="AAPL").first()
    assert aapl.portfolio is not None
    assert aapl.portfolio.name == "Default"


def test_portfolio_positions_relationship(db_session):
    """Portfolio.positions returns all 5 child positions."""
    _run_seed(db_session)

    portfolio = db_session.query(Portfolio).first()
    assert len(portfolio.positions) == 5


# ---------------------------------------------------------------------------
# Test: DecisionAudit model CRUD
# ---------------------------------------------------------------------------


def test_decision_audit_insert(db_session):
    """DecisionAudit can be inserted and queried without a portfolio FK."""
    audit = DecisionAudit(
        symbol="SPY",
        policy_mode="conservative",
        regime="LOW",
        picks_count=3,
        decision_log_json='{"picks": ["SPY_PUT_SPREAD"]}',
    )
    db_session.add(audit)
    db_session.commit()

    result = db_session.query(DecisionAudit).filter_by(symbol="SPY").first()
    assert result is not None
    assert result.policy_mode == "conservative"
    assert result.regime == "LOW"
    assert result.picks_count == 3
    assert "SPY_PUT_SPREAD" in result.decision_log_json


def test_decision_audit_with_portfolio_fk(db_session):
    """DecisionAudit can reference a Portfolio via portfolio_id FK."""
    _run_seed(db_session)

    portfolio = db_session.query(Portfolio).first()
    audit = DecisionAudit(
        portfolio_id=portfolio.id,
        symbol="AAPL",
        policy_mode="aggressive",
        regime="HIGH",
        picks_count=1,
    )
    db_session.add(audit)
    db_session.commit()

    result = db_session.query(DecisionAudit).filter_by(symbol="AAPL").first()
    assert result.portfolio_id == portfolio.id
