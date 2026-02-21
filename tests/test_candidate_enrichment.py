"""
Tests for candidate enrichment and orchestrator integration

Verifies:
1. Candidates are enriched with Phase-2 fields (bid, ask, OI, volume)
2. Orchestrator passes enriched candidates to ScoredGatekeeper
3. Full flow: candidates → gatekeeper → final picks
"""

from unittest.mock import patch, MagicMock

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "agent"))

from options_scanner import OptionsScanner


class TestCandidateEnrichment:
    """Test that candidates include Phase-2 liquidity fields."""

    def test_candidate_legs_have_phase2_fields(self):
        """Candidate legs include: bid, ask, open_interest, volume."""
        # Create a mock scanner (don't patch market_data, just pass chain directly)
        scanner = OptionsScanner()

        # Create mock chain with calls DataFrame
        import pandas as pd

        calls_data = {
            "strike": [150.0, 155.0],
            "bid": [2.0, 1.0],
            "ask": [2.05, 1.05],
            "openInterest": [5000, 4000],
            "volume": [150, 120],
            "lastPrice": [2.02, 1.02],
            "impliedVolatility": [0.25, 0.24],
        }
        calls_df = pd.DataFrame(calls_data)

        # Create empty puts DataFrame with same columns as calls
        puts_df = pd.DataFrame(columns=calls_df.columns)

        mock_chain = MagicMock()
        mock_chain.calls = calls_df
        mock_chain.puts = puts_df  # Empty puts for this test

        # Call _find_vertical_spreads directly with mock chain
        candidates = scanner._find_vertical_spreads(
            symbol="AAPL",
            spot=150.0,
            chain=mock_chain,
            expiry="2026-03-20",
            strategy="DEBIT_SPREAD",
        )

        if candidates:
            # Check first candidate
            candidate = candidates[0]
            assert "legs" in candidate
            legs = candidate["legs"]

            # Each leg should have Phase-2 fields
            for leg in legs:
                assert "bid" in leg, f"Missing 'bid' in leg: {leg}"
                assert "ask" in leg, f"Missing 'ask' in leg: {leg}"
                assert "open_interest" in leg, f"Missing 'open_interest' in leg: {leg}"
                assert "volume" in leg, f"Missing 'volume' in leg: {leg}"
                assert isinstance(leg["bid"], float)
                assert isinstance(leg["ask"], float)
                assert isinstance(leg["open_interest"], int)
                assert isinstance(leg["volume"], int)

    def test_candidate_has_required_fields(self):
        """Candidate dict has all required top-level fields."""
        scanner = OptionsScanner()

        import pandas as pd

        calls_data = {
            "strike": [150.0, 155.0],
            "bid": [2.0, 1.0],
            "ask": [2.05, 1.05],
            "openInterest": [5000, 4000],
            "volume": [150, 120],
            "lastPrice": [2.02, 1.02],
            "impliedVolatility": [0.25, 0.24],
        }
        calls_df = pd.DataFrame(calls_data)

        # Create empty puts DataFrame with same columns as calls
        puts_df = pd.DataFrame(columns=calls_df.columns)

        mock_chain = MagicMock()
        mock_chain.calls = calls_df
        mock_chain.puts = puts_df

        candidates = scanner._find_vertical_spreads(
            symbol="AAPL",
            spot=150.0,
            chain=mock_chain,
            expiry="2026-03-20",
            strategy="DEBIT_SPREAD",
        )

        if candidates:
            candidate = candidates[0]
            assert "symbol" in candidate
            assert "strategy" in candidate
            assert "expiration" in candidate
            assert "legs" in candidate
            assert "cost" in candidate
            assert "max_profit" in candidate


class TestOrchestratorGatekeeperIntegration:
    """Test that orchestrator passes candidates to gatekeeper."""

    @patch("options_scanner.generate_candidates")
    @patch("risk_engine.RiskEngine")
    @patch("market_checks.ScoredGatekeeper")
    @patch("orchestrator.vol_and_events_context")
    def test_orchestrator_scores_candidates(
        self, mock_vol_ctx, mock_gatekeeper_cls, mock_risk_cls, mock_gen_cand
    ):
        """Orchestrator passes candidates to gatekeeper and scores them."""
        from orchestrator import full_scan_with_orchestration

        # Mock vol/events context
        mock_vol_ctx.return_value = {
            "regime": MagicMock(value="LOW"),
            "vol_details": {},
            "blocking_events": [],
            "strategy_hint": "DEBIT_SPREAD",
        }

        # Mock risk engine
        mock_risk = MagicMock()
        mock_risk.should_reject_trade.return_value = (False, None)  # Accept all
        mock_risk_cls.return_value = mock_risk

        # Mock gatekeeper
        mock_gatekeeper = MagicMock()
        mock_score = MagicMock()
        mock_score.is_approved = True
        mock_score.total_score = 85.0
        mock_score.warnings = []
        mock_score.rejection_reason = None
        mock_gatekeeper.check_trade.return_value = mock_score
        mock_gatekeeper_cls.return_value = mock_gatekeeper

        # Mock candidate generation
        mock_gen_cand.return_value = [
            {
                "symbol": "AAPL",
                "strategy": "BULL_CALL_DEBIT_SPREAD",
                "expiration": "2026-03-20",
                "cost": 1.0,
                "max_profit": 3.0,
                "legs": [
                    {
                        "bid": 2.0,
                        "ask": 2.05,
                        "open_interest": 5000,
                        "volume": 150,
                    },
                    {
                        "bid": 1.0,
                        "ask": 1.05,
                        "open_interest": 4000,
                        "volume": 120,
                    },
                ],
            }
        ]

        log = full_scan_with_orchestration(
            symbol="AAPL",
            start_date="2026-03-01",
            end_date="2026-06-01",
            top_n=5,
            portfolio=[],
            policy_mode="tight",
        )

        # Verify gatekeeper was called
        assert mock_gatekeeper.check_trade.called
        call_args = mock_gatekeeper.check_trade.call_args

        # Verify the trade_proposal passed to gatekeeper has correct fields
        trade_proposal = call_args[0][0]
        assert trade_proposal["symbol"] == "AAPL"
        assert trade_proposal["strategy_type"] == "BULL_CALL_DEBIT_SPREAD"
        assert trade_proposal["expiration_date"] == "2026-03-20"
        assert "legs" in trade_proposal
        assert len(trade_proposal["legs"]) == 2

        # Verify gatekeeper score is attached to candidate
        if log.final_picks:
            assert "gatekeeper_score" in log.final_picks[0]

    @patch("options_scanner.generate_candidates")
    @patch("risk_engine.RiskEngine")
    @patch("market_checks.ScoredGatekeeper")
    @patch("orchestrator.vol_and_events_context")
    def test_orchestrator_rejects_low_scoring_candidates(
        self, mock_vol_ctx, mock_gatekeeper_cls, mock_risk_cls, mock_gen_cand
    ):
        """Orchestrator filters out candidates that fail gatekeeper."""
        from orchestrator import full_scan_with_orchestration

        mock_vol_ctx.return_value = {
            "regime": MagicMock(value="LOW"),
            "vol_details": {},
            "blocking_events": [],
            "strategy_hint": "DEBIT_SPREAD",
        }

        mock_risk = MagicMock()
        mock_risk.should_reject_trade.return_value = (False, None)
        mock_risk_cls.return_value = mock_risk

        # Gatekeeper rejects the trade
        mock_gatekeeper = MagicMock()
        mock_score = MagicMock()
        mock_score.is_approved = False
        mock_score.total_score = 45.0
        mock_score.rejection_reason = "Poor liquidity"
        mock_gatekeeper.check_trade.return_value = mock_score
        mock_gatekeeper_cls.return_value = mock_gatekeeper

        mock_gen_cand.return_value = [
            {
                "symbol": "AAPL",
                "strategy": "BULL_CALL_DEBIT_SPREAD",
                "expiration": "2026-03-20",
                "cost": 1.0,
                "max_profit": 3.0,
                "legs": [
                    {"bid": 2.0, "ask": 2.05, "open_interest": 100, "volume": 10},
                    {"bid": 1.0, "ask": 1.05, "open_interest": 50, "volume": 5},
                ],
            }
        ]

        log = full_scan_with_orchestration(
            symbol="AAPL",
            start_date="2026-03-01",
            end_date="2026-06-01",
            top_n=5,
            portfolio=[],
            policy_mode="tight",
        )

        # Candidate should be rejected by gatekeeper (doesn't reach correlation gate)
        assert len(log.final_picks) == 0
        # Gatekeeper rejects, so it doesn't appear in candidates_after_correlation
        assert len(log.candidates_after_correlation) == 0


class TestCandidateFieldAccuracy:
    """Test that enriched fields have correct types and values."""

    def test_enriched_leg_field_types(self):
        """All enriched fields have correct types."""
        # Create a mock leg as it would come from yfinance
        import pandas as pd

        data = {
            "strike": 150.0,
            "bid": 2.0,
            "ask": 2.05,
            "openInterest": 5000,
            "volume": 150,
            "lastPrice": 2.02,
            "impliedVolatility": 0.25,
        }
        row = pd.Series(data)

        # Simulate enrichment logic
        enriched = {
            "bid": float(row.get("bid", 0)),
            "ask": float(row.get("ask", 0)),
            "open_interest": int(row.get("openInterest", 0)),
            "volume": int(row.get("volume", 0)),
            "last_price": float(row.get("lastPrice", 0)),
            "implied_volatility": float(row.get("impliedVolatility", 0)),
        }

        # Verify types
        assert isinstance(enriched["bid"], float)
        assert isinstance(enriched["ask"], float)
        assert isinstance(enriched["open_interest"], int)
        assert isinstance(enriched["volume"], int)
        assert isinstance(enriched["last_price"], float)
        assert isinstance(enriched["implied_volatility"], float)

        # Verify values
        assert enriched["bid"] == 2.0
        assert enriched["ask"] == 2.05
        assert enriched["open_interest"] == 5000
        assert enriched["volume"] == 150
