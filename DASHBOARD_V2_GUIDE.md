# 🎨 Desk Command Dashboard v2 — Design & Implementation Guide

## Overview

Dashboard v2 introduces **Phase 1 improvements** based on professional trading UI patterns from HedgeDesk:

- **Left Navigation Sidebar** (collapsible, shows regime + quick stats)
- **KPI Card Grid** (4 metric cards at top for instant context)
- **Refined Brutalism Aesthetic** (institutional, data-dense, precise)
- **Improved Visual Hierarchy** (easier scanning and decision-making)

---

## Design Philosophy: Refined Brutalism

### Core Aesthetic Principles

| Principle | Implementation |
|-----------|-----------------|
| **Institutional** | No visual fluff, grid-based layout, professional color palette |
| **Data-Dense** | Monospace metrics, high information density without clutter |
| **Precise** | Exact spacing, careful typography, purposeful accents |
| **Scannable** | Clear hierarchy (serif headers → mono data), color coding |
| **Dark Theme** | Navy primary (#0F172A), reduced eye strain for traders |

### Color Palette

```css
--color-bg-primary: #0f172a    /* Navy - main background */
--color-bg-secondary: #1e293b  /* Lighter navy - cards/sections */
--color-accent: #f59e0b        /* Amber - critical info, hover states */
--color-success: #10b981       /* Emerald - positive metrics */
--color-danger: #ef4444        /* Crimson - rejections, warnings */
--color-info: #3b82f6          /* Blue - neutral data */
```

### Typography

```css
Headers:    Playfair Display (serif) — authority, institutional feel
Metrics:    IBM Plex Mono (monospace) — data clarity, scannability
UI Labels:  System font (sans-serif) — readability
```

---

## Layout Architecture

### Grid System

```
┌────────────────────────────────────────────────────────┐
│                   240px SIDEBAR (fixed)                │
│  ┌─────────────────────────────────────────────────┐  │
│  │ LOGO & TOGGLE                                   │  │
│  ├─────────────────────────────────────────────────┤  │
│  │ NAVIGATION (5 items with icons)                 │  │
│  ├─────────────────────────────────────────────────┤  │
│  │ REGIME INDICATOR (HIGH/MEDIUM/LOW badge)        │  │
│  ├─────────────────────────────────────────────────┤  │
│  │ QUICK STATS (Capital %, P&L, Positions)         │  │
│  ├─────────────────────────────────────────────────┤  │
│  │ SETTINGS LINK                                   │  │
│  └─────────────────────────────────────────────────┘  │
│                                                        │
│           MAIN CONTENT AREA (1fr width)               │
│  ┌─────────────────────────────────────────────────┐  │
│  │ KPI GRID (4 cards: Regime, Trend, Policy, Risk)│  │
│  ├─────────────────────────────────────────────────┤  │
│  │ SCAN FORM (Symbol, Dates, Policy, Portfolio)   │  │
│  ├─────────────────────────────────────────────────┤  │
│  │ GATE FUNNEL (Visual pipeline: 5 stages)        │  │
│  ├─────────────────────────────────────────────────┤  │
│  │ PICKS TABLE (Ranked results)                   │  │
│  ├─────────────────────────────────────────────────┤  │
│  │ REJECTIONS (Risk | Gatekeeper | Correlation)   │  │
│  ├─────────────────────────────────────────────────┤  │
│  │ DECISION LOG (Audit trail)                     │  │
│  └─────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────┘
```

### Component Hierarchy

```jsx
<DashboardV2>
  <Sidebar />                    // Collapsible left nav
  <div className="dashboard-content">
    <KPIGrid />                  // 4 metric cards
    <ScanForm />                 // User input
    <GateFunnel />               // Visual pipeline
    <PicksTable />               // Results
    <Rejections />               // Why trades failed
    <DecisionLog />              // Audit trail
  </div>
</DashboardV2>
```

---

## Component Details

### 1. Sidebar (240px)

**Features:**
- Logo with toggle button (→/←)
- 5 navigation items with icons
- Regime indicator (HIGH/MEDIUM/LOW) with color coding
- Quick stats (Capital %, Daily P&L, Position count)
- Settings link

**Behavior:**
- Collapses to 80px (icon-only mode)
- Fixed position (stays visible during scroll)
- Responsive: becomes horizontal bar on mobile

**CSS Classes:**
```css
.sidebar
.sidebar.collapsed
.sidebar-header
.logo / .logo-icon / .logo-text
.sidebar-nav
.nav-item (with hover state)
.sidebar-regime
.regime-badge
.sidebar-stats
.stat-row
```

### 2. KPI Card Grid (4x)

**Cards:**
1. **Market Regime** — Volatility level (HIGH/MEDIUM/LOW)
2. **SPY Trend** — Market direction (Uptrend/Downtrend)
3. **Policy Mode** — Risk limits (Tight/Moderate/Aggressive)
4. **Macro Risk** — Blocking events (None/FOMC/Earnings/etc)

**Design:**
- Card with subtle top border accent (animates on hover)
- Large monospace metric value (28px)
- Small uppercase label (11px)
- Subtext for context

**CSS Classes:**
```css
.kpi-grid
.kpi-card
.kpi-card--positive / --negative
.kpi-header / .kpi-title / .kpi-indicator
.kpi-value
.kpi-subtext
```

### 3. Gate Funnel

**Visual Representation:**
```
GENERATED       ████████████████████ 142
RISK GATE       ████████████████    86
GATEKEEPER      ██████████          42
CORRELATION     ████████            12
FINAL PICKS     ██                   3
```

**Color Coding:**
- Gray (#64748B) — Generated
- Red (#EF4444) — Risk Gate
- Amber (#F59E0B) — Gatekeeper
- Blue (#3B82F6) — Correlation
- Green (#10B981) — Final Picks

**CSS Classes:**
```css
.gate-funnel
.funnel-title
.funnel-stages
.funnel-stage
.stage-label / .stage-bar-container / .stage-bar / .stage-count
```

### 4. Picks Table

**Columns:**
| Rank | Strategy | Expiration | Cost | Max Loss | Max Profit | Score |
|------|----------|-----------|------|----------|-----------|-------|
| 1 | Bull Call Debit | Mar 20 | $1.20 | $120 | $380 | 84 |

**Styling:**
- Monospace for numbers
- Hover rows highlight with amber background
- Red text for negative values (Max Loss)
- Green text for positive values (Max Profit)
- Score displayed in amber badge

**CSS Classes:**
```css
.picks-section
.picks-table
.picks-table thead / tbody
.rank / .strategy / .cost / .max-loss.negative / .max-profit.positive
.score-badge
```

### 5. Rejections

**Grouped by Category:**
- ❌ **Risk Rejections** (red accent)
- ⚠️ **Gatekeeper Rejections** (amber accent)
- 🔗 **Correlation Rejections** (blue accent)

**Display:**
- 3-column grid on desktop
- Each category is a card with left-colored border
- Lists rejection reasons
- Shows "+X more" if truncated

**CSS Classes:**
```css
.rejections-section
.rejection-tabs
.rejection-category
.rejection-category h4
```

### 6. Decision Log

**Format:**
```
Regime:                    HIGH
Strategy Hint:             CREDIT_SPREAD
Generated:                 12
Risk Passed:               9
Gatekeeper Passed:         6
Correlation Passed:        4
Final Picks:               3
Timestamp:                 2026-02-16T09:47:32Z
```

**Styling:**
- Monospace values (data clarity)
- Left column labels (fixed width 180px)
- Audit trail appearance (like system logs)

**CSS Classes:**
```css
.decision-log-section
.decision-log
.log-row
.log-label / .log-value
```

---

## Responsive Behavior

### Desktop (>1024px)
- Sidebar fixed on left (240px)
- 4-column KPI grid
- Full table visible

### Tablet (768px - 1024px)
- Sidebar still fixed but narrower (80px icon-only on small tablets)
- 2-column KPI grid
- Rejection cards stack 2x2

### Mobile (<768px)
- Sidebar becomes horizontal tabs at top
- KPI grid becomes 1 column
- Form inputs full-width
- Tables become card-based or horizontal scrollable
- All text sizes reduce for readability

**Media Query Breakpoints:**
```css
@media (max-width: 1024px) { ... }
@media (max-width: 768px) { ... }
@media (max-width: 480px) { ... }
```

---

## CSS Variables (Customization)

All colors, spacing, and transitions use CSS variables for easy theming:

```css
/* Colors */
--color-bg-primary: #0f172a
--color-bg-secondary: #1e293b
--color-accent: #f59e0b
--color-success: #10b981
--color-danger: #ef4444

/* Spacing (4px base unit) */
--spacing-xs: 4px
--spacing-sm: 8px
--spacing-md: 16px
--spacing-lg: 24px
--spacing-xl: 32px

/* Typography */
--font-serif: 'Playfair Display'
--font-mono: 'IBM Plex Mono'
--font-sans: system fonts

/* Transitions */
--transition-fast: 150ms
--transition-normal: 300ms
```

---

## How to Use

### 1. Replace Current Dashboard

**Option A: Direct replacement** (if ready)
```bash
# Backup current version
cp ui-aistudio/dashboard.jsx ui-aistudio/dashboard.backup.jsx
cp ui-aistudio/dashboard.css ui-aistudio/dashboard.backup.css

# Use v2
cp ui-aistudio/dashboard-v2.jsx ui-aistudio/dashboard.jsx
cp ui-aistudio/dashboard-v2.css ui-aistudio/dashboard.css
```

**Option B: Side-by-side** (test first)
- Keep both versions
- Create `index.html` with toggle to switch between them
- A/B test with users

### 2. Modify index.html

Update the import to use v2:
```jsx
// ui-aistudio/index.html
import DashboardV2 from './dashboard-v2.jsx';

ReactDOM.render(
  <DashboardV2 />,
  document.getElementById('root')
);
```

### 3. Test Locally

```bash
cd ui-aistudio
python -m http.server 8080
# Navigate to http://localhost:8080/index.html
```

### 4. Verify Components

- [ ] Sidebar toggle works (→/← button)
- [ ] KPI cards display correctly
- [ ] Scan form submits to `/api/scan`
- [ ] Gate funnel animates properly
- [ ] Picks table shows real data
- [ ] Rejections categorized correctly
- [ ] Decision log readable
- [ ] Responsive on mobile (test with DevTools)

---

## Future Enhancements (Phase 2+)

### Phase 2: Add Decision Inspector
```jsx
<DecisionInspector
  steps={[
    { time: '10:00:01', status: 'pass', label: 'Regime detected' },
    { time: '10:00:05', status: 'fail', label: 'Risk gate' },
  ]}
/>
```
- Timestamped pipeline log
- Code-like appearance
- Collapsible details

### Phase 3: Live Positions Tab
```jsx
<LivePositions
  positions={[
    { symbol: 'SPY', strategy: 'Iron Condor', pnl: '+$650' }
  ]}
/>
```
- Active trades management
- Greeks display
- P&L tracking
- Risk alerts with icons

### Phase 4: Correlation Heatmap
```jsx
<CorrelationMatrix
  data={correlations}
  assets={['SPY', 'QQQ', 'TLT']}
/>
```
- Portfolio overlap visualization
- Color-coded correlation strength

---

## Accessibility Considerations

- [ ] Keyboard navigation (Tab through sidebar, forms)
- [ ] Color contrast ratios (WCAG AA minimum)
- [ ] ARIA labels on sidebar items
- [ ] Focus indicators on buttons
- [ ] Semantic HTML (buttons, labels, tables)
- [ ] Mobile touch targets (min 44px)

---

## Performance Notes

### CSS Optimization
- Uses CSS Grid (native browser optimization)
- Transitions use GPU-accelerated properties (transform, opacity)
- Minimal repaints with will-change on hover states
- No JavaScript animations (CSS-only)

### React Optimization
- Components use React.memo (avoid unnecessary re-renders)
- useMemo for expensive calculations
- Lazy load data tables (if >100 rows)

### Bundle Size
- CSS: ~25KB (unminified)
- JSX: ~12KB (unminified)
- Total: ~37KB (can compress to ~10KB gzipped)

---

## Theming (Optional)

To create a light theme, modify CSS variables:

```css
:root.light-theme {
  --color-bg-primary: #f8f9fa;
  --color-bg-secondary: #ffffff;
  --color-text-primary: #1a1a1a;
  --color-text-secondary: #4a4a4a;
  --color-border: #e0e0e0;
  --color-accent: #d97706; /* darker amber */
}
```

Then toggle in JavaScript:
```jsx
document.documentElement.classList.toggle('light-theme');
```

---

## Troubleshooting

**Sidebar not collapsing?**
- Check toggle button click handler
- Verify `.sidebar.collapsed` CSS rule applies

**KPI cards not showing?**
- Verify `apiData` or `mockData` is passed correctly
- Check `gridTemplateColumns` media queries

**Funnel stages look wrong?**
- Ensure `funnel` prop has keys: generated, afterRisk, afterGatekeeper, etc.
- Check bar width calculations

**Table not responsive?**
- Test with DevTools mobile emulation
- Check media queries are applied

---

## Summary

Dashboard v2 provides a **professional, institutional-grade interface** that:

✅ Improves visual hierarchy (sidebar + KPI cards)
✅ Maintains refined brutalism aesthetic
✅ Keeps all existing functionality
✅ Works on all device sizes
✅ Uses CSS variables for easy customization
✅ Optimized for trader workflows

Ready for production deployment with optional Phase 2+ enhancements.

---

**Questions?** Refer to the component code in `dashboard-v2.jsx` or CSS in `dashboard-v2.css` for details.
