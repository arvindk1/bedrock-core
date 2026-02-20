# Decision Intelligence UI Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Surface backend decision intelligence (per-trade pipeline journey, "why no trades" explanation, human-readable rejection reasons) in the frontend UI.

**Architecture:** Backend enriches scan response with structured `pipeline`, `strategy_reasoning`, `noTradesExplanation`, and `display_reason`/`severity` fields. Frontend renders them — no client-side inference. Three files change: `agent/orchestrator.py` (builds pipeline data), `ui/server.py` (shapes API response), `ui/app.js` (renders new UI components).

**Tech Stack:** Python (orchestrator, server), FastAPI, vanilla JS (frontend), existing `reason_codes.py` helpers (`extract_reason_summary`, `parse_reason_code`, `is_structured_reason`).

---

## Task 1: Backend — Pipeline Journey per Final Pick

**Files:**
- Modify: `agent/orchestrator.py` (add helper + call in `full_scan_with_orchestration`)
- Test: `tests/test_orchestrator_pipeline.py` (new file)

**Context:**
`full_scan_with_orchestration()` in `orchestrator.py` returns a `DecisionLog`. The `final_picks` list contains dicts. We need to enrich each pick with a `pipeline` field and `strategy_reasoning` field before returning `log`.

The orchestrator already has all the data in scope:
- `log.regime`, `log.regime_details` — for volatility stage
- `log.blocking_events`, `log.event_policy` — for event stage
- Each pick passed risk gate (so risk = pass; rejection details are in `log.rejections_risk`)
- `pick["gatekeeper_score"]` — already set on passing picks
- `log.candidates_after_correlation` — all passed correlation
- `log.strategy_hint` — e.g. "CREDIT_SPREAD"

**Step 1: Write the failing test**

Create `tests/test_orchestrator_pipeline.py`:

```python
"""Tests for pipeline journey enrichment on final picks."""
import pytest
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
    pick = {"symbol": "AAPL", "strategy": "BULL_CALL_SPREAD", "max_loss": 480, "gatekeeper_score": 87}
    log_context = {
        "regime": "HIGH", "regime_details": {"iv_rank": 0.78, "annual_vol": 0.45},
        "blocking_events": [], "event_policy": "PLAY",
        "max_risk": 1000, "max_sector_pct": 0.25, "max_correlation": 0.70,
        "gatekeeper_threshold": 70, "max_corr_seen": 0.42,
        "sector": "Technology", "sector_pct": 0.22,
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
```

**Step 2: Run test to verify it fails**

```bash
cd /home/arvindk/devl/aws/bedrock-core
source .venv/bin/activate
python -m pytest tests/test_orchestrator_pipeline.py -v
```

Expected: `ImportError` or `AttributeError` — `_build_pipeline_journey` doesn't exist yet.

**Step 3: Implement helpers in `agent/orchestrator.py`**

Add these two functions BEFORE `full_scan_with_orchestration`. Insert after the `format_event_for_display` function (around line 87):

```python
def _build_pipeline_journey(pick: Dict[str, Any], log_context: Dict[str, Any]) -> Dict[str, Any]:
    """
    Build structured pipeline journey for a final pick.

    All picks passed every gate (otherwise they wouldn't be final picks).
    log_context provides the metrics for each stage.
    """
    regime = log_context.get("regime", "UNKNOWN")
    regime_details = log_context.get("regime_details", {})
    blocking_events = log_context.get("blocking_events", [])
    event_policy = log_context.get("event_policy", "PLAY")
    max_risk = log_context.get("max_risk", 1000)
    max_sector_pct = log_context.get("max_sector_pct", 0.25)
    max_correlation = log_context.get("max_correlation", 0.70)
    gatekeeper_threshold = log_context.get("gatekeeper_threshold", 70)
    max_corr_seen = log_context.get("max_corr_seen", 0.0)
    sector = log_context.get("sector", "Unknown")
    sector_pct = log_context.get("sector_pct", 0.0)

    iv_rank = regime_details.get("iv_rank", 0) if isinstance(regime_details, dict) else 0
    if iv_rank and iv_rank <= 1.0:
        iv_rank_display = round(iv_rank * 100)
    else:
        iv_rank_display = round(iv_rank) if iv_rank else 0

    annual_vol = regime_details.get("annual_vol", 0) if isinstance(regime_details, dict) else 0
    max_loss = pick.get("max_loss", 0)
    gk_score = pick.get("gatekeeper_score", 0)

    return {
        "volatility": {
            "status": "pass",
            "code": f"{regime}_REGIME",
            "metrics": {
                "regime": regime,
                "iv_rank": iv_rank_display,
                "annual_vol": round(annual_vol * 100, 1) if annual_vol else None,
            },
            "display": (
                f"{regime} vol regime, IV rank {iv_rank_display}% — "
                f"{'credit spreads preferred' if regime == 'HIGH' else 'debit spreads preferred' if regime == 'LOW' else 'vertical spreads preferred'}"
            ),
        },
        "event": {
            "status": "pass",
            "code": "NO_EVENTS" if not blocking_events else f"POLICY_{event_policy}",
            "metrics": {
                "blocking_count": len(blocking_events),
                "policy": event_policy,
            },
            "display": (
                "No blocking events — trading permitted"
                if not blocking_events
                else f"{len(blocking_events)} event(s) nearby, policy {event_policy} — trading with haircuts"
            ),
        },
        "risk": {
            "status": "pass",
            "code": "WITHIN_LIMITS",
            "metrics": {
                "max_loss": max_loss,
                "limit": max_risk,
                "sector": sector,
                "sector_pct": round(sector_pct * 100),
                "sector_limit_pct": round(max_sector_pct * 100),
            },
            "display": (
                f"Max loss ${max_loss:.0f} within ${max_risk:.0f} limit, "
                f"{sector} sector at {sector_pct * 100:.0f}% (limit {max_sector_pct * 100:.0f}%)"
            ),
        },
        "gatekeeper": {
            "status": "pass",
            "code": "APPROVED",
            "metrics": {
                "score": round(gk_score, 1),
                "threshold": gatekeeper_threshold,
            },
            "display": f"Score {gk_score:.0f}/100 above threshold {gatekeeper_threshold}",
        },
        "correlation": {
            "status": "pass",
            "code": "DIVERSIFIED",
            "metrics": {
                "max_corr": round(max_corr_seen, 2),
                "threshold": max_correlation,
            },
            "display": (
                f"Max correlation {max_corr_seen:.2f} — well diversified (threshold {max_correlation:.2f})"
                if max_corr_seen < max_correlation
                else f"Max correlation {max_corr_seen:.2f} within threshold {max_correlation:.2f}"
            ),
        },
    }


def _build_strategy_reasoning(
    strategy_hint: str,
    regime: Optional[str],
    iv_rank: Optional[float],
    spy_trend: Optional[str],
    policy_mode: str,
) -> Dict[str, Any]:
    """Build strategy reasoning object for a final pick."""
    iv_display = 0
    if iv_rank is not None:
        iv_display = round(iv_rank * 100) if iv_rank <= 1.0 else round(iv_rank)

    strategy_display_map = {
        "CREDIT_SPREAD": "credit spreads",
        "DEBIT_SPREAD": "debit spreads",
        "VERTICAL_SPREAD": "vertical spreads",
    }
    strategy_label = strategy_display_map.get(strategy_hint, strategy_hint.replace("_", " ").lower())

    regime_label = (regime or "UNKNOWN").upper()
    policy_label = policy_mode.title()

    display = (
        f"IV Rank {iv_display}% ({regime_label} vol) with {policy_label} policy "
        f"→ prefer {strategy_label}"
    )

    return {
        "chosen": strategy_hint,
        "drivers": {
            "regime": regime_label,
            "iv_rank": iv_display,
            "trend": (spy_trend or "UNKNOWN").upper(),
            "policy": policy_mode.upper(),
        },
        "display": display,
    }


def _build_no_trades_explanation(log: "DecisionLog", policy_mode: str, max_risk: float) -> Dict[str, Any]:
    """
    Build structured 'why no trades' explanation when final_picks is empty.
    Ranked by primary blocker.
    """
    gate_counts = {
        "generated": len(log.candidates_raw),
        "after_event": len(log.candidates_raw) if log.event_policy != "TIGHT" else 0,
        "after_risk": len(log.candidates_after_risk_gate),
        "after_gatekeeper": len([
            c for c in log.candidates_after_risk_gate
            if not any(
                r.get("candidate", {}).get("symbol") == c.get("symbol") and
                r.get("candidate", {}).get("strategy") == c.get("strategy")
                for r in log.rejections_gatekeeper
            )
        ]),
        "after_correlation": len(log.candidates_after_correlation),
        "final": 0,
    }

    top_blockers = []
    next_actions = []
    summary = "No picks generated"

    if log.event_policy == "TIGHT" and log.blocking_events:
        evt = log.blocking_events[0]
        top_blockers.append({
            "gate": "event",
            "code": "EVENT_TIGHT",
            "count": len(log.candidates_raw),
            "display": f"Event within 1 day — no new trades permitted: {format_event_for_display(evt)}",
        })
        next_actions = [
            "Wait for event to pass",
            "Monitor positions already held",
            "Re-scan after event clears",
        ]
        summary = f"0 picks: Event in tight window ({format_event_for_display(evt)})"

    elif log.rejections_risk:
        # Find most common rejection rule
        from reason_codes import parse_reason_code, is_structured_reason
        rule_counts: Dict[str, int] = {}
        for candidate, reason in log.rejections_risk:
            if is_structured_reason(reason):
                parsed = parse_reason_code(reason)
                rule = parsed.get("rule", "UNKNOWN")
            else:
                rule = reason.split("|")[0] if "|" in reason else reason
            rule_counts[rule] = rule_counts.get(rule, 0) + 1

        top_rule = max(rule_counts, key=lambda r: rule_counts[r])
        count = rule_counts[top_rule]

        if top_rule == "SECTOR_CAP":
            # Extract sector from first matching rejection
            sector_name = "Unknown"
            for candidate, reason in log.rejections_risk:
                if is_structured_reason(reason):
                    parsed = parse_reason_code(reason)
                    if parsed.get("rule") == "SECTOR_CAP":
                        ctx = parsed.get("context", {})
                        sector_name = ctx.get("sector", "Unknown")
                        used_pct = ctx.get("used_pct", "?")
                        limit_pct = ctx.get("limit_pct", 25)
                        break
            top_blockers.append({
                "gate": "risk",
                "code": "SECTOR_CAP",
                "count": count,
                "display": f"{sector_name} sector at {used_pct}% (limit {limit_pct}%) — {count} candidates blocked",
            })
            next_actions = [
                f"Reduce {sector_name} sector exposure below {limit_pct}%",
                "Expand scan to symbols in other sectors",
                f"Switch policy from {policy_mode.title()} → Moderate if risk tolerance allows",
            ]
            summary = f"0 picks: {count}/{len(log.candidates_raw)} rejected at Risk Gate (sector cap)"

        elif top_rule == "MAX_LOSS_EXCEEDED":
            top_blockers.append({
                "gate": "risk",
                "code": "MAX_LOSS_EXCEEDED",
                "count": count,
                "display": f"Max loss exceeds ${max_risk:.0f} limit — {count} candidates blocked",
            })
            next_actions = [
                f"Switch policy from Tight → Moderate to raise risk limit",
                "Scan for tighter spreads with lower max loss",
            ]
            summary = f"0 picks: {count}/{len(log.candidates_raw)} exceeded ${max_risk:.0f} max loss limit"

        else:
            top_blockers.append({
                "gate": "risk",
                "code": top_rule,
                "count": count,
                "display": f"Risk gate ({top_rule.replace('_', ' ').title()}) rejected {count} candidates",
            })
            next_actions = ["Review risk parameters", "Expand scan date range"]
            summary = f"0 picks: {count}/{len(log.candidates_raw)} rejected at Risk Gate"

    elif log.rejections_gatekeeper:
        count = len(log.rejections_gatekeeper)
        top_blockers.append({
            "gate": "gatekeeper",
            "code": "LOW_SCORE",
            "count": count,
            "display": f"Gatekeeper score below threshold 70 — {count} candidates blocked",
        })
        next_actions = [
            "Scan for more liquid options (tighter spreads)",
            "Expand date range to capture higher-quality expirations",
        ]
        summary = f"0 picks: {count} rejected by Gatekeeper (score below 70)"

    elif log.rejections_correlation:
        count = len(log.rejections_correlation)
        top_blockers.append({
            "gate": "correlation",
            "code": "CORRELATION_BREACH",
            "count": count,
            "display": f"Portfolio correlation too high — {count} candidates blocked",
        })
        next_actions = [
            "Close or reduce correlated positions before adding new trades",
            "Scan symbols in different sectors",
        ]
        summary = f"0 picks: {count} rejected by Correlation Gate (too correlated with existing portfolio)"

    elif not log.candidates_raw:
        top_blockers.append({
            "gate": "generated",
            "code": "NO_CANDIDATES",
            "count": 0,
            "display": "No option candidates found in the specified date window",
        })
        next_actions = [
            "Expand date range (start_date / end_date)",
            "Verify symbol has liquid options",
        ]
        summary = "0 picks: No candidates generated in date window"

    return {
        "summary": summary,
        "top_blockers": top_blockers,
        "gate_counts": gate_counts,
        "next_actions": next_actions,
    }
```

**Step 4: Wire into `full_scan_with_orchestration`**

In `full_scan_with_orchestration`, just before `return log` at line 526, add:

```python
        # Build pipeline journey for each final pick
        from risk_engine import SECTOR_MAP
        # Estimate max_corr_seen from correlation rejections (0 if none)
        max_corr_seen = 0.0
        for rej_candidate, rej_reason in log.rejections_correlation:
            from reason_codes import parse_reason_code, is_structured_reason
            if is_structured_reason(rej_reason):
                parsed = parse_reason_code(rej_reason)
                corr_val = parsed.get("context", {}).get("corr", 0.0)
                if isinstance(corr_val, (int, float)):
                    max_corr_seen = max(max_corr_seen, float(corr_val))

        spy_trend = context.get("vol_details", {}).get("spy_trend") if isinstance(context.get("vol_details"), dict) else None

        iv_rank_raw = None
        if isinstance(log.regime_details, dict):
            iv_rank_raw = log.regime_details.get("iv_rank")
        elif hasattr(log.regime_details, "iv_rank"):
            iv_rank_raw = log.regime_details.iv_rank

        log_context_for_pipeline = {
            "regime": log.regime,
            "regime_details": log.regime_details if isinstance(log.regime_details, dict) else {},
            "blocking_events": log.blocking_events,
            "event_policy": log.event_policy,
            "max_risk": max_risk,
            "max_sector_pct": 0.25,
            "max_correlation": 0.70,
            "gatekeeper_threshold": 70,
            "max_corr_seen": max_corr_seen,
            "sector": SECTOR_MAP.get(symbol, "Unknown"),
            "sector_pct": 0.0,  # approximation — sector pct passed (at/near limit)
        }

        strategy_reasoning = _build_strategy_reasoning(
            strategy_hint=log.strategy_hint or "VERTICAL_SPREAD",
            regime=log.regime,
            iv_rank=iv_rank_raw,
            spy_trend=spy_trend,
            policy_mode=policy_mode,
        )

        for pick in log.final_picks:
            pick["pipeline"] = _build_pipeline_journey(pick, log_context_for_pipeline)
            pick["strategy_reasoning"] = strategy_reasoning
```

Also add at end of try block when `final_picks` is empty:

After the existing `log.final_picks = []` lines, add:

```python
        # Build no-trades explanation (only when needed)
        if not log.final_picks:
            log.no_trades_explanation = _build_no_trades_explanation(log, policy_mode, max_risk)
        else:
            log.no_trades_explanation = None
```

Also add `no_trades_explanation: Optional[Dict[str, Any]] = None` to `DecisionLog` dataclass fields.

**Step 5: Run tests to verify pass**

```bash
cd /home/arvindk/devl/aws/bedrock-core
source .venv/bin/activate
python -m pytest tests/test_orchestrator_pipeline.py -v
```

Expected: All 4 tests PASS.

**Step 6: Commit**

```bash
git add agent/orchestrator.py tests/test_orchestrator_pipeline.py
git commit -m "feat: enrich final picks with pipeline journey and strategy reasoning"
```

---

## Task 2: Backend — No-Trades Explanation + Display Reasons in API Response

**Files:**
- Modify: `ui/server.py` (scan endpoint response, lines ~165-203)
- Test: `tests/test_server_scan_response.py` (new file)

**Context:**
`server.py` `/api/scan` endpoint calls `full_scan_with_orchestration()` and maps `log.to_dict()` to the response. We need to:
1. Add `noTradesExplanation` from `log.no_trades_explanation` (when picks = 0)
2. Add `display_reason` + `severity` to each rejection in the `rejections` dict
3. Pass through `pipeline` + `strategy_reasoning` fields from picks (they're already in `log_dict["final_picks"]`)

**Step 1: Write the failing test**

Create `tests/test_server_scan_response.py`:

```python
"""Tests for scan API response enrichment."""
import pytest
from unittest.mock import patch, MagicMock


def _make_mock_log_dict(n_picks=0, n_risk_rej=3):
    """Build a minimal log_dict as returned by log.to_dict()."""
    picks = []
    if n_picks > 0:
        picks = [{
            "symbol": "AAPL",
            "strategy": "BULL_CALL_SPREAD",
            "max_loss": 480,
            "gatekeeper_score": 87,
            "pipeline": {
                "risk": {"status": "pass", "code": "WITHIN_LIMITS", "metrics": {}, "display": "ok"},
            },
            "strategy_reasoning": {"chosen": "CREDIT_SPREAD", "drivers": {}, "display": "test"},
        }]
    risk_rejs = [
        {
            "candidate": {"symbol": "AAPL", "strategy": "BULL_CALL_SPREAD"},
            "reason": "RISK_REJECT|rule=SECTOR_CAP|sector=Technology|used_pct=100|limit_pct=25",
        }
        for _ in range(n_risk_rej)
    ]
    return {
        "regime": "HIGH",
        "spy_trend": "UPTREND",
        "macro_risk": "None",
        "blocking_events": [],
        "total_generated": 3,
        "after_event_filter": 3,
        "after_risk_gate": 0,
        "after_gatekeeper": 0,
        "after_correlation": 0,
        "final_picks": picks,
        "risk_rejections": risk_rejs,
        "gatekeeper_rejections": [],
        "correlation_rejections": [],
        "blocking_events_str": "None",
        "regime_details": {"iv_rank": 0.78, "annual_vol": 0.45},
        "strategy_hint": "CREDIT_SPREAD",
        "timestamp": "2026-02-19T00:00:00",
    }


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
    assert _severity_for_rule("UNKNOWN_RULE") == "info"  # safe default
```

**Step 2: Run test to verify it fails**

```bash
python -m pytest tests/test_server_scan_response.py -v
```

Expected: `ImportError` — `_enrich_rejections` and `_severity_for_rule` don't exist.

**Step 3: Add helpers to `ui/server.py`**

Add these functions after the imports (before the route definitions, around line 48):

```python
# --- Scan Response Enrichment Helpers ---

def _severity_for_rule(rule: str) -> str:
    """Map a rejection rule code to a UI severity level."""
    critical_rules = {"SECTOR_CAP", "MAX_LOSS_EXCEEDED", "DRAWDOWN_HALT", "EARNINGS", "FOMC", "CPI", "JOBS_REPORT", "EVENT_TIGHT"}
    warning_rules = {"LIQUIDITY", "SPREAD_TOO_WIDE", "CORRELATION_BREACH", "IV_PENALTY"}
    info_rules = {"LOW_SCORE", "NO_MAX_LOSS"}
    if rule in critical_rules:
        return "critical"
    if rule in warning_rules:
        return "warning"
    if rule in info_rules:
        return "info"
    return "info"  # safe default


def _enrich_rejections(rejections: list) -> list:
    """
    Add display_reason and severity to each rejection dict.
    Works for any rejection list (risk, gatekeeper, correlation).
    """
    import sys, os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "agent"))
    from reason_codes import extract_reason_summary, parse_reason_code, is_structured_reason

    enriched = []
    for rej in rejections:
        r = dict(rej)
        reason = r.get("reason", "")
        if is_structured_reason(reason):
            r["display_reason"] = extract_reason_summary(reason)
            parsed = parse_reason_code(reason)
            rule = parsed.get("rule", "UNKNOWN")
            r["severity"] = _severity_for_rule(rule)
        else:
            r["display_reason"] = reason or "Unknown"
            r["severity"] = "info"
        enriched.append(r)
    return enriched
```

**Step 4: Update the `/api/scan` response in `server.py`**

In the `scan()` function, update the return dict to:
1. Enrich rejections with `_enrich_rejections`
2. Add `noTradesExplanation`
3. Picks already contain `pipeline` and `strategy_reasoning` (passed through from `log_dict`)

Find the `return {` block (around line 165) and update:

```python
        # Enrich rejections with display_reason + severity
        risk_rejs_enriched = _enrich_rejections(log_dict.get("risk_rejections", []))
        gk_rejs_enriched = _enrich_rejections(log_dict.get("gatekeeper_rejections", []))
        corr_rejs_enriched = _enrich_rejections(log_dict.get("correlation_rejections", []))

        # No-trades explanation (from orchestrator)
        no_trades_explanation = None
        if hasattr(decision_log, 'no_trades_explanation') and decision_log.no_trades_explanation:
            no_trades_explanation = decision_log.no_trades_explanation

        return {
            "regime": log_dict.get("regime", "HIGH"),
            "spyTrend": log_dict.get("spy_trend", "Uptrend"),
            "macroRisk": log_dict.get("macro_risk", "No macro events"),
            "policyMode": f"{req.policy_mode.title()} (${policy_amount})",
            "blockingEvents": log_dict.get("blocking_events", []),
            "gateFunnel": {
                "generated": log_dict.get("total_generated", 0),
                "afterEvent": log_dict.get("after_event_filter", 0),
                "afterRisk": log_dict.get("after_risk_gate", 0),
                "afterGatekeeper": log_dict.get("after_gatekeeper", 0),
                "afterCorrelation": log_dict.get("after_correlation", 0),
                "final": len(log_dict.get("final_picks", [])),
            },
            "picks": log_dict.get("final_picks", []),
            "rejections": {
                "risk": risk_rejs_enriched,
                "gatekeeper": gk_rejs_enriched,
                "event": [],
                "correlation": corr_rejs_enriched,
            },
            "noTradesExplanation": no_trades_explanation,
            "volatilityContext": {
                "annual_vol": log_dict.get("regime_details", {}).get("annual_vol"),
                "daily_vol": log_dict.get("regime_details", {}).get("daily_vol"),
                "iv_rank": log_dict.get("regime_details", {}).get("iv_rank"),
                "expected_move_30d": log_dict.get("regime_details", {}).get("expected_move"),
            },
            "decisionLog": {
                "regime": log_dict.get("regime", "HIGH"),
                "strategyHint": log_dict.get("strategy_hint", "CREDIT_SPREAD"),
                "blockingEvents": log_dict.get("blocking_events_str", "None"),
                "generated": log_dict.get("total_generated", 0),
                "riskPassed": log_dict.get("after_risk_gate", 0),
                "gatekeeperPassed": log_dict.get("after_gatekeeper", 0),
                "correlationPassed": log_dict.get("after_correlation", 0),
                "finalPicks": len(log_dict.get("final_picks", [])),
                "timestamp": log_dict.get("timestamp", datetime.now().isoformat()),
            },
        }
```

**Step 5: Run tests**

```bash
python -m pytest tests/test_server_scan_response.py -v
```

Expected: All 4 tests PASS.

**Step 6: Commit**

```bash
git add ui/server.py tests/test_server_scan_response.py
git commit -m "feat: add display_reason, severity, and noTradesExplanation to scan API response"
```

---

## Task 3: Frontend — Pipeline Journey Panel in Trade Cards

**Files:**
- Modify: `ui/app.js` (functions `renderTradeCards`, add `renderPipelineJourney`)
- Test: Manual browser test (no test runner for vanilla JS in this project)

**Context:**
`renderTradeCards()` in `app.js` (line 443) builds `hd-trade-card` HTML. Currently the expanded body has two panels: "Leg Structure" and "Trade Summary". We add a third panel: "Pipeline Journey".

The `pick` object now contains `pick.pipeline` (5-stage dict) and `pick.strategy_reasoning`.

**Step 1: Add `renderPipelineJourney` function to `app.js`**

Add this function after `toggleTradeCard` (around line 554):

```javascript
// ============================================================================
// PIPELINE JOURNEY RENDERER
// ============================================================================

function renderPipelineJourney(pipeline, strategyReasoning) {
    if (!pipeline) {
        return '<p style="color:var(--color-text-muted); font-size:0.78rem; font-family:var(--font-mono);">Pipeline data not available</p>';
    }

    const stageOrder = ['volatility', 'event', 'risk', 'gatekeeper', 'correlation'];
    const stageLabels = {
        volatility: 'Volatility',
        event: 'Event Check',
        risk: 'Risk Gate',
        gatekeeper: 'Gatekeeper',
        correlation: 'Correlation',
    };

    const stageIcons = {
        pass: `<svg style="width:14px;height:14px;stroke:var(--accent-green-lt);fill:none;stroke-width:2.5;flex-shrink:0;" viewBox="0 0 24 24"><polyline points="20 6 9 17 4 12"/></svg>`,
        fail: `<svg style="width:14px;height:14px;stroke:var(--accent-red);fill:none;stroke-width:2.5;flex-shrink:0;" viewBox="0 0 24 24"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>`,
        skip: `<svg style="width:14px;height:14px;stroke:var(--color-text-muted);fill:none;stroke-width:2;flex-shrink:0;" viewBox="0 0 24 24"><line x1="5" y1="12" x2="19" y2="12"/></svg>`,
    };

    const stagesHtml = stageOrder.map(key => {
        const stage = pipeline[key];
        if (!stage) return '';
        const status = stage.status || 'skip';
        const icon = stageIcons[status] || stageIcons.skip;
        const label = stageLabels[key] || key;
        const display = stage.display || '—';
        const labelColor = status === 'pass' ? 'var(--color-text-primary)' : status === 'fail' ? 'var(--accent-red)' : 'var(--color-text-muted)';

        return `
        <div style="display:flex; align-items:flex-start; gap:10px; padding:6px 0; border-bottom:1px solid var(--color-border-subtle);">
            <div style="margin-top:2px;">${icon}</div>
            <div style="flex:1; min-width:0;">
                <span style="font-family:var(--font-mono); font-size:0.65rem; font-weight:700; text-transform:uppercase; letter-spacing:0.1em; color:${labelColor};">${label}</span>
                <p style="margin:2px 0 0; font-family:var(--font-mono); font-size:0.72rem; color:var(--color-text-muted); line-height:1.4;">${display}</p>
            </div>
        </div>`;
    }).join('');

    const reasoningHtml = strategyReasoning
        ? `<div style="margin-top:12px; padding:8px; background:var(--accent-indigo-dim); border-radius:4px; border-left:2px solid var(--accent-indigo);">
            <span style="font-family:var(--font-mono); font-size:0.6rem; font-weight:700; text-transform:uppercase; letter-spacing:0.12em; color:var(--accent-indigo-hover); display:block; margin-bottom:3px;">Strategy Reasoning</span>
            <span style="font-family:var(--font-mono); font-size:0.72rem; color:var(--color-text-secondary);">${strategyReasoning.display || '—'}</span>
          </div>`
        : '';

    return `${stagesHtml}${reasoningHtml}`;
}
```

**Step 2: Update `renderTradeCards` to include pipeline panel**

Find the `hd-trade-card-body` section in `renderTradeCards` (around line 517). Replace the inner div from:

```javascript
            <div class="hd-trade-card-body">
                <div>
                    <p style="...">Leg Structure</p>
                    ${legsHtml}
                </div>
                <div>
                    <p style="...">Trade Summary</p>
                    ...
                </div>
            </div>
```

To (add a third column):

```javascript
            <div class="hd-trade-card-body" style="grid-template-columns: 1fr 1fr 1fr;">
                <div>
                    <p style="font-size:0.6rem; text-transform:uppercase; letter-spacing:0.15em; color:var(--color-text-muted); font-weight:700; margin-bottom:10px; font-family:var(--font-mono);">Leg Structure</p>
                    ${legsHtml}
                </div>
                <div>
                    <p style="font-size:0.6rem; text-transform:uppercase; letter-spacing:0.15em; color:var(--color-text-muted); font-weight:700; margin-bottom:10px; font-family:var(--font-mono);">Trade Summary</p>
                    <div style="display:grid; grid-template-columns:1fr 1fr; gap:12px; font-family:var(--font-mono); font-size:0.82rem;">
                        <div>
                            <span style="color:var(--color-text-muted); font-size:0.62rem; display:block; text-transform:uppercase; letter-spacing:0.1em; font-weight:700;">Max Profit</span>
                            <span style="color:var(--accent-success-lt); font-weight:700; font-size:1rem;">+$${maxProfit.toFixed(0)}</span>
                        </div>
                        <div>
                            <span style="color:var(--color-text-muted); font-size:0.62rem; display:block; text-transform:uppercase; letter-spacing:0.1em; font-weight:700;">Max Loss</span>
                            <span style="color:var(--accent-danger); font-weight:700; font-size:1rem;">-$${maxLoss.toFixed(0)}</span>
                        </div>
                        <div>
                            <span style="color:var(--color-text-muted); font-size:0.62rem; display:block; text-transform:uppercase; letter-spacing:0.1em; font-weight:700;">Gate Score</span>
                            <span class="hd-score-badge ${scoreClass}">${score.toFixed(0)}</span>
                        </div>
                        <div>
                            <span style="color:var(--color-text-muted); font-size:0.62rem; display:block; text-transform:uppercase; letter-spacing:0.1em; font-weight:700;">Premium</span>
                            <span style="color:${premiumColor}; font-weight:700; font-size:1rem;">${isCredit ? '+' : ''}${cost.toFixed(2)}</span>
                        </div>
                    </div>
                </div>
                <div>
                    <p style="font-size:0.6rem; text-transform:uppercase; letter-spacing:0.15em; color:var(--color-text-muted); font-weight:700; margin-bottom:10px; font-family:var(--font-mono);">Pipeline Journey</p>
                    ${renderPipelineJourney(pick.pipeline, pick.strategy_reasoning)}
                </div>
            </div>
```

Also extract `pipeline` and `strategy_reasoning` at top of the `picks.map()` callback:

```javascript
        const pipeline = pick.pipeline || null;
        const strategyReasoning = pick.strategy_reasoning || null;
```

**Step 3: Manual verification**

1. Start the server: `cd /home/arvindk/devl/aws/bedrock-core && source .venv/bin/activate && python -m uvicorn ui.server:app --reload --port 8080`
2. Open browser at `http://localhost:8080`
3. Run a scan (e.g., AAPL, tight policy)
4. Navigate to Scan & Discovery view
5. Click a trade card to expand it
6. Verify third panel "Pipeline Journey" shows 5 stages with green checkmarks and display text
7. Verify "Strategy Reasoning" block appears at bottom of pipeline panel

**Step 4: Commit**

```bash
git add ui/app.js
git commit -m "feat: add pipeline journey panel to expanded trade cards"
```

---

## Task 4: Frontend — "Why No Trades?" Zero-Picks Card

**Files:**
- Modify: `ui/app.js` (function `renderTradeCards`, add `renderNoTradesCard`)
- Test: Manual browser test

**Context:**
When `picks` array is empty, `renderTradeCards([])` currently shows a plain `<p>No picks found</p>`. We replace this with a rich "Zero Trades Card" using `scanResult.noTradesExplanation`.

**Step 1: Add `renderNoTradesCard` function to `app.js`**

Add after `renderPipelineJourney`:

```javascript
// ============================================================================
// ZERO TRADES CARD
// ============================================================================

function renderNoTradesCard(explanation) {
    if (!explanation) {
        return `<div style="color:var(--color-text-muted); padding:40px; text-align:center; font-family:var(--font-mono); font-size:0.85rem;">No picks found for this scan</div>`;
    }

    const { summary, top_blockers = [], gate_counts = {}, next_actions = [] } = explanation;

    const blockerSeverityColor = {
        event: 'var(--accent-red)',
        risk: 'var(--accent-red)',
        gatekeeper: 'var(--accent-amber)',
        correlation: 'var(--accent-amber)',
        generated: 'var(--color-text-muted)',
    };

    const blockersHtml = top_blockers.map(b => `
        <div style="padding:10px 14px; margin-bottom:6px; border-left:3px solid ${blockerSeverityColor[b.gate] || 'var(--accent-red)'}; background:rgba(239,68,68,0.06); border-radius:0 4px 4px 0;">
            <div style="font-family:var(--font-mono); font-size:0.65rem; font-weight:700; text-transform:uppercase; letter-spacing:0.1em; color:${blockerSeverityColor[b.gate] || 'var(--accent-red)'}; margin-bottom:3px;">
                ${(b.gate || '').toUpperCase()} GATE — ${(b.code || '').replace(/_/g, ' ')}
            </div>
            <div style="font-family:var(--font-mono); font-size:0.8rem; color:var(--color-text-secondary);">${b.display || '—'}</div>
        </div>`).join('');

    // Mini funnel
    const gc = gate_counts;
    const funnelSteps = [
        { label: 'Generated', value: gc.generated },
        { label: 'Event', value: gc.after_event },
        { label: 'Risk', value: gc.after_risk },
        { label: 'Gate', value: gc.after_gatekeeper },
        { label: 'Corr', value: gc.after_correlation },
        { label: 'Final', value: gc.final },
    ];
    const funnelHtml = funnelSteps.map((step, i) => {
        const isZero = step.value === 0;
        const color = isZero ? 'var(--accent-red)' : 'var(--color-text-muted)';
        const sep = i < funnelSteps.length - 1 ? '<span style="color:var(--color-text-dim); margin:0 4px;">→</span>' : '';
        return `<span style="font-family:var(--font-mono); font-size:0.7rem; color:${color}; font-weight:${isZero ? 700 : 400};">${step.value ?? '—'}<span style="font-size:0.55rem; color:var(--color-text-dim); display:block;">${step.label}</span></span>${sep}`;
    }).join('');

    const actionsHtml = next_actions.length > 0
        ? next_actions.map(a => `
            <div style="display:flex; align-items:flex-start; gap:8px; padding:5px 0; font-family:var(--font-mono); font-size:0.75rem; color:var(--color-text-secondary);">
                <span style="color:var(--accent-indigo); flex-shrink:0;">→</span>
                <span>${a}</span>
            </div>`).join('')
        : '';

    return `
    <div style="border:1px solid rgba(239,68,68,0.2); border-radius:8px; padding:20px; background:rgba(239,68,68,0.03);">
        <div style="display:flex; align-items:center; gap:10px; margin-bottom:16px;">
            <svg style="width:18px;height:18px;stroke:var(--accent-red);fill:none;stroke-width:2;flex-shrink:0;" viewBox="0 0 24 24">
                <circle cx="12" cy="12" r="10"/><line x1="4.93" y1="4.93" x2="19.07" y2="19.07"/>
            </svg>
            <span style="font-family:var(--font-mono); font-weight:700; font-size:0.85rem; color:var(--color-text-primary);">No Trades Selected</span>
        </div>
        <p style="font-family:var(--font-mono); font-size:0.72rem; color:var(--color-text-muted); margin:0 0 14px;">${summary || '0 picks returned'}</p>

        ${blockersHtml}

        <div style="margin:14px 0; display:flex; align-items:center; gap:2px; flex-wrap:wrap;">
            <span style="font-family:var(--font-mono); font-size:0.6rem; text-transform:uppercase; letter-spacing:0.1em; color:var(--color-text-dim); margin-right:6px; font-weight:700;">Funnel</span>
            ${funnelHtml}
        </div>

        ${actionsHtml ? `
        <div style="margin-top:14px; padding-top:12px; border-top:1px solid var(--color-border-subtle);">
            <span style="font-family:var(--font-mono); font-size:0.6rem; text-transform:uppercase; letter-spacing:0.1em; color:var(--color-text-dim); font-weight:700; display:block; margin-bottom:6px;">Suggested Actions</span>
            ${actionsHtml}
        </div>` : ''}
    </div>`;
}
```

**Step 2: Update `renderTradeCards` empty-state handler**

Find the empty-picks check in `renderTradeCards` (around line 447):

```javascript
    if (!picks || picks.length === 0) {
        container.innerHTML = '<p style="color:var(--color-text-muted); padding:40px; text-align:center; font-family:var(--font-mono); font-size:0.85rem;">No picks found for this scan</p>';
        return;
    }
```

Replace with:

```javascript
    if (!picks || picks.length === 0) {
        const noTradesExpl = (appState.lastScanResult || {}).noTradesExplanation || null;
        container.innerHTML = renderNoTradesCard(noTradesExpl);
        return;
    }
```

**Step 3: Manual verification**

1. Run a scan with tight policy on a symbol where sector cap is likely to trigger (e.g., AAPL with existing portfolio)
2. When 0 picks returned, verify the Zero Trades Card appears with:
   - Summary sentence
   - Blocker block with gate name + display text
   - Mini funnel showing where count dropped to 0
   - 3 suggested action items
3. Also verify normal picks still render correctly

**Step 4: Commit**

```bash
git add ui/app.js
git commit -m "feat: replace empty picks message with structured no-trades explanation card"
```

---

## Task 5: Frontend — Human-Readable Rejection Reasons in Rejection Tabs

**Files:**
- Modify: `ui/app.js` (function `switchRejectionTab`, line ~387)
- Test: Manual browser test

**Context:**
`switchRejectionTab()` renders rejection rows in a table. Each row shows a raw `reason` string formatted by `formatRejectionReason()`. Now that the API response includes `display_reason` and `severity` on each rejection, we use those directly.

**Step 1: Update `switchRejectionTab` rejection row renderer**

Find the `content.innerHTML` assignment in `switchRejectionTab` (around line 409):

```javascript
    content.innerHTML = `
    <table class="hd-table">
        ...
        ${list.map(rej => {
            const candidate = rej.candidate || rej;
            const sym = candidate.symbol || rej.symbol || '—';
            const strat = (candidate.strategy || rej.strategy || '—').replace(/_/g, ' ');
            const rawReason = rej.reason || rej.message || rej.rejection_reason || '—';
            const reason = formatRejectionReason(rawReason);
            const score = rej.score !== undefined ? parseFloat(rej.score).toFixed(1) : '—';
            return `<tr>...${reason}...`;
```

Update the `reason` and severity extraction lines:

```javascript
        ${list.map(rej => {
            const candidate = rej.candidate || rej;
            const sym = candidate.symbol || rej.symbol || '—';
            const strat = (candidate.strategy || rej.strategy || '—').replace(/_/g, ' ');
            // Prefer pre-computed display_reason from API; fall back to client-side parser
            const reason = rej.display_reason || formatRejectionReason(rej.reason || rej.message || rej.rejection_reason || '—');
            const severity = rej.severity || 'info';
            const score = rej.score !== undefined ? parseFloat(rej.score).toFixed(1) : '—';

            const severityColors = {
                critical: 'var(--accent-red)',
                warning: 'var(--accent-amber)',
                info: 'var(--color-text-muted)',
            };
            const reasonColor = severityColors[severity] || 'var(--accent-red)';

            return `
            <tr>
                <td style="font-weight:700;">${sym}</td>
                <td class="text-muted">${strat}</td>
                <td style="color:${reasonColor}; font-size:0.78rem;">${reason}</td>
                <td class="text-mono">${score}</td>
            </tr>`;
        }).join('')}
```

**Step 2: Manual verification**

1. Run a scan that triggers rejections (tight policy on tech stock)
2. In Scan & Discovery view, check the rejection tabs (Risk, Gatekeeper, etc.)
3. Verify rejection reasons show human-readable text like:
   - "Sector Technology cap exceeded: 100% used (limit 25%)" in red
   - "Score 65 below threshold 70" in amber/muted
4. Verify color coding matches severity (red = critical, amber = warning)

**Step 3: Commit**

```bash
git add ui/app.js
git commit -m "feat: use display_reason and severity colors in rejection tabs"
```

---

## Task 6: Integration Verification

**Step 1: Run full test suite**

```bash
cd /home/arvindk/devl/aws/bedrock-core
source .venv/bin/activate
python -m pytest tests/ -v --tb=short
```

Expected: All existing tests pass. New tests pass. No regressions.

**Step 2: End-to-end browser check**

1. Start server: `python -m uvicorn ui.server:app --reload --port 8080`
2. Navigate to `http://localhost:8080`
3. Verify Analyze view loads with KPIs and volatility context
4. Run a scan → verify pipeline counts update in Scan view
5. Expand a trade card → verify 3-panel layout with Pipeline Journey
6. Check rejection tabs → verify colored display reasons
7. Switch to Positions → verify no regressions
8. Switch to Decision Audit → verify log still populates

**Step 3: Verify zero-picks case**

Run scan with policy=tight and a symbol likely to be blocked (or temporarily set portfolio mock to include large tech position so sector cap triggers):

Check that zero-picks card appears with blocker + funnel + actions instead of blank message.

**Step 4: Final commit**

```bash
git add -A
git commit -m "feat: decision intelligence UI — pipeline journey, no-trades explanation, display reasons"
```

---

## Regression Checklist

Before calling complete:

- [ ] Header ticker still updates
- [ ] Pipeline stage counts update after scan
- [ ] Rejection tab counts update after scan
- [ ] Existing trade card expand/collapse still works (chevron animation)
- [ ] Positions view loads with sector chart and correlation matrix
- [ ] Decision Audit view populates with log text
- [ ] Risk Alerts still show in Positions view
- [ ] Settings view loads without error

---

## What's NOT in Scope (v2)

- Risk Engine Panel (remaining capital, drawdown status)
- Liquidity & Execution scores visible in trade cards
- Event Engine calendar view
- Correlation breach linked to trade decision text
- System State Awareness panel
