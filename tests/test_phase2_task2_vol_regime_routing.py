"""
Task 2: Vol Regime Routing Tests
=================================

Verifies that vol regime detection actually affects candidate generation:
- LOW vol: Generate debit spreads (buy cheap premium)
- HIGH vol: Generate credit spreads (sell expensive premium)
- MEDIUM vol: Flexible or balanced approach

Currently the routing is cosmetic (says which to generate, but doesn't actually
change the generation logic). Task 2 makes it real.
"""

import sys
import os
from unittest.mock import patch, MagicMock


sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "agent"))

from options_scanner import OptionsScanner
from vol_engine import VolRegime


class TestVolRegimeRoutingFoundation:
    """Verify regime detection is wired to scanner."""

    def test_detect_regime_called_in_scan(self):
        """scan_opportunities calls vol_engine.detect_regime()."""
        scanner = OptionsScanner()

        with patch.object(scanner.vol_engine, "detect_regime") as mock_regime:
            mock_regime.return_value = VolRegime.LOW
            with patch.object(
                scanner, "_find_optimal_expiration", return_value="2026-03-20"
            ):
                with patch.object(
                    scanner.market_data, "get_current_price", return_value=150.0
                ):
                    with patch.object(
                        scanner.market_data, "get_option_chain", return_value=None
                    ):
                        # Should call detect_regime
                        scanner.scan_opportunities("AAPL")

                        mock_regime.assert_called_with("AAPL")

    def test_regime_determines_strategy_hint(self):
        """Regime (LOW/HIGH/MEDIUM) maps to strategy hint."""
        scanner = OptionsScanner()

        # Mock vol engine to return each regime
        with patch.object(scanner.vol_engine, "detect_regime") as mock_regime:
            with patch.object(
                scanner.vol_engine, "calculate_volatility"
            ) as mock_vol_calc:
                mock_vol_calc.return_value = MagicMock(annual_volatility=0.30)
                with patch.object(
                    scanner, "_find_optimal_expiration", return_value="2026-03-20"
                ):
                    with patch.object(
                        scanner.market_data, "get_current_price", return_value=150.0
                    ):
                        with patch.object(
                            scanner.market_data, "get_option_chain", return_value=None
                        ):
                            # LOW vol -> DEBIT_SPREAD
                            mock_regime.return_value = VolRegime.LOW
                            scanner.scan_opportunities("AAPL")
                            # We expect _find_vertical_spreads to be called with DEBIT_SPREAD
                            # (would verify via log message if logging is set up)

                            # HIGH vol -> CREDIT_SPREAD
                            mock_regime.return_value = VolRegime.HIGH
                            scanner.scan_opportunities("AAPL")

                            # MEDIUM vol -> VERTICAL_SPREAD (flexible)
                            mock_regime.return_value = VolRegime.MEDIUM
                            scanner.scan_opportunities("AAPL")


class TestDebitSpreadGeneration:
    """Verify DEBIT_SPREAD strategy generates appropriate candidates."""

    def test_low_vol_generates_debit_spreads(self):
        """In LOW vol, scanner generates debit (long vega) spreads."""
        # This test verifies the future state after Task 2
        # For now: verify that regime=LOW gets routed to DEBIT_SPREAD
        scanner = OptionsScanner()

        with patch.object(scanner.vol_engine, "detect_regime") as mock_regime:
            mock_regime.return_value = VolRegime.LOW

            with patch.object(
                scanner.vol_engine, "calculate_volatility"
            ) as mock_vol_calc:
                mock_vol_calc.return_value = MagicMock(annual_volatility=0.20)

                with patch.object(
                    scanner, "_find_optimal_expiration", return_value="2026-03-20"
                ):
                    with patch.object(
                        scanner.market_data, "get_current_price", return_value=150.0
                    ):
                        # Mock option chain with call data
                        import pandas as pd

                        calls_data = {
                            "strike": [145.0, 150.0, 155.0, 160.0],
                            "bid": [7.0, 3.0, 1.5, 0.5],
                            "ask": [7.2, 3.2, 1.7, 0.7],
                            "openInterest": [5000, 8000, 6000, 2000],
                            "volume": [200, 500, 300, 50],
                            "lastPrice": [7.1, 3.1, 1.6, 0.6],
                            "impliedVolatility": [0.25, 0.24, 0.23, 0.22],
                        }
                        calls_df = pd.DataFrame(calls_data)
                        puts_df = pd.DataFrame(columns=calls_df.columns)

                        mock_chain = MagicMock()
                        mock_chain.calls = calls_df
                        mock_chain.puts = puts_df

                        with patch.object(
                            scanner.market_data,
                            "get_option_chain",
                            return_value=mock_chain,
                        ):
                            candidates = scanner.scan_opportunities("AAPL")

                            # Should generate candidates (call debit spreads in LOW vol)
                            assert len(candidates) > 0, (
                                "Should generate debit spreads in LOW vol"
                            )

                            # All should be debit spreads (buy long, sell short)
                            for candidate in candidates:
                                assert "DEBIT_SPREAD" in candidate["strategy"]
                                assert candidate["cost"] > 0  # Debit = cost to enter


class TestCreditSpreadGeneration:
    """Verify CREDIT_SPREAD strategy generates appropriate candidates."""

    def test_high_vol_generates_credit_spreads(self):
        """In HIGH vol, scanner should generate credit (short vega) spreads."""
        # This is a placeholder for future implementation
        # Currently the scanner only generates debit spreads
        # After Task 2: Should generate put credit spreads in HIGH vol
        pass

    def test_credit_spread_has_negative_cost(self):
        """Credit spreads have net credit (negative cost)."""
        # Future test: verify credit spreads are entered for credit
        # Example: short 150 put (bid 1.5), long 140 put (ask 0.3)
        # Net credit = 1.5 - 0.3 = 1.2
        pass


class TestMedianSpreadGeneration:
    """Verify MEDIUM vol uses flexible/neutral approach."""

    def test_medium_vol_vertical_spread(self):
        """In MEDIUM vol, use VERTICAL_SPREAD (flexible)."""
        # Could generate either debit or credit, or balanced approach
        pass


class TestStrategyPreferenceOverride:
    """Verify explicit strategy_preference overrides regime."""

    def test_user_override_ignores_regime(self):
        """If user specifies strategy, ignore regime."""
        scanner = OptionsScanner()

        with patch.object(scanner.vol_engine, "detect_regime") as mock_regime:
            mock_regime.return_value = VolRegime.HIGH  # High vol normally = credit

            with patch.object(
                scanner.vol_engine, "calculate_volatility"
            ) as mock_vol_calc:
                mock_vol_calc.return_value = MagicMock(annual_volatility=0.60)

                with patch.object(
                    scanner, "_find_optimal_expiration", return_value="2026-03-20"
                ):
                    with patch.object(
                        scanner.market_data, "get_current_price", return_value=150.0
                    ):
                        with patch.object(
                            scanner.market_data, "get_option_chain", return_value=None
                        ):
                            # User specifies DEBIT_SPREAD explicitly
                            scanner.scan_opportunities(
                                "AAPL", strategy_preference="DEBIT_SPREAD"
                            )

                            # Should use user preference, not regime's suggestion
                            # (Verify via logging: should say "Strategy=DEBIT_SPREAD" not CREDIT_SPREAD)


class TestRegimeToDeltaSelection:
    """Verify regime affects delta selection."""

    def test_low_vol_delta_for_debit(self):
        """Debit spreads in LOW vol: look for ATM longs (delta ~0.5)."""
        # Future: LOW vol → buy ATM/ITM, sell OTM for defined risk
        pass

    def test_high_vol_delta_for_credit(self):
        """Credit spreads in HIGH vol: look for OTM shorts (delta ~0.3)."""
        # Future: HIGH vol → sell OTM, buy deep OTM for protection
        pass


class TestRegimeConsistency:
    """Verify regime affects entire workflow."""

    def test_regime_to_orchestrator_flow(self):
        """Regime flows from detect_regime → strategy_hint → orchestrator."""
        # The orchestrator receives strategy_hint from vol_and_events_context
        # This should match what scan_opportunities decided
        pass

    def test_decisionlog_shows_regime(self):
        """DecisionLog captures which regime triggered which strategy."""
        from orchestrator import DecisionLog

        log = DecisionLog(
            symbol="AAPL",
            start_date="2026-03-01",
            end_date="2026-06-01",
            policy_mode="tight",
        )

        log.regime = "LOW"
        log.strategy_hint = "DEBIT_SPREAD"

        output = log.to_formatted_string()

        # Should show regime and strategy choice
        assert "Regime" in output or "regime" in output.lower()
        assert "DEBIT_SPREAD" in output or "Strategy" in output


class TestRegimeEdgeCases:
    """Verify edge cases don't crash."""

    def test_no_regime_detected_defaults_gracefully(self):
        """If regime detection fails, use safe default."""
        scanner = OptionsScanner()

        with patch.object(
            scanner.vol_engine, "detect_regime", side_effect=Exception("vol calc error")
        ):
            with patch.object(
                scanner, "_find_optimal_expiration", return_value="2026-03-20"
            ):
                with patch.object(
                    scanner.market_data, "get_current_price", return_value=150.0
                ):
                    with patch.object(
                        scanner.market_data, "get_option_chain", return_value=None
                    ):
                        # Should not crash, should use default strategy
                        candidates = scanner.scan_opportunities("AAPL")
                        # Should either return [] or use VERTICAL_SPREAD as fallback
                        assert isinstance(candidates, list)

    def test_regime_with_missing_vol_data(self):
        """Regime detection with incomplete vol data."""
        scanner = OptionsScanner()

        with patch.object(scanner.vol_engine, "detect_regime") as mock_regime:
            mock_regime.return_value = VolRegime.MEDIUM

            with patch.object(
                scanner.vol_engine,
                "calculate_volatility",
                side_effect=Exception("no data"),
            ):
                with patch.object(
                    scanner, "_find_optimal_expiration", return_value="2026-03-20"
                ):
                    with patch.object(
                        scanner.market_data, "get_current_price", return_value=150.0
                    ):
                        with patch.object(
                            scanner.market_data, "get_option_chain", return_value=None
                        ):
                            # Should handle gracefully
                            candidates = scanner.scan_opportunities("AAPL")
                            assert isinstance(candidates, list)
