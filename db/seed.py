"""Seed the database with demo positions for local development."""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from db import init_db, SessionLocal
from db.models import Portfolio, Position


def seed():
    init_db()
    db = SessionLocal()
    try:
        # Idempotent: skip if already seeded
        if db.query(Portfolio).count() > 0:
            print("Database already seeded, skipping.")
            return

        portfolio = Portfolio(name="Default", total_cash_balance=100000.0)
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
        db.add_all(positions)
        db.commit()
        print(f"Seeded portfolio '{portfolio.name}' with {len(positions)} positions.")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
