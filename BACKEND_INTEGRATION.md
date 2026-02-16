# 🔗 Backend Integration Guide

## Overview

The Desk Command dashboard is now fully connected to the backend orchestrator. The frontend sends scan requests to `/api/scan` and receives structured decision logs with picks, rejections, and market context.

---

## API Endpoint: POST /api/scan

### Request

```json
{
  "symbol": "NVDA",
  "start_date": "2026-03-01",
  "end_date": "2026-06-01",
  "top_n": 5,
  "portfolio_json": "[{\"symbol\": \"QQQ\", \"max_loss\": 500}]",
  "policy_mode": "tight"
}
```

### Response

```json
{
  "regime": "HIGH",
  "spyTrend": "Uptrend",
  "macroRisk": "FOMC in 3 days",
  "policyMode": "Tight ($1,000)",
  "blockingEvents": [],
  "gateFunnel": {
    "generated": 12,
    "afterRisk": 9,
    "afterGatekeeper": 6,
    "afterCorrelation": 4,
    "final": 3
  },
  "picks": [
    {
      "rank": 1,
      "strategy": "Bull Call Debit",
      "expiration": "Mar 20",
      "cost": 1.2,
      "maxLoss": 120,
      "maxProfit": 380,
      "score": 84,
      "legs": [...],
      "warnings": []
    }
  ],
  "rejections": {
    "risk": ["Max loss $1,500 exceeds limit $1,000", ...],
    "gatekeeper": ["Leg 1 bid/ask spread too wide", ...],
    "correlation": ["Correlation 0.78 with AAPL", ...]
  },
  "decisionLog": {
    "regime": "HIGH",
    "strategyHint": "CREDIT_SPREAD",
    "blockingEvents": "None",
    "generated": 12,
    "riskPassed": 9,
    "gatekeeperPassed": 6,
    "correlationPassed": 4,
    "finalPicks": 3,
    "timestamp": "2026-02-16T14:32:45Z"
  }
}
```

---

## Data Flow

```
Dashboard (React)
    ↓
User enters: Symbol, Dates, Portfolio, Policy
    ↓
ScanForm component submits to /api/scan
    ↓
ui/server.py (FastAPI)
    ↓
Calls orchestrator.full_scan_with_orchestration()
    ↓
Orchestrator runs pipeline:
  - EventLoader (blocking events)
  - VolEngine (regime detection)
  - OptionsScanner (candidates)
  - RiskEngine (hard rejections)
  - ScoredGatekeeper (soft scoring)
  - CorrelationGate (portfolio overlaps)
    ↓
Returns DecisionLog with all metrics
    ↓
UIServer transforms DecisionLog → Dashboard response
    ↓
Dashboard re-renders with real data
    ↓
User sees:
  - Market context
  - Gate funnel
  - Final picks (ranked)
  - Rejections (categorized)
  - Decision log (audit trail)
```

---

## Running the Dashboard

### Start the Backend Server

```bash
cd /home/arvindk/devl/aws/bedrock-core
source .venv/bin/activate
python -m uvicorn ui.server:app --host 0.0.0.0 --port 8001 --reload
```

The server runs on `http://localhost:8001`

### Access the Dashboard

```bash
# Option 1: Serve static files (development)
cd ui-aistudio
python -m http.server 8080

# Then navigate to:
# http://localhost:8080/index.html
# (The fetch calls will go to http://localhost:8001/api/scan)
```

Or:

```bash
# Option 2: Run with React development server (if using npm)
npm start
```

---

## How the Dashboard Uses API Data

### 1. User Enters Scan Parameters

```jsx
<ScanForm onSubmit={handleScan} isLoading={isLoading} />
```

User fills:
- Symbol: "NVDA"
- Start Date: "2026-03-01"
- End Date: "2026-06-01"
- Policy: "Tight ($1,000)"
- Portfolio: Optional JSON

### 2. Dashboard Calls API

```jsx
const handleScan = async (params) => {
  const response = await fetch('/api/scan', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(params),
  });
  const data = await response.json();
  setApiData(data);  // Update dashboard
};
```

### 3. Dashboard Renders With Real Data

```jsx
const displayData = apiData || mockData;

<MarketContext
  regime={displayData.regime}
  spyTrend={displayData.spyTrend}
  macroRisk={displayData.macroRisk}
  policyMode={displayData.policyMode}
/>

<GateFunnel
  generated={displayData.gateFunnel.generated}
  afterRisk={displayData.gateFunnel.afterRisk}
  afterGatekeeper={displayData.gateFunnel.afterGatekeeper}
  afterCorrelation={displayData.gateFunnel.afterCorrelation}
  final={displayData.gateFunnel.final}
/>
```

---

## Error Handling

If the API call fails:

```jsx
{error && (
  <div style={{ padding: '20px 40px', background: 'rgba(239, 68, 68, 0.1)', ... }}>
    <p style={{ color: '#EF4444', margin: 0 }}>❌ Error: {error}</p>
  </div>
)}
```

The dashboard shows an error message but doesn't crash — it can retry the scan.

---

## Expected DecisionLog Structure

The orchestrator's `DecisionLog` object should have these fields (mapped to dashboard response):

```python
class DecisionLog:
    regime: str                           # "HIGH", "MEDIUM", "LOW"
    spy_trend: str                        # "Uptrend", "Downtrend"
    macro_risk: str                       # "FOMC in 3 days", "None"
    total_generated: int                  # Raw candidates scanned
    after_risk_gate: int                  # Survived risk filtering
    after_gatekeeper: int                 # Survived liquidity/spreads
    after_correlation: int                # Survived portfolio overlap
    final_picks: List[Dict]               # Top N ranked by score
    risk_rejections: List[str]            # Why trades failed risk gate
    gatekeeper_rejections: List[str]      # Why trades failed gatekeeper
    correlation_rejections: List[str]     # Why trades failed correlation
    blocking_events: List[str]            # FOMC, earnings, etc.
    strategy_hint: str                    # "CREDIT_SPREAD", "BULL_CALL_DEBIT"
    timestamp: str                        # ISO format timestamp
```

---

## Testing the Integration Locally

### 1. Start the Backend

```bash
uvicorn ui.server:app --host 0.0.0.0 --port 8001 --reload
```

### 2. Make a Test Request

```bash
curl -X POST http://localhost:8001/api/scan \
  -H "Content-Type: application/json" \
  -d '{
    "symbol": "NVDA",
    "start_date": "2026-03-01",
    "end_date": "2026-06-01",
    "top_n": 5,
    "portfolio_json": "[]",
    "policy_mode": "tight"
  }'
```

### 3. Check the Response

You should get back the full decision log with all gates and picks.

### 4. Open the Dashboard

```bash
cd ui-aistudio
python -m http.server 8080
# Navigate to http://localhost:8080/index.html
```

### 5. Run a Scan in the Dashboard

- Enter symbol: "NVDA"
- Select dates and policy
- Click "🔍 Run Scan"
- Watch the funnel animate and fill with real data

---

## Fallback to Mock Data

If the API is unavailable, the dashboard automatically falls back to mock data:

```jsx
const displayData = apiData || {
  regime: 'HIGH',
  spyTrend: 'Uptrend',
  // ... etc
  picks: mockPicks,
  rejections: mockRejections,
  decisionLog: mockDecisionLog,
};
```

This allows the dashboard UI to be tested/demoed without a running backend.

---

## Production Deployment

### Environment Variables

```bash
# For backend to find agent modules
export PYTHONPATH=/path/to/bedrock-core:/path/to/bedrock-core/agent

# For API requests (if dashboard is separate server)
export REACT_APP_API_URL=https://api.deskcommand.example.com
```

### Docker

The dashboard can be served from FastAPI directly:

```python
app.mount("/", StaticFiles(directory="ui-aistudio", html=True), name="static")
```

Or served from a separate static file server (Nginx, S3, CDN).

---

## Files Modified

1. **ui-aistudio/dashboard.jsx** — Added `ScanForm` component and API integration
2. **ui-aistudio/dashboard.css** — Added form styling
3. **ui-aistudio/USER_WALKTHROUGH.md** — Added user journey documentation
4. **ui/server.py** — Added `/api/scan` endpoint connecting to orchestrator
5. **BACKEND_INTEGRATION.md** — This file

---

## Next Steps

1. ✅ Dashboard connected to backend
2. ✅ User walkthrough documented
3. ⏭️ Deploy to staging
4. ⏭️ Test with real market data
5. ⏭️ Monitor performance metrics
6. ⏭️ Collect user feedback
7. ⏭️ Deploy to production

---

**The Desk Command dashboard is now live and ready to connect to the hedging strategy orchestrator.** 🚀

