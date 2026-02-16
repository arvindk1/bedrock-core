# UI/UX Analysis: HedgeDesk Console v2.4.0

## Overview
The ui-aistudio folder contains a professional React/TypeScript UI for options trading decision visualization. It demonstrates clean design patterns, type safety, and excellent information architecture that can inspire both the backend system and future UI development.

---

## Key Design Patterns We Can Adopt

### 1. **Structured Rejection Logging with Context**
**Current UI Pattern:**
```tsx
// RejectionPanel.tsx - Table-based rejection display
reasonCode: 'R-MAX-DD'        // Code (machine-readable)
message: 'Projected DD exceeds daily limit'  // Description (human-readable)
timestamp: '10:02:41'          // When it was rejected
category: 'Risk' | 'Gatekeeper' | 'Correlation'  // Which gate
```

**How This Aligns with Our Implementation:**
- Our `reason_codes.py` already does this! ✅
- UI shows we should store: `reasonCode`, `message`, `timestamp`, `category`
- Our structured format: `RISK_REJECT|rule=MAX_LOSS_EXCEEDED|...` captures this
- **Recommendation:** Enhance DecisionLog to include timestamps and gate categories in rejection reason codes

### 2. **Pipeline Stage Visualization with Status Indicators**
**Current UI Pattern:**
```tsx
// PipelineBar.tsx - Shows candidates flowing through gates
Generated (142) → Risk Gate (86) ⚠️ → Gatekeeper (42) ✅ → Correlation (12) ✅ → Final Picks (5) ✅
```

**How This Aligns with Our Implementation:**
- Our orchestrator has `candidates_raw`, `candidates_after_risk_gate`, `candidates_after_correlation`, `final_picks`
- UI color-codes by status: normal, warning, critical, success
- **Recommendation:** Add status tracking to each pipeline stage in DecisionLog for future UI consumption

### 3. **Expandable Detail Panels**
**Current UI Pattern:**
```tsx
// TradeCard - Collapsed shows summary, expanded shows full details
Summary: Symbol | Strategy | Net Premium | Max Risk | Score
Expanded: Leg Structure (left) | Risk Profile + Buttons (right)
```

**How This Aligns with Our Implementation:**
- Our TradeScore has `score_breakdown` and `details` fields
- Perfect structure for expandable UI components
- **Recommendation:** Keep this granular data structure (already doing it! ✅)

### 4. **Tabbed Categorization of Rejections**
**Current UI Pattern:**
```tsx
// RejectionPanel - Three tabs: Risk | Gatekeeper | Correlation
// Each filters rejections by category
```

**How This Aligns with Our Implementation:**
- We have three hard gates: RiskEngine, ScoredGatekeeper, CorrelationGate
- Plus EventLoader (hard block)
- DecisionLog stores: `rejections_risk`, `rejections_correlation`
- **Recommendation:** Add `rejections_gatekeeper`, `rejections_event` to DecisionLog for symmetry

### 5. **Color-Coded Status System**
**Current UI Palette:**
- `emerald` (green): Success, Long positions, bullish
- `rose`/`red`: Risk, negative, Short positions, bearish
- `amber`/`yellow`: Warning, volatility
- `indigo`/`blue`: Primary info, strategy details
- `slate`: Neutral, background, muted text

**Implications:**
- Consistent color coding across system = intuitive UX
- Our rejection messages should include severity levels
- **Recommendation:** Add severity enum to reason codes (LOW, MEDIUM, HIGH, CRITICAL)

---

## Architectural Insights from UI

### Type Safety Excellence
The UI demonstrates strong TypeScript patterns:
```tsx
// types.ts shows clear data contracts
interface TradeCandidate {
  id: string;
  symbol: string;
  gatekeeperScore: number;      // 0-100 score
  status: 'pending' | 'active' | 'rejected';
  rejectionReason?: string;
  rejectionCategory?: 'Risk' | 'Gatekeeper' | 'Correlation';
}

interface RejectionLog {
  id: string;
  reasonCode: string;           // Machine-readable: 'R-MAX-DD'
  message: string;              // Human-readable description
  timestamp: string;            // When rejected
  category: 'Risk' | 'Gatekeeper' | 'Correlation';
}
```

**Comparison to Our System:**
- We use structured reason codes ✅
- We should extend with `severity`, `category`, `timestamp` in DecisionLog ✅
- We have all the pieces, just need to surface them

---

## Recommendations for Backend Enhancement

### 1. **Extend DecisionLog to Support UI Rich Display**
```python
@dataclass
class RejectionDetail:
    reason_code: str           # RISK_REJECT|rule=MAX_LOSS_EXCEEDED|...
    message: str               # Extracted human summary
    timestamp: str             # ISO format when rejected
    category: str              # 'risk' | 'gatekeeper' | 'correlation' | 'event'
    severity: str              # 'low' | 'medium' | 'high' | 'critical'
    symbol: str
    strategy: str
```

### 2. **Add Structured Timestamps to Reason Codes**
Current: `RISK_REJECT|rule=MAX_LOSS_EXCEEDED|proposed=1500|limit=1000`
Enhanced: `RISK_REJECT|rule=MAX_LOSS_EXCEEDED|proposed=1500|limit=1000|severity=critical|ts=2026-02-16T10:05:00Z`

### 3. **Enhance RejectionPanel Data Structure**
```python
rejections_risk: List[RejectionDetail]           # Structured rejections
rejections_gatekeeper: List[RejectionDetail]     # Currently missing!
rejections_event: List[RejectionDetail]          # Currently missing!
rejections_correlation: List[RejectionDetail]    # Exists, enhance it
```

### 4. **Add Pipeline Stage Metadata**
```python
@dataclass
class PipelineSnapshot:
    stage: str                  # 'generated' | 'risk' | 'gatekeeper' | 'correlation' | 'final'
    candidate_count: int
    rejection_count: int
    status: str                 # 'normal' | 'warning' | 'critical' | 'success'
    timestamp: str
```

---

## Visual/UX Insights to Adopt

### 1. **Clear Visual Hierarchy**
- **Summary cards**: Most important info only (symbol, strategy, score)
- **Expandable details**: Less critical but valuable info on demand
- **Rejection tables**: Scannable format with time, code, description

### 2. **Status Color Coding (Recommended for Output)**
```
Risk Rejection    → Rose/Red (#ef4444)
Gatekeeper Alert  → Amber/Yellow (#f59e0b)
Correlation Issue → Indigo/Blue (#6366f1)
Event Block       → Amber/Yellow (#f59e0b)
Success           → Emerald/Green (#10b981)
```

### 3. **Monospace Fonts for Data**
- Reason codes: `font-mono`
- Timestamps: `font-mono`
- Prices/deltas: `font-mono`
- Makes scanning easier and looks professional

### 4. **Collapsible Sections**
- DecisionLog (already have!) ✅
- Trade details (leg structure, risk profile)
- Portfolio risk breakdown

---

## Missing Backend Features (Identified via UI)

1. **Rejection Severity Levels** - UI doesn't show, but necessary for prioritization
2. **Rejection Timestamps** - UI has them, we should track them
3. **Gatekeeper Rejection Logging** - UI has tab for it, DecisionLog doesn't track them separately
4. **Event Blocking Rejections** - Should be tracked as separate category
5. **Decision Timeline** - DecisionLog.tsx shows timeline of decisions, we show just final log

---

## API Contract for UI Integration

Based on UI expectations, DecisionLog JSON output should look like:
```json
{
  "symbol": "AAPL",
  "regime": "HIGH",
  "strategy_hint": "CREDIT_SPREAD",
  "blocking_events": [
    {
      "type": "earnings",
      "name": "Earnings",
      "reason_code": "EVENT_BLOCK|rule=EARNINGS|days_until=5",
      "severity": "critical"
    }
  ],
  "pipeline": [
    {"stage": "generated", "count": 142, "status": "normal", "timestamp": "2026-02-16T10:00:01Z"},
    {"stage": "risk", "count": 86, "status": "warning", "timestamp": "2026-02-16T10:00:15Z"},
    {"stage": "gatekeeper", "count": 42, "status": "normal", "timestamp": "2026-02-16T10:00:22Z"},
    {"stage": "correlation", "count": 12, "status": "normal", "timestamp": "2026-02-16T10:00:30Z"},
    {"stage": "final", "count": 5, "status": "success", "timestamp": "2026-02-16T10:00:35Z"}
  ],
  "rejections_by_category": {
    "risk": [
      {
        "id": "r1",
        "symbol": "TSLA",
        "strategy": "Short Straddle",
        "reason_code": "RISK_REJECT|rule=MAX_LOSS_EXCEEDED|proposed=1500|limit=1000",
        "severity": "critical",
        "timestamp": "2026-02-16T10:02:41Z"
      }
    ],
    "gatekeeper": [
      {
        "id": "g1",
        "symbol": "META",
        "strategy": "Iron Condor",
        "reason_code": "GATEKEEP_REJECT|rule=LOW_SCORE|score=65|threshold=70",
        "severity": "medium",
        "timestamp": "2026-02-16T10:03:12Z"
      }
    ],
    "correlation": [...],
    "event": [...]
  },
  "final_picks": [
    {
      "symbol": "SPX",
      "strategy": "Iron Condor",
      "gatekeeper_score": 92,
      "legs": [...]
    }
  ]
}
```

---

## Summary

✅ **We're Doing Well:**
- Structured reason codes (like reasonCode field)
- DecisionLog with candidate tracking
- Clear gate separation (Risk, Gatekeeper, Correlation)
- Type-safe data structures

⚠️ **Opportunities:**
- Add timestamps to rejection tracking
- Track gatekeeper rejections separately
- Add severity levels to reason codes
- Create pipeline stage snapshots
- Support decision timeline logging

🎯 **Next Steps for Future UI:**
1. Enhance DecisionLog to include pipeline stage metadata
2. Add severity/confidence scores to all rejection reasons
3. Implement timeline logging for decision events
4. Create JSON export format compatible with RejectionPanel UI expectations

---

## Component Reference for UI Implementation

| Component | Purpose | Inspired Backend Data |
|-----------|---------|----------------------|
| **Header** | Status overview, regime, alerts | Vol regime, blocking events |
| **PipelineBar** | Candidate flow visualization | Pipeline stage counts/status |
| **TradeCard** | Final pick display, detail expansion | Trade with legs, score breakdown |
| **RejectionPanel** | Categorized rejection display | Rejections by category + reason codes |
| **RiskDashboard** | Portfolio metrics | Risk analysis results |
| **DecisionLog** | Decision timeline | Structured log of all gate decisions |
| **StrategyControls** | Policy & parameter tuning | Mode, thresholds, filters |

---

## Design Files Location
```
ui-aistudio/
├── App.tsx                 # Main layout: 70% picks / 30% risk
├── components/
│   ├── Header.tsx         # Symbol, regime, alerts
│   ├── PipelineBar.tsx    # Candidate flow stages
│   ├── TradeCard.tsx      # Expandable trade details
│   ├── RejectionPanel.tsx # Tabbed rejections
│   ├── RiskDashboard.tsx  # Risk metrics
│   ├── DecisionLog.tsx    # Collapsible decision timeline
│   └── StrategyControls.tsx
├── constants.ts           # Mock data (PIPELINE_STAGES, MOCK_TRADES, MOCK_REJECTIONS)
├── types.ts              # TypeScript interfaces
└── vite.config.ts        # Build config
```
