"""Tests for scan API response enrichment helpers."""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "agent"))


def test_scan_response_includes_display_reason_in_rejections():
    """Each rejection should have display_reason and severity added."""
    from ui.server import _enrich_rejections

    raw = [
        {
            "candidate": {"symbol": "AAPL", "strategy": "BULL_CALL_SPREAD"},
            "reason": "RISK_REJECT|rule=SECTOR_CAP|sector=Technology|used_pct=100|limit_pct=25",
        }
    ]
    enriched = _enrich_rejections(raw)
    assert "display_reason" in enriched[0]
    assert "severity" in enriched[0]
    assert enriched[0]["severity"] == "critical"
    assert "Technology" in enriched[0]["display_reason"]


def test_scan_response_includes_display_reason_for_unstructured():
    """Unstructured reasons should still get a display_reason."""
    from ui.server import _enrich_rejections

    raw = [{"candidate": {"symbol": "X"}, "reason": "rejected for some reason"}]
    enriched = _enrich_rejections(raw)
    assert "display_reason" in enriched[0]
    assert enriched[0]["display_reason"] == "rejected for some reason"
    assert "severity" in enriched[0]


def test_severity_mapping():
    from ui.server import _severity_for_rule

    assert _severity_for_rule("SECTOR_CAP") == "critical"
    assert _severity_for_rule("MAX_LOSS_EXCEEDED") == "critical"
    assert _severity_for_rule("DRAWDOWN_HALT") == "critical"
    assert _severity_for_rule("LIQUIDITY") == "warning"
    assert _severity_for_rule("SPREAD_TOO_WIDE") == "warning"
    assert _severity_for_rule("LOW_SCORE") == "info"
    assert _severity_for_rule("CORRELATION_BREACH") == "warning"
    assert _severity_for_rule("EARNINGS") == "critical"
    assert _severity_for_rule("UNKNOWN_RULE") == "info"


def test_enrich_rejections_preserves_existing_fields():
    """_enrich_rejections must not drop existing fields."""
    from ui.server import _enrich_rejections

    raw = [
        {
            "candidate": {"symbol": "AAPL"},
            "reason": "RISK_REJECT|rule=MAX_LOSS_EXCEEDED|proposed=1500|limit=1000",
            "score": 65.0,
        }
    ]
    enriched = _enrich_rejections(raw)
    assert enriched[0]["score"] == 65.0
    assert "display_reason" in enriched[0]
