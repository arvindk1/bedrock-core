# Ideal Frontend Architecture

Based on the capabilities of the backend options trading engine, an ideal frontend should seamlessly expose the underlying data, orchestrator stages, and telemetry, ensuring users can take action with full transparency.

## Core Philosophical Goals
1. **Radical Transparency**: The user should never wonder *why* the backend rejected a trade. Every decision, from an earnings block to an insufficient correlation score, must be prominently explained using the structured reason codes.
2. **Speed to Insight**: Options data is dense. The UI must aggressively prioritize actionable metrics (Risk/Reward, Max Profit, Probability of Profit, DTE) and highlight strategy alignment with volatility regimes.
3. **Auditability**: Provide a clear "Decision Log" view that mirrors the backend pipeline, allowing traders to review the system's logic stage-by-stage.

## Ideal Views

### 1. Smart Scanner (The Discovery Hub)
*Purpose: Initiate orchestration pipelines and view resulting candidates.*

- **Input Controls**:
  - Ticker Symbol, Start/End Dates, Max Trades, and Policy Mode (Tight/Loose).
- **Context Header**:
  - Real-time `MarketData` snapshot.
  - Detected `VolRegime` (Low, Medium, High).
  - Upcoming macro/earnings events (from `EventLoader`).
- **Results Grid (The "Picks")**:
  - Displays candidates that passed the **full** orchestration pipeline.
  - Columns needed: Strategy Type, Expiration (DTE), Strikes, Max Profit/Loss, R/R Ratio, Premium, and execution capability.
  - Expandable rows detailing the exact Option Legs (Bid/Ask/Volume/OI) and the calculated Risk properties.
- **Pipeline Audit (The "Cemetary")**:
  - A prominent section showing *rejected* candidates.
  - Integrates the `reason_codes` parser to display human-readable translations:
    - *"Rejected: AAPL vs MSFT Correlation 0.85 (over 0.70 threshold)."*
    - *"Rejected: Bid/Ask Spread > 5% on 150C Leg."*
    - *"Blocked: Earnings in 4 Days."*

### 2. Live Portfolio & Risk Engine (The Command Center)
*Purpose: Monitor active positions and evaluate aggregate risk metrics.*

- **Concentration Alerts**:
  - Visual warnings (Traffic Light / Heatmap style) sourced from `RiskEngine.analyze_portfolio_risk()`.
  - Display "Sector Limits" (e.g., Tech is at 35% capacity vs. 25% allow).
- **Drawdown Circuit Breakers**:
  - A clear indicator of today's P&L vs. the `drawdown_halt_pct` threshold, alerting if the system is approaching a halt.
- **Existing Positions Grid**:
  - Current trades showing real-time valuation, remaining DTE, and "Days Held."

### 3. Strategy & Volatility Deep-Dive
*Purpose: Expose the "Why" behind the `VolEngine` and `OptionsScanner`.*

- **Volatility Tear Sheet**:
  - Displays the `VolatilityResult` dataclass output for a given symbol.
  - Breaks down the hybrid score (Historical vs GARCH vs EWMA).
  - Shows IV Rank and percentiles over 252 days.
  - Visualizes the normalized Bell Curve the `VolEngine` predicts for the next 30/60/90 days.
- **Gatekeeper Simulation (Sandbox)**:
  - An interactive tool connecting to `/api/gatekeeper/check`.
  - The trader can arbitrarily build a spread and see how the soft-filtering scores it (0-100) based on Liquidity, Spreads, and Regime Alignment *without* committing it to a portfolio.

## Technical Execution
- **State Management**: Robust handling of complex asynchronous responses, especially pulling out the `DecisionLog` and `reason_codes` effectively.
- **Visuals**: Dark mode, data-dense brutalist typography, and clear red/yellow/green color coding for risk alerts.
- **Components**: Reusable, atomic components for rendering option legs, tooltips for reason codes, and progress bars for execution scores.
