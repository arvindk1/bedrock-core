# 🛡️ Desk Command Dashboard — Build Summary

## What Was Built

A **production-grade, institutional-grade trading dashboard** for the hedge fund options desk system. This is NOT a retail scanner UI — it's a desk risk manager interface emphasizing transparency, risk, and decision clarity.

### Key Features Implemented

1. **Market Context Bar** — Vol regime, macro risk, policy limits at a glance
2. **Gate Flow Funnel** — Visual representation of filtering: Generated → Risk Gate → Gatekeeper → Correlation → Final
3. **Blocking Events Banner** — Clear display of hard rejections (earnings, macro events)
4. **Final Picks Table** — Ranked candidates with live drill-down detail view
5. **Rejections Tab** — Transparent view of why trades were filtered (Risk | Gatekeeper | Correlation)
6. **Decision Log** — Audit trail for paper trading review and backtest comparison
7. **Trade Management** — Live position tracking with P/L, expected move, DTE warnings

### Design Philosophy: Refined Brutalism

- **Dark Theme**: Deep charcoal (#0F172A) background with slate overlays
- **Precision Typography**: Playfair Display (headers), IBM Plex Mono (data)
- **Color Language**: Emerald (pass/good), Crimson (reject/danger), Amber (warning), Steel Blue (info)
- **Motion**: Purposeful animations (smooth funnel reveals, table transitions)
- **Density**: High information density but breathable — no clutter

### Emotional Design

Users should feel: **"The system is protecting me."**

Not: "This is a scanner that shows me contracts."  
But: "This is a structured desk that enforces discipline."

---

## File Structure

```
ui-aistudio/
├── dashboard.jsx              # Main React component (1000 lines)
├── dashboard.css              # Styling & animations (700 lines)
├── index.html                 # Standalone demo with React CDN
├── README.md                  # Comprehensive documentation
├── [existing files]           # TypeScript config, package.json, etc.
```

---

## Quick Start

### 1. View the Dashboard

**Option A: Standalone HTML Demo**
```bash
cd /home/arvindk/devl/aws/bedrock-core/ui-aistudio
open index.html  # or point browser to file://...
```

**Option B: React Component Integration**
```jsx
import TradingDashboard from './ui-aistudio/dashboard.jsx';

export default function App() {
  return <TradingDashboard />;
}
```

### 2. Connect to Backend

Update the `TradingDashboard` component to call your orchestrator:

```jsx
// Inside useEffect, call your backend
const response = await fetch('/api/scan', {
  method: 'POST',
  body: JSON.stringify({
    symbol: 'NVDA',
    start_date: '2026-03-01',
    end_date: '2026-06-01',
    portfolio_json: '[]',
    policy_mode: 'tight'
  })
});

// Response should include:
// - regime, spyTrend, macroRisk, policyMode
// - gateFunnel: { generated, afterRisk, afterGatekeeper, afterCorrelation, final }
// - picks: [ { rank, strategy, expiration, cost, maxLoss, maxProfit, score, legs, warnings } ]
// - rejections: { risk: [...], gatekeeper: [...], correlation: [...] }
// - decisionLog: { regime, strategyHint, blockingEvents, ... }
```

### 3. Expected Backend Response

The dashboard expects this shape (from `ui/server.py` → orchestrator):

```json
{
  "regime": "HIGH",
  "spyTrend": "Uptrend",
  "macroRisk": "FOMC in 3 days ⚠️",
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
      "breakeven": "$425",
      "legs": [
        { "side": "Long Call", "strike": "420", "delta": "0.65", "iv": "22%", "bid": "2.50", "ask": "2.65", "oi": "12,400" },
        { "side": "Short Call", "strike": "425", "delta": "0.45", "iv": "21%", "bid": "1.30", "ask": "1.45", "oi": "8,900" }
      ],
      "warnings": []
    }
  ],
  "rejections": {
    "risk": [
      "Max loss $1,500 exceeds limit $1,000",
      "Sector Technology cap exceeded",
      "Concentration: Already 3x NVDA exposure"
    ],
    "gatekeeper": [
      "Leg 1 bid/ask spread too wide (1.8% > 1.5%)",
      "Market impact 3.2% exceeds 2% threshold",
      "Open interest below threshold for short strike"
    ],
    "correlation": [
      "Correlation 0.78 with AAPL exceeds threshold 0.70",
      "Correlation 0.72 with QQQ exceeds threshold 0.70"
    ]
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

## Design Details

### Color Palette

| Usage | Hex | RGB |
|-------|-----|-----|
| Pass/Good | #10B981 | Emerald |
| Reject/Danger | #EF4444 | Crimson |
| Warning/Caution | #F59E0B | Amber |
| Info/Neutral | #3B82F6 | Steel Blue |
| Background Primary | #0F172A | Deep Charcoal |
| Background Secondary | #1E293B | Slate |

### Typography

| Usage | Font | Size | Notes |
|-------|------|------|-------|
| Header | Playfair Display | 36px | Authority, serif |
| Section Title | Playfair Display | 20px | Hierarchy |
| Table Header | IBM Plex Mono | 11px | Precision, uppercase |
| Table Data | IBM Plex Mono | 13px | Code-like |
| Body | System fonts | 14px | Clean, readable |

### Spacing

- Main padding: 32px
- Section gaps: 24px
- Card padding: 24px
- Internal gaps: 12px
- Table cell padding: 16px

### Animations

- Bar animations: 0.6s cubic-bezier(0.34, 1.56, 0.64, 1)
- Modal slides: 0.3s ease-out
- Table hovers: 0.2s ease
- Pulse warnings: 2s infinite

---

## Architecture Principles

### Component Hierarchy

```
TradingDashboard
├── Header
├── MarketContext
├── GateFunnel
├── BlockingEventsBanner (conditional)
├── Tabs
│   ├── FinalPicksTable
│   │   └── TradeDetailModal (overlay)
│   ├── RejectionsPanel
│   └── TradeManagementView
└── DecisionLogModal (overlay)
```

### State Management

```jsx
const [selectedPick, setSelectedPick] = useState(null);       // Currently viewed trade
const [showTradeDetail, setShowTradeDetail] = useState(false); // Modal open/close
const [showDecisionLog, setShowDecisionLog] = useState(false); // Audit log modal
const [activeTab, setActiveTab] = useState('picks');          // Tab selection
```

### Props Flow

Each component receives mocked/real data:
- `regime`, `spyTrend`, `macroRisk`, `policyMode` → MarketContext
- `generated`, `afterRisk`, `afterGatekeeper`, `afterCorrelation`, `final` → GateFunnel
- `events` → BlockingEventsBanner
- `picks` → FinalPicksTable
- `rejections` → RejectionsPanel
- `log` → DecisionLogModal

---

## Next Steps for Integration

### Phase 1: Backend Connection
1. Update `/api/scan` endpoint in `ui/server.py`
2. Connect to `full_scan_with_orchestration()` from orchestrator
3. Map decision log structure to response

### Phase 2: Live Updates
1. Add WebSocket for real-time position updates
2. Implement trade management socket connection
3. Add P/L streaming

### Phase 3: Advanced Features
1. Add performance analytics tab
2. Add threshold tuning UI
3. Add correlation heatmap visualization
4. Add backtest comparison view

---

## Key Design Decisions

### Why This Aesthetic?

1. **Dark Theme**: Reduces eye strain, feels professional, common in trading apps
2. **Monospace for Data**: Precision, immediately recognizable as real information
3. **Serif Headers**: Authority, differentiates from retail apps
4. **High Contrast**: Accessibility + readability
5. **Minimal Motion**: Professional feel, not "flashy"

### Why This Structure?

1. **Funnel First**: Immediate transparency about filtering
2. **Rejections Prominent**: Build trust through explanation
3. **Table-Based Picks**: Familiar trading interface
4. **Modal Drills**: Details without clutter
5. **Decision Log**: Audit trail differentiates from retail

---

## Testing Checklist

- [ ] Dashboard loads without errors
- [ ] Market context bar displays correctly
- [ ] Funnel bars animate on load
- [ ] Picking a row opens detail modal
- [ ] Rejections tab shows all three categories
- [ ] Decision log modal displays progression
- [ ] Tab switching works smoothly
- [ ] Responsive design on mobile (already included)
- [ ] Color contrast meets accessibility standards
- [ ] No console errors in browser dev tools

---

## Support

For questions about:
- **Design**: See `README.md` in ui-aistudio/
- **Component API**: Inline JSDoc in dashboard.jsx
- **Styling**: CSS variables documented in dashboard.css
- **Integration**: Check this file's "Backend Response" section

