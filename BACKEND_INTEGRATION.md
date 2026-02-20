# Backend Integration Guide

Document status: Current runtime contract for UI and backend.
Last reviewed: 2026-02-17.

## Overview
The current dashboard is served from `ui/` and integrates with FastAPI endpoints in `ui/server.py`.

Primary production-like scan path:
- UI (`ui/app.js`) -> `POST /api/scan`
- Backend (`ui/server.py`) -> `agent.orchestrator.full_scan_with_orchestration`
- Response -> gate funnel, picks, rejections, volatility context, decision log summary

## Runtime Components
- Frontend files: `ui/index.html`, `ui/app.js`, `ui/terminal.css`
- API server: `ui/server.py`
- Core engines:
  - `agent/orchestrator.py`
  - `agent/options_scanner.py`
  - `agent/risk_engine.py`
  - `agent/market_checks.py`
  - `agent/correlation_gate.py`
  - `agent/event_loader.py`
  - `agent/vol_engine.py`

## Main Endpoint: POST /api/scan

### Request
```json
{
  "symbol": "SPY",
  "start_date": "2026-03-01",
  "end_date": "2026-06-01",
  "top_n": 5,
  "portfolio_json": "[]",
  "policy_mode": "tight"
}
```

### Response Shape (Current)
```json
{
  "regime": "medium",
  "spyTrend": "Uptrend",
  "macroRisk": "No macro events",
  "policyMode": "Tight ($1000)",
  "blockingEvents": [],
  "gateFunnel": {
    "generated": 19,
    "afterEvent": 19,
    "afterRisk": 0,
    "afterGatekeeper": 0,
    "afterCorrelation": 0,
    "final": 0
  },
  "picks": [],
  "rejections": {
    "risk": [
      {
        "candidate": {
          "symbol": "SPY",
          "strategy": "BULL_CALL_DEBIT_SPREAD",
          "expiration": "2026-03-13"
        },
        "reason": "RISK_REJECT|rule=SECTOR_CAP|..."
      }
    ],
    "gatekeeper": [],
    "event": [],
    "correlation": []
  },
  "volatilityContext": {
    "annual_vol": 0.24,
    "daily_vol": 0.015,
    "iv_rank": null,
    "expected_move_30d": null
  },
  "decisionLog": {
    "regime": "medium",
    "strategyHint": "VERTICAL_SPREAD",
    "blockingEvents": "None",
    "generated": 19,
    "riskPassed": 0,
    "gatekeeperPassed": 0,
    "correlationPassed": 0,
    "finalPicks": 0,
    "timestamp": "2026-02-17T..."
  }
}
```

## Current Data Flow
1. User submits scan form in `ui/index.html`.
2. `initiateDiscoveryScan()` in `ui/app.js` calls `POST /api/scan`.
3. `ui/server.py` parses request and invokes orchestrator.
4. Orchestrator runs pipeline:
- Vol + events context
- Candidate generation
- Risk gate
- Gatekeeper scoring
- Correlation gate
- Final ranking
5. API transforms `DecisionLog` to dashboard response contract.
6. UI updates funnel, picks table, volatility block, and decision audit.

## Other Endpoints

### POST /api/gatekeeper/check
- Validates a trade proposal through `ScoredGatekeeper`.

### GET /api/market/snapshot/{symbol}
- Used by live ticker.
- Mix of live price fetch and static/mock context values.

### GET /api/portfolio/risk
- Currently static/mock response.

### GET /api/events/calendar
- Currently static/mock response.

### POST /api/smart-scan
- Not a stable path currently. Contract mismatch exists in request model vs handler usage.
- Treat as non-production until fixed.

## Known Functional Caveats
1. Default scan calls often return zero picks when `portfolio_json` is empty due current sector-cap behavior in risk gating.
2. Candidate risk-unit consistency (`max_loss`) needs care (per-share vs contract-dollar semantics).
3. Earnings data quality may degrade when external parser dependencies/data-provider behavior changes.
4. Some market data fetch failures can degrade to fallback/mock behavior.

## Local Runbook

### Start backend
```bash
cd /home/arvindk/devl/aws/bedrock-core
./run-ui.sh
```

### Open dashboard
- `http://localhost:8080/`

### Test API quickly
```bash
curl -X POST http://localhost:8080/api/scan \
  -H "Content-Type: application/json" \
  -d '{
    "symbol": "SPY",
    "start_date": "2026-03-01",
    "end_date": "2026-06-01",
    "top_n": 5,
    "portfolio_json": "[]",
    "policy_mode": "tight"
  }'
```

## Documentation Ownership
- If `ui/server.py` response fields change, update this file in the same change.
- If frontend payload shape changes in `ui/app.js`, update request examples here.
- Keep "Last reviewed" date current.
