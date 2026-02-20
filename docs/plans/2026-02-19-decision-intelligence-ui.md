# Decision Intelligence UI — Design Doc
**Date:** 2026-02-19
**Status:** Approved
**Scope:** 3 critical UX gaps — per-trade pipeline breakdown, "why no trades" explanation, human-readable decision reasoning

---

## Problem Statement

The backend is a 7-stage institutional pipeline (Vol → Events → Risk → Gatekeeper → Correlation → Ranking). The frontend is a log viewer. Users see outputs but not the decision intelligence behind them.

**Core insight:** Backend enriches, frontend renders. UI must be a truthful projection of backend decisions — no frontend inference that could drift from actual outcomes.

---

## Fix 1: Per-Trade Pipeline Journey

### Backend Change (`orchestrator.py`)

Each `final_pick` in `DecisionLog.final_picks` gets a `pipeline` field added before return. This is built during orchestration from data already in scope.

**Data structure (structured-first, narrative-second):**

```json
{
  "pipeline": {
    "volatility": {
      "status": "pass",
      "code": "MEDIUM_REGIME",
      "metrics": { "regime": "MED", "iv_rank": 45, "annual_vol": 0.307 },
      "display": "Medium vol regime, IV rank 45% — vertical spreads preferred"
    },
    "event": {
      "status": "pass",
      "code": "NO_EVENTS",
      "metrics": { "blocking_count": 0, "policy": "PLAY" },
      "display": "No blocking events — trading permitted"
    },
    "risk": {
      "status": "pass",
      "code": "WITHIN_LIMITS",
      "metrics": { "max_loss": 480, "limit": 1000, "sector": "Technology", "sector_pct": 22 },
      "display": "Max loss $480 within $1,000 limit, sector at 22% (limit 25%)"
    },
    "gatekeeper": {
      "status": "pass",
      "code": "APPROVED",
      "metrics": { "score": 87, "threshold": 70 },
      "display": "Score 87/100 above threshold 70"
    },
    "correlation": {
      "status": "pass",
      "code": "DIVERSIFIED",
      "metrics": { "max_corr": 0.42, "threshold": 0.70 },
      "display": "Max correlation 0.42 — well diversified"
    }
  },
  "strategy_reasoning": {
    "chosen": "CREDIT_SPREAD",
    "drivers": {
      "regime": "HIGH",
      "iv_rank": 78,
      "trend": "UPTREND",
      "policy": "TIGHT"
    },
    "display": "IV Rank 78% (High) in Tight policy → prefer credit spreads over debit"
  }
}
```

**Key design rules:**
- `status`: always `"pass"` | `"fail"` | `"skip"` (skipped = not reached)
- `code`: machine-readable, stable identifier (no spaces)
- `metrics`: raw numbers for future analytics/sorting
- `display`: preformatted human string, built server-side

### Frontend Change (`app.js`, `index.html`)

Expand the existing `hd-trade-card-body` to show a third panel: **Pipeline Journey**.

```
┌─────────────────────────────────────────────────────────┐
│ AAPL  |  CREDIT SPREAD  |  +$2.40  |  -$760  |  Score 87 │
├─────────────────────────────────────────────────────────┤
│ [Leg Structure]  [Trade Summary]  [Pipeline Journey]      │
│                                                           │
│  ✔ Volatility   Medium regime, IV rank 45%               │
│  ✔ Event Check  No blocking events                        │
│  ✔ Risk Gate    Max loss $480 within $1,000 limit         │
│  ✔ Gatekeeper   Score 87/100                              │
│  ✔ Correlation  Max corr 0.42 — well diversified          │
│                                                           │
│  Strategy: Credit spreads preferred (HIGH vol + TIGHT)    │
└─────────────────────────────────────────────────────────┘
```

Status indicator: green checkmark for pass, red X for fail, gray dash for skip.

---

## Fix 2: "Why No Trades?" Explanation

### Backend Change (`orchestrator.py`, `server.py`)

When `final_picks` is empty, include `noTradesExplanation` in the API response:

```json
{
  "noTradesExplanation": {
    "summary": "0 picks: 17/17 rejected at Risk Gate",
    "top_blockers": [
      {
        "gate": "risk",
        "code": "SECTOR_CAP",
        "count": 17,
        "display": "Technology sector at 100% (limit 25%) — all candidates blocked"
      }
    ],
    "gate_counts": {
      "generated": 17,
      "after_event": 17,
      "after_risk": 0,
      "after_gatekeeper": 0,
      "after_correlation": 0,
      "final": 0
    },
    "next_actions": [
      "Reduce Technology sector exposure below 25%",
      "Expand scan to non-tech symbols (AMZN, JPM, JNJ)",
      "Switch policy from Tight → Moderate if risk tolerance allows"
    ]
  }
}
```

**`top_blockers` logic:**
1. If `blocking_events` → event blocker(s)
2. Else if `risk_rejections` → most common risk rule
3. Else if `gatekeeper_rejections` → low score
4. Else if `correlation_rejections` → correlation breach
5. Else → "No candidates generated in date window"

**`next_actions` logic:** Pre-templated strings based on blocker type. Not AI-generated.

### Frontend Change

Replace the single "No picks found" `<p>` with a "Zero Trades Card":

```
┌─────────────────────────────────────────────────────────┐
│ ⊘  No Trades Selected                                    │
│                                                           │
│  Primary blocker: RISK GATE — Sector Concentration       │
│  Technology at 100% (limit 25%)                          │
│  17/17 candidates blocked at this stage                  │
│                                                           │
│  Funnel:  17 → 17 → 0 → — → — → 0                       │
│                                                           │
│  Suggested actions:                                       │
│  → Reduce Technology exposure below 25%                  │
│  → Expand to non-tech symbols (AMZN, JPM, JNJ)           │
│  → Switch Tight → Moderate policy                        │
└─────────────────────────────────────────────────────────┘
```

---

## Fix 3: Human-Readable Rejection Reasons

### Backend Change (`server.py`)

Add `display_reason` and `severity` to every rejection in the API response. Use existing `extract_reason_summary()` from `reason_codes.py`.

```json
{
  "rejections": {
    "risk": [
      {
        "candidate": { "symbol": "AAPL", "strategy": "BULL_CALL_SPREAD" },
        "reason": "RISK_REJECT|rule=SECTOR_CAP|sector=Technology|used_pct=100|limit_pct=25",
        "display_reason": "Sector Technology cap exceeded: 100% used (limit 25%)",
        "severity": "critical"
      }
    ]
  }
}
```

**`severity` mapping:**
- `SECTOR_CAP`, `MAX_LOSS_EXCEEDED`, `DRAWDOWN_HALT` → `"critical"`
- `LIQUIDITY`, `SPREAD_TOO_WIDE` → `"warning"`
- `LOW_SCORE`, `IV_PENALTY` → `"info"`
- `CORRELATION_BREACH` → `"warning"`
- Event blocks → `"critical"`

### Frontend Change (`app.js`)

Update `switchRejectionTab()` renderer to use `display_reason` when available, fallback to `formatRejectionReason(reason)`. Add severity color coding.

---

## Naming Convention

**Rule: snake_case throughout the API** (backend generates, frontend reads).

The frontend already handles both (`scanResult.policyMode` was camelCase — we standardize to snake_case on the backend, add mapping in `server.py` response).

Exception: existing keys that already ship as camelCase remain unchanged to avoid regressions (`spyTrend`, `gateFunnel`, `decisionLog`, `policyMode`). New fields use snake_case.

---

## Files Changed

| File | Change |
|------|--------|
| `agent/orchestrator.py` | `_build_pipeline_journey(pick, log)` helper, call in final sort block; `_build_no_trades_explanation(log)` helper |
| `ui/server.py` | Add `display_reason` + `severity` to rejections; add `noTradesExplanation` to scan response; pass strategy_reasoning through |
| `ui/app.js` | Update `renderTradeCards()` to show pipeline panel; update `renderTradeCards()` for zero-picks state; update `switchRejectionTab()` for display_reason |
| `ui/index.html` | No structural changes needed (app.js generates the HTML) |

---

## What's NOT in Scope

- Risk Engine Panel (fix #5 from analysis) — v2
- Liquidity & Execution visibility (fix #7) — v2
- Event Engine calendar view (fix #6) — v2
- Correlation breach linked to decisions (fix #8) — v2
- System State Awareness panel (fix #9) — v2

---

## Success Criteria

1. Expanded trade card shows 5 pipeline stages with pass/fail + detail for each final pick
2. Zero-picks state shows structured explanation with top blocker + 3 suggested actions
3. Rejection tab rows show human-readable `display_reason` with severity color
4. No regressions in existing pipeline visualization, portfolio view, or audit view
