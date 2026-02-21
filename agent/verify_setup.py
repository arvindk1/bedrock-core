"""
Pipeline Verification Script
============================
Tests the integration of the "Hedge Fund Grade" modules:
1. Event Loader (Context)
2. Volatility Engine (Regime)
3. Options Scanner (Strategy Selection)
4. Market Checks (Gatekeeper Validation)
"""

import asyncio
import logging
import sys

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("PipelineVerifier")

from agent.event_loader import event_loader
from agent.vol_engine import AdvancedVolatilityCalculator, VolatilityModel
from agent.options_scanner import options_scanner
from agent.market_checks import gatekeeper


async def run_verification():
    logger.info("🚀 Starting Hedge Fund Grade Pipeline Verification")

    symbols = ["MSFT", "NVDA", "SPY", "TSLA"]

    for symbol in symbols:
        logger.info(f"\n--- Analyzing {symbol} ---")

        # 1. Event Check
        # ---------------------------------------------------------
        logger.info("1. Checking Events...")
        earnings = event_loader.check_earnings_before_expiry(symbol, days_to_expiry=45)
        if earnings:
            logger.warning(
                f"⚠️  Earnings Warning: {earnings['warning']} on {earnings['earnings_date']}"
            )
        else:
            logger.info("✅ No conflicting earnings events found.")

        # 2. Volatility Regime
        # ---------------------------------------------------------
        logger.info("2. Analyzing Volatility Regime...")
        vol_calc = AdvancedVolatilityCalculator()
        vol_res = await vol_calc.calculate_volatility(
            symbol, model=VolatilityModel.HYBRID
        )

        logger.info(f"📊 Annual Vol: {vol_res.annual_volatility:.1%}")
        logger.info(f"📊 Confidence: {vol_res.confidence_score:.2f}")

        # 3. Scan for Opportunities
        # ---------------------------------------------------------
        logger.info("3. Scanning for Opportunities...")
        opportunities = await options_scanner.scan_opportunities(symbol)

        if not opportunities:
            logger.info(f"ℹ️  No opportunities found for {symbol} matching criteria.")
            continue

        logger.info(f"✅ Found {len(opportunities)} potential setups.")

        # 4. Gatekeeper Validation
        # ---------------------------------------------------------
        logger.info("4. Running Scored Gatekeeper...")

        for trade in opportunities[:2]:  # Check top 2
            logger.info(f"   Testing: {trade['description']}")

            # Construct proposal for gatekeeper
            proposal = {
                "symbol": symbol,
                "strategy_type": trade["strategy"],
                "expiration_date": trade["expiration"],
                "max_loss": 500.0,  # Mock
                "quantity": 1,
            }

            score_card = await gatekeeper.check_trade(proposal)

            if score_card.is_approved:
                logger.info(f"   ✅ APPROVED (Score: {score_card.total_score:.1f})")
            else:
                logger.info(
                    f"   ❌ REJECTED (Score: {score_card.total_score:.1f}) - {score_card.rejection_reason}"
                )

            if score_card.warnings:
                logger.info(f"      Warnings: {', '.join(score_card.warnings)}")

    logger.info("\n🏁 Verification Complete")


if __name__ == "__main__":
    asyncio.run(run_verification())
