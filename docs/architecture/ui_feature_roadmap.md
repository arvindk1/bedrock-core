# Prioritized UI Feature Roadmap

Goal: Surface the full analytical power of the Bedrock backend engines (`RiskEngine`, `ScoredGatekeeper`, `VolEngine`) through intuitive, visual frontend components.

## Priority 1: The Strategy Sandbox (Interactive Gatekeeper)
**Backend Power Surfaced**: `ScoredGatekeeper` (`market_checks.py`)
- **The Gap**: The scanner automatically grades trades (0-100), but users cannot manually build a custom spread to see how the system would score it.
- **The Feature**: A new "Option Builder" modal or tab.
- **Functionality**: Users select a Symbol, Strategy (e.g., Credit Spread), Strikes, and Expiration. Clicking "Test Trade" pings `/api/gatekeeper/check`.
- **Visuals**: Instantly displays the resulting 0-100 score, explicit warning flags (e.g., "Counter-Regime" or "Spread too wide"), and a clear pass/fail badge *before* execution.

## Priority 2: Visual Volatility Curves & Expected Moves
**Backend Power Surfaced**: `VolEngine` (Hybrid GARCH/EWMA/Historical Model)
- **The Gap**: The "Event Volatility Context" card currently just shows static text numbers for 1σ and 2σ expected moves.
- **The Feature**: Upgrade the Context Card in the Analyze view.
- **Functionality**: Render a visual bell curve (Normal Distribution graph) or a price chart overlaid with standard deviation cones.
- **Visuals**: Plots the current price in the center, and visually shades the 1σ (68%) and 2σ (95%) expected move ranges based on the hybrid model's exact outputs, giving traders an instant geometric sense of risk.

## Priority 3: Dynamic Circuit Breakers & Heatmaps
**Backend Power Surfaced**: `RiskEngine` (`analyze_portfolio_risk`)
- **The Gap**: The Portfolio view shows text alerts but lacks a visceral warning system for hard limits.
- **The Feature**: Enhance the "Command Center" (Portfolio Tab).
- **Functionality**: 
  - *Daily Drawdown Thermometer*: A visual bar showing Today's P&L rapidly filling toward the red "Halt Trading" limit (e.g., -$150).
  - *Sector Limits Heatmap*: A visual heatmap turning Yellow, then Red when a sector (e.g., Tech) approaches its 25% maximum capital allocation.

## Priority 4: Geometric Trade Payoff Profiles
**Backend Power Surfaced**: `OptionsScanner` (Greeks and P&L Math)
- **The Gap**: The Scanner results show Max Profit/Loss and "Leg Structure" in text.
- **The Feature**: Expandable visual risk graphs in the trade cards.
- **Functionality**: When clicking a generated trade, show the classic "Options Tent/Slope" payoff diagram.
- **Visuals**: Illustrates the exact breakeven points at expiration and the risk/reward geometry, making it immediately clear why a trade was selected.

---
*Implementation Note: These visual features (Charts, Heatmaps, Bell Curves) will be significantly easier to build and maintain using a component-based framework (React/Recharts) rather than the current Vanilla JS/HTML setup.*
