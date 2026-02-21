"""Database models for the options trading platform."""
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, Float, String, DateTime, Boolean, Text, ForeignKey, Index
from sqlalchemy.orm import declarative_base, relationship

def _utcnow():
    return datetime.now(timezone.utc)

Base = declarative_base()


class Portfolio(Base):
    __tablename__ = "portfolios"

    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False, default="Default")
    total_cash_balance = Column(Float, nullable=False, default=100000.0)
    created_at = Column(DateTime, default=_utcnow)

    positions = relationship("Position", back_populates="portfolio")


class Position(Base):
    __tablename__ = "positions"

    id = Column(Integer, primary_key=True)
    portfolio_id = Column(Integer, ForeignKey("portfolios.id"), nullable=False, index=True)
    symbol = Column(String(20), nullable=False)
    strategy = Column(String(50), nullable=False)       # e.g. "BULL_CALL_SPREAD"
    quantity = Column(Integer, nullable=False, default=1)
    cost_basis = Column(Float, nullable=False)          # total cost paid (debit) or received (credit)
    current_mark = Column(Float, nullable=True)         # last mark-to-market price
    unrealized_pnl = Column(Float, nullable=True)
    max_profit = Column(Float, nullable=True)
    max_loss = Column(Float, nullable=True)
    delta = Column(Float, nullable=True)
    gamma = Column(Float, nullable=True)
    theta = Column(Float, nullable=True)
    vega = Column(Float, nullable=True)
    sector = Column(String(50), nullable=True)
    is_credit = Column(Boolean, nullable=False, default=False)
    open_date = Column(DateTime, default=_utcnow)
    expiration_date = Column(String(20), nullable=True)  # ISO date string
    days_held = Column(Integer, nullable=True)
    status = Column(String(20), nullable=False, default="open", index=True)  # "open" | "closed"

    portfolio = relationship("Portfolio", back_populates="positions")


class DecisionAudit(Base):
    __tablename__ = "decision_audits"

    id = Column(Integer, primary_key=True)
    portfolio_id = Column(Integer, ForeignKey("portfolios.id"), nullable=True, index=True)
    symbol = Column(String(20), nullable=False)
    scan_timestamp = Column(DateTime, default=_utcnow, index=True)
    policy_mode = Column(String(20), nullable=False)
    regime = Column(String(10), nullable=True)
    picks_count = Column(Integer, default=0)
    decision_log_json = Column(Text, nullable=True)     # full JSON blob of the DecisionLog
