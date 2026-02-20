# Frontend Gap Analysis

This document compares the *Ideal Frontend Architecture* against the *Current Live Frontend* (running on port 8080 via `ui/index.html` and `ui/app.js`).

## 1. Smart Scanner (Discovery Hub)
**Status: Strong Match**

The current frontend implements this exceptionally well:
- **Input Controls**: The "Analyze" view includes the full suite of inputs (Symbol, Dates, Policy, Top N). 
- **Context Header**: Real-time regime (e.g., MED VOL), IV Rank, and SPY Trend are wired in the header.
- **Results Grid**: Trade cards effectively show the strategy, premium, max risk/profit, overall score, and leg structure.
- **Pipeline Audit ("The Cemetery")**: The visual pipeline (Generated → Event → Risk → Gatekeeper → Correlation) is fully implemented. Clicking a stage shows the exact rejection reasons translated from backend codes (e.g., Risk, Gatekeeper tabs).

*Gap*: Minor UI polish needed for leg details. No missing core features.

## 2. Live Portfolio & Risk (Command Center)
**Status: Partial Match**

- **KPIs**: Capital Utilization (with fill bar), Net Delta, Daily P&L, and Net Greeks are present.
- **Positions Grid**: Fully scaffolded table for active positions, though it currently displays "No active positions" (likely relying on mocked or empty backend data).
- **Concentration**: Sector Concentration and Correlation Matrix charts are scaffolded but might need live data binding to act as true "Traffic Light" alerts.

*Gap*: The "Risk Alerts" container is static ("No critical alerts"). Hard circuit breaker thresholds are not explicitly visualized beyond the Daily Drawdown number. 

## 3. Strategy & Volatility Deep-Dive
**Status: Needs Work (Major Gaps)**

- **Volatility Tear Sheet**: 
  - *Current*: Has a robust "Event Volatility Context" card showing 1σ/2σ Expected Move Ranges, Annual/Daily Vol, IV Rank, and Event Policy (e.g., "PLAY"). 
  - *Gap*: Lacks a visual bell curve representation; currently relies on numeric text bands.
- **Gatekeeper Simulation (Sandbox)**:
  - *Current*: Not implemented. The user can run full scans, but cannot manually build a custom multi-leg spread to bounce off the `/api/gatekeeper/check` route for a score.
  - *Gap*: Requires a new UI view or modal for "Strategy Builder / Sandbox".

## 4. Technical Architecture
**Status: Architectural Pivot Required?**

- *Current State*: The frontend is a monolithic Vanilla HTML/JS/CSS implementation (`ui/index.html`, `ui/app.js`, `terminal.css`).
- *Ideal/Planned State*: Earlier documentation (`DASHBOARD_V2_GUIDE.md`, `IMPLEMENTATION_SUMMARY.md`) referenced a React-based component architecture (`dashboard-v2.jsx`). 
- *Gap*: The current live app achieves the visual and functional goals beautifully but lacks the React componentization. If the goal is a React architecture, the entire existing vanilla JS app needs to be ported. If the goal is to stick with vanilla JS, the documentation should be updated to reflect this reality.
