"""Tests for pipeline journey enrichment on final picks."""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "agent"))

from agent.orchestrator import _build_pipeline_journey, _build_strategy_reasoning


def test_pipeline_journey_all_pass():
    pick = {
        "symbol": "AAPL",
        "strategy": "BULL_CALL_SPREAD",
        "max_loss": 480,
        "gatekeeper_score": 87,
    }
    log_context = {
        "regime": "MED",
        "regime_details": {"iv_rank": 0.45, "annual_vol": 0.307},
        "blocking_events": [],
        "event_policy": "PLAY",
        "max_risk": 1000,
        "max_sector_pct": 0.25,
        "max_correlation": 0.70,
        "gatekeeper_threshold": 70,
        "max_corr_seen": 0.42,
        "sector": "Technology",
        "sector_pct": 0.22,
    }
    pipeline = _build_pipeline_journey(pick, log_context)

    assert pipeline["volatility"]["status"] == "pass"
    assert pipeline["event"]["status"] == "pass"
    assert pipeline["risk"]["status"] == "pass"
    assert pipeline["gatekeeper"]["status"] == "pass"
    assert pipeline["correlation"]["status"] == "pass"

    # Structured fields must be present
    assert "code" in pipeline["risk"]
    assert "metrics" in pipeline["risk"]
    assert "display" in pipeline["risk"]
    assert pipeline["risk"]["metrics"]["max_loss"] == 480
    assert pipeline["gatekeeper"]["metrics"]["score"] == 87


def test_pipeline_journey_display_strings_are_non_empty():
    pick = {
        "symbol": "AAPL",
        "strategy": "BULL_CALL_SPREAD",
        "max_loss": 480,
        "gatekeeper_score": 87,
    }
    log_context = {
        "regime": "HIGH",
        "regime_details": {"iv_rank": 0.78, "annual_vol": 0.45},
        "blocking_events": [],
        "event_policy": "PLAY",
        "max_risk": 1000,
        "max_sector_pct": 0.25,
        "max_correlation": 0.70,
        "gatekeeper_threshold": 70,
        "max_corr_seen": 0.42,
        "sector": "Technology",
        "sector_pct": 0.22,
    }
    pipeline = _build_pipeline_journey(pick, log_context)
    for stage_name, stage in pipeline.items():
        assert stage["display"], f"Stage {stage_name} has empty display string"


def test_strategy_reasoning_high_vol():
    reasoning = _build_strategy_reasoning(
        strategy_hint="CREDIT_SPREAD",
        regime="HIGH",
        iv_rank=0.78,
        spy_trend="UPTREND",
        policy_mode="tight",
    )
    assert reasoning["chosen"] == "CREDIT_SPREAD"
    assert reasoning["drivers"]["regime"] == "HIGH"
    assert reasoning["drivers"]["iv_rank"] == 78  # converted to 0-100
    assert "display" in reasoning
    assert len(reasoning["display"]) > 10


def test_strategy_reasoning_low_vol():
    reasoning = _build_strategy_reasoning(
        strategy_hint="DEBIT_SPREAD",
        regime="LOW",
        iv_rank=0.22,
        spy_trend="DOWNTREND",
        policy_mode="moderate",
    )
    assert reasoning["chosen"] == "DEBIT_SPREAD"
    assert reasoning["drivers"]["regime"] == "LOW"
