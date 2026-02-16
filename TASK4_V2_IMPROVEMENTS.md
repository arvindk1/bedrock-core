# Task 4: Correlation Gate v2 Improvements

## Status: ✅ UPGRADED
Implemented production-grade correlation gate addressing 5 critical design gaps.

---

## What Changed

### v1 → v2: Design Issues Fixed

| Issue | v1 Problem | v2 Solution |
|-------|-----------|-----------|
| **Correlation Model** | Heuristic only (sector-based) | Real correlations + heuristic fallback |
| **Pair-Specific Logic** | Took max correlation, single threshold | Reject on ANY pair > pair-specific threshold |
| **Portfolio Check** | Checked all positions | Check only top 3 by risk_dollars |
| **Threshold Redundancy** | `_get_correlation_threshold()` recomputed sectors | Compute once, pass once |
| **Reason Codes** | Free text ("Correlation X with Y") | Structured codes ("CORR_REJECT\|candidate=A\|vs=B\|corr=0.78\|threshold=0.70\|basis=prices") |

---

## CorrelationGate v2: Detailed Improvements

### 1. Real Return Correlations (Primary)

```python
def _rolling_corr(a_prices, b_prices, lookback=60) -> Optional[float]:
    """
    Compute Pearson correlation of daily returns (preferred method).

    Algorithm:
    1. Take most recent N prices (up to lookback days, default 60)
    2. Compute daily returns: r = Δprice / price_yesterday
    3. Pearson correlation on returns
    4. Return None if < 20 data points or NaN/Inf
    """
```

**Why this matters:**
- Sector heuristic is deterministic but coarse
- Real correlations capture actual co-movement
- Fallback gracefully if data unavailable

**Example:**
```python
# Same sector but different volatility profiles
aapl_prices = [150, 151, 152, ...]  # Tech, stable
amd_prices = [100, 95, 110, ...]    # Tech, volatile
corr = 0.45  # Real correlation, not assumed 0.70

# Threshold: same_sector=0.70
# Decision: ACCEPT (0.45 < 0.70, despite same sector)
```

### 2. Pair-Specific Thresholds (Correct Logic)

**Wrong (v1):**
```python
# Take ONE max correlation
worst_corr = max([corr_vs_AAPL, corr_vs_MSFT, corr_vs_NVDA])
# Apply single threshold (e.g., 0.70)
if worst_corr > 0.70: reject
```

**Right (v2):**
```python
# Check EACH pair with pair-specific threshold
for pos in portfolio:
    threshold = _pair_threshold(candidate, pos)  # Varies by relationship
    if corr > threshold:
        track_violation()  # Different thresholds for different relationships!
```

**Example:**
```python
# Candidate: AAPL spread
# Portfolio: [AAPL call, MSFT call, SPY call]

# vs AAPL call: corr=0.95, threshold=0.90 (same symbol) → REJECT
# vs MSFT call: corr=0.72, threshold=0.70 (same sector) → REJECT
# vs SPY call: corr=0.25, threshold=0.30 (different) → OK

# Result: REJECT (failed on first check, use most severe reason)
```

### 3. Top-3 Risk-Weighted Positions Only

```python
# Rank all portfolio positions by risk_dollars
ranked = sorted(portfolio, key=lambda p: p.get("risk_dollars", 0.0), reverse=True)
check_positions = ranked[:3]  # Only top 3

# Rationale:
# - Conserves computation (O(3) instead of O(n))
# - Focuses on material risk factors
# - Avoids micro-positions diluting analysis
```

**Why this matters:**
- Portfolio might have 50+ positions
- Only top 3 matter for diversification
- Scales linearly regardless of portfolio size

**Contract requirement:**
```python
portfolio = [
    {
        "symbol": "AAPL",
        "risk_dollars": 1500.0,  # ← NEW: Used for ranking
        "strategy": "BULL_CALL_SPREAD",
    },
    {
        "symbol": "MSFT",
        "risk_dollars": 800.0,
        "strategy": "PUT_CREDIT_SPREAD",
    },
    # ...rest of positions
]
```

### 4. Standardized Reason Codes

**Format:**
```
CORR_REJECT|candidate=AAPL|vs=MSFT|corr=0.78|threshold=0.70|basis=prices
```

**Parsing example:**
```python
reason = "CORR_REJECT|candidate=AAPL|vs=MSFT|corr=0.78|threshold=0.70|basis=prices"
parts = reason.split("|")
# parts[0] = "CORR_REJECT"
# parts[1] = "candidate=AAPL"
# parts[2] = "vs=MSFT"
# parts[3] = "corr=0.78"
# parts[4] = "threshold=0.70"
# parts[5] = "basis=prices"  # "prices" | "heuristic" | "unknown_default"
```

**Benefits:**
- Machine-parseable (not free text)
- Includes basis: "prices" (real data), "heuristic" (sector fallback), "unknown_default" (conservative)
- Easy analytics: count rejections by basis, threshold, etc.

### 5. Fallback Strategy

**Priority:**
1. Try real correlation on prices (if available)
2. Fall back to sector heuristic (if prices too short)
3. Conservative default if can't determine (0.80)

```python
def _corr_from_prices_or_fallback(...) -> Tuple[float, str]:
    # Try real correlation
    corr = _rolling_corr(c_px, p_px, self.lookback)
    if corr is not None:
        return corr, "prices"  # Real data

    # Fallback to sector heuristic
    if c_sym == p_sym: return 0.95, "heuristic"
    if same_sector: return 0.70, "heuristic"
    if diff_sector: return 0.20, "heuristic"

    # Last resort: conservative default
    return 0.80, "unknown_default"  # Assume correlated (safer)
```

---

## Backward Compatibility

✅ **All existing tests pass unchanged**

The v2 implementation is drop-in compatible:
```python
# v1 call (still works)
accepted, rejections = corr_gate.filter_candidates(candidates, portfolio)

# v2 enhanced call (now possible)
accepted, rejections = corr_gate.filter_candidates(
    candidates,
    portfolio=portfolio,
    portfolio_prices={"AAPL": [150, 151, 152, ...], ...},
    candidate_prices={"MSFT": [350, 351, 352, ...], ...},
)
```

---

## Orchestrator Integration (Next Step)

Currently, orchestrator calls:
```python
after_correlation, corr_rejections = corr_gate.filter_candidates(
    scored_candidates, portfolio  # ← Missing price data
)
```

**Recommended update:**
```python
# In full_scan_with_orchestration():
portfolio_prices = context.get("portfolio_prices", {})  # Injected or loaded
candidate_prices = context.get("candidate_prices", {})  # Injected or loaded

after_correlation, corr_rejections = corr_gate.filter_candidates(
    scored_candidates,
    portfolio=portfolio,
    portfolio_prices=portfolio_prices,
    candidate_prices=candidate_prices,
)
```

**Data sources (examples):**
```python
# Option 1: Load from MarketData
market_data = MarketData()
aapl_prices = market_data.get_price_history("AAPL", days=60)
msft_prices = market_data.get_price_history("MSFT", days=60)

# Option 2: Pre-fetch in agent initialization
portfolio_prices = {
    pos["symbol"]: market_data.get_price_history(pos["symbol"], days=60)
    for pos in portfolio
}

# Option 3: Shared context (fastest)
context = {
    "portfolio_prices": {...},
    "candidate_prices": {...},
}
```

---

## Example: v2 in Action

### Scenario: AAPL candidate, mixed portfolio

```
Portfolio:
  1. AAPL call (risk=$1500) — same symbol
  2. MSFT call (risk=$800)  — same sector (tech)
  3. GLD call  (risk=$200)  — different sector

Candidate: AAPL spread

Analysis (v2):
  Top-3 ranked: AAPL ($1500), MSFT ($800), GLD ($200)

  vs AAPL (top 1):
    Real correlation: 0.92 (from prices)
    Threshold: 0.90 (same symbol)
    Status: REJECT (0.92 > 0.90)
    Reason: "CORR_REJECT|candidate=AAPL|vs=AAPL|corr=0.92|threshold=0.90|basis=prices"

  (Stop here — already rejected)

Result: Candidate REJECTED
```

### Scenario: MSFT candidate, tech-heavy portfolio

```
Portfolio:
  1. AAPL call (risk=$1500) — same sector
  2. NVDA call (risk=$1200) — same sector
  3. GOOGL call (risk=$900) — same sector
  4. GLD call (risk=$200)   — different sector (not in top-3)

Candidate: MSFT spread

Analysis (v2):
  Top-3 ranked: AAPL ($1500), NVDA ($1200), GOOGL ($900)

  vs AAPL (top 1):
    Real correlation: 0.68 (from prices)
    Threshold: 0.70 (same sector)
    Status: OK (0.68 < 0.70)

  vs NVDA (top 2):
    Real correlation: 0.65
    Threshold: 0.70
    Status: OK (0.65 < 0.70)

  vs GOOGL (top 3):
    Real correlation: 0.69
    Threshold: 0.70
    Status: OK (0.69 < 0.70)

  All pairs OK.

Result: Candidate ACCEPTED
```

---

## Config Customization

### Looser Policy (More Diversification Required)

```python
corr_gate = CorrelationGate(
    lookback=90,  # Longer window (more history)
    top_n_positions=5,  # Check more positions
    thresholds={
        "same_symbol": 0.85,      # Stricter
        "same_sector": 0.60,      # Stricter
        "different_sector": 0.25, # Stricter
    }
)
```

### Tighter Policy (Fewer Constraints)

```python
corr_gate = CorrelationGate(
    lookback=30,  # Shorter window (recent only)
    top_n_positions=2,  # Check only top 2
    thresholds={
        "same_symbol": 0.95,      # Looser
        "same_sector": 0.80,      # Looser
        "different_sector": 0.40, # Looser
    }
)
```

---

## Next Steps (Roadmap)

### Phase 2.5: Orchestrator Integration
- [ ] Pass portfolio_prices and candidate_prices to filter_candidates()
- [ ] Ensure portfolio positions include risk_dollars field
- [ ] Update decision log to parse standardized reason codes
- [ ] Add basis tracking: "prices" vs "heuristic" vs "unknown_default"

### Phase 3: Advanced Correlation
- [ ] Implement dynamic thresholds based on portfolio vol regime
- [ ] Add "correlation coefficient of determination" (R²) metric
- [ ] Track correlation drift over time
- [ ] Multi-position correlation (e.g., "all tech down 5%")

### Phase 3.5: ML-Based Diversification
- [ ] Learn optimal thresholds from backtesting
- [ ] Predict correlation regime shifts
- [ ] Optimize portfolio allocation under correlation constraints

---

## Summary

✅ **CorrelationGate v2 ready for production:**
- Real correlations (prices) + heuristic fallback
- Pair-specific thresholds (not one-size-fits-all)
- Top-3 risk-weighted filtering (scalable)
- Standardized rejection codes (parseable + attributable)
- Backward compatible (all tests pass)

**Next action:** Integrate into orchestrator by passing portfolio_prices/candidate_prices and populating risk_dollars in portfolio positions.
