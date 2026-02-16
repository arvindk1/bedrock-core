# Implementation Plan: "Hedge Fund Grade" Options System

## Goal
Build a robust, risk-first options trading system. This revision addresses "desk-level" gaps by formalizing metrics, ensuring execution realism, and integrating a full event calendar.

## Phase 1: The Core Infrastructure (Risk & Data Layers)

### 1. The Risk Engine (`agent/risk_engine.py`)
**Source:** `dynamic-options-v1/backend/services/risk_concentration_monitor.py`
**Goal:** Deterministic "No" Machine with precise definitions.
*   **Metric Definitions**:
    *   **`MAX_RISK_PER_TRADE`**: Defined as **Max Loss at Entry** (Cost of Debit Spread). For undefined risk (if added later), use **VaR(95)**.
    *   **`MAX_SECTOR_EXPOSURE`**: Hard cap (e.g., 25%) based on **GICS Sector**.
    *   **`MAX_CORRELATION`**: Reject trade if **60-day rolling correlation** of daily returns vs. current portfolio > 0.7.
    *   **Drawdown Limit**: "Circuit Breaker" - halt buying if daily loss > 2%.

### 2. The Volatility Model (`agent/vol_engine.py`)
**Source:** `dynamic-options-v1/backend/services/advanced_volatility_calculator.py`
**Goal:** Standardized Volatility Metrics for reliable signal generation.
*   **Logic**:
    *   **Standardized Vol**: Hybrid model (Historical + GARCH + IV).
    *   **Regime Detection**: Classifies environment as Low/Medium/High Vol.
    *   **Expected Move**: `calculate_expected_move(symbol, days, confidence=0.68)`.

### 3. The Event & Calendar Layer (`agent/event_loader.py`)
**Source:** `dynamic-options-v1/backend/services/earnings_intelligence.py`
**Goal:** Context-aware routing.
*   **Logic**:
    *   **Earnings Check**: `check_earnings_before_expiry(symbol)` -> hard reject for non-earnings plays.
    *   **Macro Events**: Manually loaded list (FOMC, CPI) to block execution windows.

---

## Phase 2: The Logic Engines (Gatekeeper & Scanner)

### 4. The Scored Gatekeeper (`agent/market_checks.py`)
**Goal:** Score execution viability with realistic checks.
*   **Liquidity Score (0-100)**:
    *   **Metric**: `min(Open Interest, NBBO Size * 100)`.
    *   **Pass**: Can we enter/exit `target_size` without taking > 2% of available liquidity?
*   **Spread Check**:
    *   **Pass**: `Ask - Bid < max(0.05, 0.01 * Bid)`.

### 5. Policy-Based Scanner (`agent/options_scanner.py`)
**Goal:** Regime-based Strategy Selection.
*   **Router Logic**:
    *   **Regime**: Bull Trend + Low Vol (`IV < RV` & `IV Percentile < 20`).
        *   **Strategy**: **Long Call / Bull Call Spread**.
    *   **Regime**: Neutral/Bull + High Vol (`IV > RV` & `IV Percentile > 50`).
        *   **Strategy**: **Bull Put Spread / Iron Condor**.
    *   **Regime**: Event (Earnings).
        *   **Strategy**: **Skip** (Default) or Long Straddle (if "Lotto" account).

---

## Phase 3: Trade Management (The "Exit Manager")

### 6. Execution Realism (`agent/execution_model.py`)
**Goal:** Simulate real-world friction.
*   **Slippage Model**:
    *   `expected_slippage = max(0.25 * spread, tick_size)`.
    *   **Spreads**: Pay slippage on **both legs**.
*   **Fill Probability**:
    *   **Limit Orders**: Assume fill only if price trades *through* limit.

### 7. Thesis-Based Exits (`agent/trade_manager.py`)
**Goal:** Algorithmically defined exits.
*   **Invalidation Logic**:
    *   **Technical**: Close below **Anchored VWAP** (from Swing Low) or **2x ATR(14)** trailing stop.
*   **Profit Taking**:
    *   **Scale Out**: Sell 50% at **Expected Move (1 Standard Deviation)**.
*   **Time Stop**:
    *   "If `days_held > 0.5 * DTE` and `profit < 0`: **Exit**."

---

## Phase 4: Architecture & Feedback (V3)

### Agent Logic (ReAct Loop)
1.  **Orchestrator**: "Bullish Tech. Max Risk $1,000. Regimes: Vol=Low, Trend=Up."
2.  **Scout**: "NVDA and AMD fit. Both passed Liquidity checks."
3.  **Risk Manager**: "NVDA sector exposure OK. Correlation check passed."
4.  **Analyst**: "Grouping as 'Semis Bull'. Structuring Debit Spreads."
5.  **Execution**: "Simulating Limit Buy @ Mid + Slippage."

### The "Statistical" Feedback Loop
*   **Feature Store**: At entry, record `[IV_Rank, IV_vs_RV, Spy_Trend_Score, Sector_RS]`.
*   **Analysis**:
    *   **Shapley Values**: "Higher IV_vs_RV was the #1 predictor of loss for Long Calls."
    *   **Optimization**: "Rule Change: Reject Long Calls if IV_vs_RV > 10%."

## Verification Plan
*   **Backtest (Robustness)**:
    *   **Window**: 3 Years (covering Low Vol -> High Vol -> Rate Hike regimes).
    *   **Method**: Walk-Forward Analysis (Train on Y1, Test on Y2).
*   **Paper Trade**:
    *   Live shadow trading with **Slippage Model** applied.
    *   "Rejected Trade" Audit Log: daily review of false positives.
