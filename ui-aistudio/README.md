# 🛡️ Desk Command — Professional Trading Dashboard

A sophisticated, institutional-grade frontend for the hedge fund options desk system. Emphasizes **risk transparency**, **decision clarity**, and **professional workflow**.

## Design Philosophy

This dashboard is NOT a retail scanner. It's a **desk risk manager** interface that:

✅ Shows what survived professional filtering  
✅ Explains why trades were rejected  
✅ Enforces portfolio discipline  
✅ Prevents correlated bet stacking  
✅ Tracks performance drivers  

The emotional tone: **"The system is protecting me. I understand why this trade exists. It acts like a desk risk manager."**

---

## Core Components

### 1️⃣ **Landing Dashboard — Market Context Bar**

```
Vol Regime: HIGH | SPY Trend: Uptrend | Macro Risk: FOMC in 3 days ⚠️ | Policy: Tight ($1,000)
```

**Purpose**: Immediate context before scanning.

**Design**:
- Monospace fonts for precision
- Color-coded regime status (green=LOW, amber=MEDIUM, red=HIGH)
- Real-time market state at a glance
- Policy limits always visible

---

### 2️⃣ **Gate Flow Funnel Visualization**

Shows the progression through filtering stages:

```
Generated:    12   ████████████
Risk Gate:     9   █████████
Gatekeeper:    6   ██████
Correlation:   4   ████
Final Picks:   3   ███
```

**Purpose**: Build trust through transparency. Users see exactly how many survived each gate.

**Features**:
- Animated bar charts with smooth transitions
- Color gradient showing filtering intensity
- Counts at each stage
- Reveals rejection logic implicitly

---

### 3️⃣ **Blocking Events Banner**

```
⚠️ Earnings (5 days until)
System blocked new positions inside trade window.
```

**Purpose**: Hard rejection explanation. No surprise blocks.

**Features**:
- Amber/red warning colors
- Clear reason statement
- Dismissible
- Prevents user confusion

---

### 4️⃣ **Final Picks Table**

| Rank | Strategy | Exp | Cost | Max Loss | Max Profit | Score |
|------|----------|-----|------|----------|-----------|-------|
| 1 | Bull Call Debit | Mar 20 | $1.20 | $120 | $380 | 84 |
| 2 | Bull Call Debit | Mar 20 | $1.00 | $100 | $250 | 79 |
| 3 | Bull Call Debit | Mar 20 | $0.85 | $85 | $180 | 73 |

**Purpose**: Quick scan of top candidates ranked by gatekeeper score.

**Design**:
- Monospace fonts for price/data
- Color-coded: red=risk, green=reward, blue=score
- Click row → detailed drill-down
- DTE, breakeven, legs, warnings

**Drill-Down Modal**:
```
Trade Overview          Leg Details         Gatekeeper Assessment
─────────────           ───────────         ─────────────────────
Expiration: Mar 20      Long Call 420       ✓ Passed
Cost: $1.20             Delta: 0.65         
Max Loss: $120          IV: 22%             Warnings:
Max Profit: $380        ...                 • None
Breakeven: $425
```

---

### 5️⃣ **Rejections Tab — The Transparency Engine**

This is the most important feature. Shows:

**❌ Risk Rejections**
- Max loss $1,500 exceeds limit $1,000
- Sector Technology cap exceeded
- Concentration: Already 3x NVDA exposure

**❌ Gatekeeper Rejections**
- Leg 1 bid/ask spread too wide (1.8% > 1.5%)
- Market impact 3.2% exceeds 2% threshold
- Open interest below threshold for short strike

**❌ Correlation Rejections**
- Correlation 0.78 with AAPL exceeds threshold 0.70
- Correlation 0.72 with QQQ exceeds threshold 0.70

**Purpose**: Transform "why was this rejected?" into actionable insight.

**Design**:
- Three-column grid: Risk | Gatekeeper | Correlation
- Each category color-coded
- Specific thresholds shown
- Builds credibility ("system actually has rules")

---

### 6️⃣ **Decision Log — Audit Trail**

```
Regime: HIGH
Strategy Hint: CREDIT_SPREAD
Blocking Events: None

Gate Progression:
  Generated 12 → Risk Gate 9 → Gatekeeper 6 → Correlation 4 → Final 3

Timestamp: 2026-02-16T14:32:45Z
```

**Purpose**: Perfect for:
- Paper trading review
- Backtest comparison
- Threshold tuning
- Compliance audits

---

### 7️⃣ **Trade Management View**

For live positions:

| Symbol | Strategy | Entry | Current P/L | Expected Move | DTE | Status |
|--------|----------|-------|-------------|----------------|-----|--------|
| NVDA | Bull Call Debit | $2.50 | +15.2% | $2.10 | 18 | Active |

**Features**:
- Entry price tracking
- Live P/L
- Expected move (from vol engine)
- Days to expiration
- Scale-out hints
- DTE < 30 warnings

---

## Aesthetic Direction: Refined Brutalism

### Color Palette
```css
--color-bg-primary: #0F172A       (deep charcoal)
--color-bg-secondary: #1E293B     (slate)
--color-text-primary: #F1F5F9     (near-white)
--color-text-secondary: #CBD5E1   (light gray)
--color-pass: #10B981             (emerald)
--color-reject: #EF4444           (crimson)
--color-warning: #F59E0B          (amber)
--color-info: #3B82F6             (steel blue)
```

### Typography
- **Display**: Playfair Display (serif, authoritative)
- **Data/Code**: IBM Plex Mono (precision)
- **Body**: System fonts (readable, clean)

### Motion
- Smooth bar animations (0.6s cubic-bezier)
- Staggered funnel reveals
- Table row hover states
- Modal slide-up entries

---

## File Structure

```
ui-aistudio/
├── dashboard.jsx          # Main React component
├── dashboard.css          # Styling & animations
├── index.html            # Demo/standalone HTML
└── README.md             # This file
```

---

## Integration with Backend

### Expected API Endpoints

The dashboard expects these backend endpoints (connect via `ui/server.py`):

```bash
POST /api/scan
  {
    symbol: "NVDA",
    start_date: "2026-03-01",
    end_date: "2026-06-01",
    top_n: 5,
    portfolio_json: "[]",
    policy_mode: "tight"
  }
  
Response:
  {
    regime: "HIGH",
    spyTrend: "Uptrend",
    macroRisk: "FOMC in 3 days",
    blockingEvents: [],
    gateFunnel: {
      generated: 12,
      afterRisk: 9,
      afterGatekeeper: 6,
      afterCorrelation: 4,
      final: 3
    },
    picks: [
      { rank: 1, strategy: "Bull Call Debit", ... },
      ...
    ],
    rejections: {
      risk: [...],
      gatekeeper: [...],
      correlation: [...]
    },
    decisionLog: { ... }
  }
```

---

## How to Use

### Standalone Demo
```bash
# Open in browser
open ui-aistudio/index.html

# Or serve locally
python -m http.server 8000 --directory ui-aistudio
```

### React Integration
```jsx
import TradingDashboard from './ui-aistudio/dashboard.jsx';

export default function App() {
  return <TradingDashboard />;
}
```

### With FastAPI Backend
```python
# ui/server.py should already have these endpoints:
@app.post("/api/scan")
async def scan_symbol(request: ScanRequest):
    # Call agent with orchestration
    # Return decision log, picks, rejections
    pass
```

---

## What Makes This Different

### ❌ Retail Apps Do:
- Show contracts
- Show Greeks
- Let users gamble

### ✅ This System Does:
- Shows what survived professional filtering
- Explains why rejected
- Enforces portfolio discipline
- Prevents correlated stacking
- Tracks performance drivers

---

## Emotional Design

Users should feel:

> "The system is protecting me."  
> "I understand why this trade exists."  
> "It acts like a desk risk manager."  
> "It doesn't hide rejections."

If it feels like a scanner → failed.  
If it feels like a structured trading desk → succeeded.

---

## Next Steps

1. **Connect to Backend**: Update API endpoints in dashboard components
2. **Add Live Data**: Replace mock data with real orchestrator output
3. **Add Trade Management**: Connect to live position tracking
4. **Add Performance Metrics**: Link to backtest results
5. **Mobile Responsiveness**: Optimize for tablets/mobile (already has responsive CSS)

---

## Architecture Notes

- **React 18** for component state & reactivity
- **Pure CSS** animations (no external animation library)
- **CSS Variables** for theming consistency
- **Accessibility**: Semantic HTML, ARIA labels where needed
- **Performance**: Lazy component loading, memoized calculations

---

## Typography & Spacing

- **Header**: Playfair 36px, -1px letter spacing (authority)
- **Section Title**: Playfair 20px, -0.5px letter spacing
- **Table Header**: Mono 11px, uppercase, 0.5px spacing
- **Body**: 14px, 1.6 line height
- **Padding**: 32px main, 24px sections, 16px cards
- **Gaps**: 24px between major sections, 12px within

---

## Color Usage

- **Emerald (#10B981)**: Pass, approval, success
- **Crimson (#EF4444)**: Reject, danger, hard stop
- **Amber (#F59E0B)**: Warning, caution, soft alert
- **Steel Blue (#3B82F6)**: Info, neutral, UI chrome
- **Deep Charcoal**: Background (authority, focus)

---

## Questions?

This is a reference implementation. Adapt the aesthetic, layout, and features to your specific needs. The key principle: **transparency first, risk managed always**.

