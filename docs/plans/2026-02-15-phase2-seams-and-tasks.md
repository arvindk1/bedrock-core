# Phase 2: Exact Seam Lines & Corrected Task Order

## Architecture (Fixed)

```
AGENT TOOL LAYER (tools.py)
  ↓
  ├─ scan_options(symbol, start_date, end_date, top_n)
  │   └─ Returns: formatted string (simple wrapper, unchanged)
  │
  └─ scan_options_with_context(symbol, start_date, end_date, top_n, portfolio, market_context, policy_mode)
      ↓
      [Decision Log initialized]
      ↓
      PHASE 2 ORCHESTRATION
      ├─ events_check(symbol, dte) → blocking events list ✏️ TASK 3
      ├─ vol_regime_check(symbol) → regime + rationale ✏️ TASK 2
      ├─ scanner_candidates(symbol, regime, expiry_window) → raw candidates ✏️ BASE (existing)
      ├─ risk_gate(candidates, portfolio, market_context) → scored+filtered ✏️ TASK 1 (reframed)
      ├─ correlation_check(candidate, portfolio_prices) → accept/reject ✏️ TASK 4
      └─ [Decision Log recorded + returned]
      ↓
      Returns: decision log with all steps traced
```

---

## NEW TASK ORDER (Least Painful)

### ✏️ TASK 6 → FIRST: Define the Tool API Contract

**File:** `agent/tools.py`

**What to add:**

```python
from strands.tools import tool

# Existing tool (UNCHANGED)
@tool
def scan_options(symbol: str, start_date: str, end_date: str, top_n: int = 5) -> str:
    """Simple wrapper, returns formatted string."""
    from options_scanner import find_cheapest_options
    return find_cheapest_options(symbol, start_date, end_date, top_n)


# ✅ NEW TOOL — This is the "orchestrator" tool
@tool
def scan_options_with_strategy(
    symbol: str,
    start_date: str,
    end_date: str,
    top_n: int = 5,
    portfolio_json: str = "[]",  # JSON string of portfolio positions
    policy_mode: str = "tight",  # "tight", "moderate", "aggressive"
) -> str:
    """
    Full Phase 2 orchestration: Events → Vol → Risk → Correlation → Return decision log.

    Args:
        symbol: Ticker
        start_date, end_date: Expiration window (YYYY-MM-DD)
        top_n: Return top N contracts
        portfolio_json: JSON string of portfolio positions (use for risk checks)
        policy_mode: "tight" (max_risk=$1000), "moderate" ($2000), "aggressive" ($5000)

    Returns:
        DecisionLog as JSON string + human-readable summary.
    """
    import json
    from orchestrator import full_scan_with_orchestration

    portfolio = json.loads(portfolio_json) if portfolio_json else []
    result = full_scan_with_orchestration(
        symbol, start_date, end_date, top_n, portfolio, policy_mode
    )
    return result.to_formatted_string()


# ✅ NEW TOOL — Risk-only gatekeeper for trade approval
@tool
def check_trade_risk(
    symbol: str,
    strategy: str,
    max_loss: float,
    portfolio_json: str = "[]",
) -> str:
    """
    Check if a proposed trade fits risk policy.

    Returns: approval status + reasoning.
    """
    import json
    from risk_engine import RiskEngine

    portfolio = json.loads(portfolio_json) if portfolio_json else []
    engine = RiskEngine()

    trade = {
        "symbol": symbol,
        "strategy_type": strategy,
        "max_loss": max_loss,
        "sector": symbol,
    }

    rejected, reason = engine.should_reject_trade(trade, portfolio, {})

    if rejected:
        return f"❌ REJECTED: {reason}"
    else:
        return f"✅ APPROVED: Trade fits risk profile"
```

**Tests:**
```python
def test_scan_options_returns_string():
    # Existing tool still works
    pass

def test_scan_options_with_strategy_returns_decision_log():
    # New tool returns DecisionLog JSON
    pass

def test_check_trade_risk_rejects_oversized():
    # Risk gate works as standalone tool
    pass
```

---

### ✏️ TASK 2: Vol Regime Routing (in orchestrator layer)

**File:** Create `agent/orchestrator.py`

**What to add:**

```python
from vol_engine import VolEngine, VolRegime
from event_loader import EventLoader

class DecisionLog:
    """Artifact capturing: inputs, regime, events, candidates, rejections, picks."""

    def __init__(self, symbol: str, start_date: str, end_date: str):
        self.symbol = symbol
        self.start_date = start_date
        self.end_date = end_date
        self.regime = None
        self.blocking_events = []
        self.candidates_raw = []
        self.candidates_accepted = []
        self.candidates_rejected = []
        self.correlation_checks = {}

    def to_formatted_string(self) -> str:
        """Human-readable output for agent."""
        output = f"\n{'='*80}\nDECISION LOG: {self.symbol}\n"
        output += f"Regime: {self.regime.value if self.regime else 'Unknown'}\n"
        output += f"Blocking Events: {len(self.blocking_events)}\n"
        output += f"Candidates (Raw): {len(self.candidates_raw)}\n"
        output += f"Candidates (Accepted): {len(self.candidates_accepted)}\n"
        output += f"{'='*80}\n"
        return output


def vol_and_events_context(symbol: str, dte: int):
    """
    ✏️ TASK 2 + TASK 3 SEAM

    Returns: regime, blocking events, strategy hint
    """
    vol_engine = VolEngine()
    event_loader = EventLoader()

    # Vol regime
    regime, vol_details = vol_engine.detect_regime(symbol)

    # Events
    blocking = event_loader.get_blocking_events(symbol, dte)

    # Strategy hint based on regime
    if regime == VolRegime.LOW:
        strategy_hint = "DEBIT_SPREAD"  # Buy premium cheap
    elif regime == VolRegime.HIGH:
        strategy_hint = "CREDIT_SPREAD"  # Sell premium expensive
    else:
        strategy_hint = "VERTICAL_SPREAD"  # Neutral

    return {
        "regime": regime,
        "vol_details": vol_details,
        "blocking_events": blocking,
        "strategy_hint": strategy_hint,
    }


def full_scan_with_orchestration(
    symbol: str,
    start_date: str,
    end_date: str,
    top_n: int,
    portfolio: list,
    policy_mode: str = "tight",
) -> DecisionLog:
    """
    ✏️ MAIN ORCHESTRATION (Tasks 1-4)

    Call graph:
      1. Vol/Events context (TASK 2 + 3)
      2. Scan candidates (base scanner)
      3. Risk gate (TASK 1)
      4. Correlation gate (TASK 4)
    """
    from options_scanner import find_cheapest_options
    from risk_engine import RiskEngine

    log = DecisionLog(symbol, start_date, end_date)

    # TASK 2+3: Get regime and events
    context = vol_and_events_context(symbol, 45)
    log.regime = context["regime"]
    log.blocking_events = context["blocking_events"]

    # Hard block if earnings within window
    if context["blocking_events"]:
        earnings = [e for e in context["blocking_events"] if e.get("type") == "earnings"]
        if earnings:
            log.candidates_accepted = []
            return log  # Early exit

    # TASK 1: Generate candidates, then risk gate
    candidates = find_cheapest_options(symbol, start_date, end_date, top_n=50)
    log.candidates_raw = candidates

    # Risk gate
    engine = RiskEngine(max_risk_per_trade=policy_to_limit(policy_mode))
    accepted = []
    for candidate in candidates:
        rejected, reason = engine.should_reject_trade(candidate, portfolio, {})
        if rejected:
            log.candidates_rejected.append((candidate, reason))
        else:
            accepted.append(candidate)

    # TASK 4: Correlation gate (if portfolio_prices available)
    for candidate in accepted:
        # Correlation check (see Task 4 seam below)
        pass

    log.candidates_accepted = accepted[:top_n]
    return log

def policy_to_limit(mode: str) -> float:
    return {"tight": 1000, "moderate": 2000, "aggressive": 5000}.get(mode, 1000)
```

**Tests:**
```python
def test_low_vol_returns_debit_strategy_hint():
    context = vol_and_events_context("AAPL", 45)
    # Mock vol_engine to return LOW regime
    assert context["strategy_hint"] == "DEBIT_SPREAD"

def test_earnings_event_blocks_all_candidates():
    log = full_scan_with_orchestration("AAPL", "2026-02-15", "2026-02-20", ...)
    # Mock earnings in 2 days
    assert len(log.candidates_accepted) == 0
```

---

### ✏️ TASK 3: Event Blocking (seam in orchestrator)

**File:** `agent/orchestrator.py` (see above)

**Key seam:** `vol_and_events_context()` calls `event_loader.get_blocking_events()`

**What you DON'T need to change in `event_loader.py`** — it already has:
- `check_earnings_before_expiry(symbol, dte)` ✅
- `get_blocking_events(symbol, dte)` ✅
- `is_macro_blackout(date)` ✅

**Only fix needed in `event_loader.py`:** Task 5 (macro year-lock) — separate.

---

### ✏️ TASK 1 (REFRAMED): Risk Gate in Orchestrator

**File:** `agent/orchestrator.py` (see above in `full_scan_with_orchestration`)

**Key change:** Risk gate is applied AFTER scanning, not inside `find_cheapest_options()`.

**To do:**
1. Leave `find_cheapest_options()` as-is (simple wrapper → formatted string)
2. In `orchestrator.full_scan_with_orchestration()`, create raw candidates, then gate them
3. `options_scanner.find_cheapest_options()` should be refactored to `generate_candidates()`
   (no risk gating, just ranked list)

**Refactor in `options_scanner.py`:**

```python
# ❌ DELETE or KEEP AS-IS for backward compat: find_cheapest_options()

# ✅ ADD NEW FUNCTION:
def generate_candidates(
    symbol: str,
    start_date: str,
    end_date: str,
) -> List[Dict]:
    """
    Generate raw candidate spreads (NO risk gating, just greeks + liquidity).

    Returns: List of dicts with:
      - symbol, strategy, expiration, legs, cost, max_profit, dte
    """
    # (Extract the scanning logic from find_cheapest_options)
    # No RiskEngine calls here!
```

**Tests:**
```python
def test_risk_gate_rejects_oversized_in_orchestrator():
    log = full_scan_with_orchestration(
        "AAPL", ..., portfolio=[], policy_mode="tight"
    )
    # Oversized trade should be in log.candidates_rejected
    assert any("exceeds" in r[1].lower() for r in log.candidates_rejected)
```

---

### ✏️ TASK 4: Correlation Gate

**File:** `agent/orchestrator.py`

**Define the contract:**

```python
def correlation_gate(
    candidate: Dict,
    portfolio: List[Dict],
    portfolio_prices: Dict[str, List[float]],  # { "AAPL": [150.2, 150.5, ...], ... }
    max_correlation: float = 0.7,
) -> Tuple[bool, Optional[str]]:
    """
    Check if candidate is too correlated with top-N largest portfolio positions.

    Args:
        candidate: Trade dict with symbol
        portfolio: List of positions
        portfolio_prices: Dict mapping symbol → price series (required!)
        max_correlation: Threshold (0.7 default)

    Returns:
        (rejected: bool, reason: str|None)
    """
    if not portfolio_prices:
        return False, None  # No data, pass through

    from risk_engine import RiskEngine
    engine = RiskEngine(max_correlation=max_correlation)

    candidate_symbol = candidate["symbol"]
    candidate_prices = portfolio_prices.get(candidate_symbol)
    if not candidate_prices:
        return False, None  # No price history, pass through

    # Check vs TOP 3 largest positions by risk
    portfolio_by_risk = sorted(
        portfolio,
        key=lambda p: p.get("max_loss", 0),
        reverse=True
    )[:3]

    for pos in portfolio_by_risk:
        pos_symbol = pos["symbol"]
        pos_prices = portfolio_prices.get(pos_symbol)
        if not pos_prices:
            continue

        corr = engine.calculate_correlation(
            np.array(candidate_prices),
            np.array(pos_prices)
        )

        if corr > max_correlation:
            return True, f"Correlation {corr:.2f} too high vs {pos_symbol}"

    return False, None
```

**Integrate into orchestrator:**

```python
def full_scan_with_orchestration(...):
    # ... risk gate ...

    # TASK 4: Correlation gate
    # Caller MUST provide portfolio_prices in market_context
    # Example caller (in app.py or agent system prompt):
    #   portfolio_prices = {
    #       "AAPL": fetch_prices("AAPL"),
    #       "MSFT": fetch_prices("MSFT"),
    #   }
    #   market_context = {"portfolio_prices": portfolio_prices}

    portfolio_prices = {}  # Caller responsibility to populate

    final_candidates = []
    for candidate in accepted:
        corr_rejected, corr_reason = correlation_gate(
            candidate, portfolio, portfolio_prices
        )
        if corr_rejected:
            log.correlation_checks[candidate["symbol"]] = corr_reason
        else:
            final_candidates.append(candidate)

    log.candidates_accepted = final_candidates[:top_n]
    return log
```

**Tests:**
```python
def test_correlation_gate_rejects_highly_correlated():
    # portfolio has AAPL (largest)
    # candidate is MSFT
    # portfolio_prices shows 0.85 correlation
    rejected, reason = correlation_gate(msft_candidate, [aapl_pos], prices_dict)
    assert rejected is True
    assert "Correlation" in reason

def test_no_prices_passes_through():
    rejected, reason = correlation_gate(candidate, [], {})
    assert rejected is False
```

---

### ✏️ TASK 5: Macro Year-Lock Fix (Option A — Fail Loudly)

**File:** `agent/event_loader.py`

**Change:**

```python
def _build_macro_calendar(self) -> List[Dict[str, Any]]:
    """Build static macro event calendar."""
    from datetime import date

    today = date.today()
    current_year = today.year

    if current_year not in [2026, 2027]:  # Supported years
        logger.warning(
            f"⚠️ Macro calendar not available for {current_year}. "
            f"Only 2026-2027 are supported. Add dates or fetch from source."
        )
        return []  # Empty calendar = no macro events blocked

    # Build for current year
    if current_year == 2026:
        fomc_dates = FOMC_DATES_2026
        cpi_dates = CPI_DATES_2026
        jobs_dates = JOBS_DATES_2026
    else:  # 2027
        fomc_dates = FOMC_DATES_2027  # Add these next year
        cpi_dates = CPI_DATES_2027
        jobs_dates = JOBS_DATES_2027

    events = []
    for d in fomc_dates:
        events.append({"name": "FOMC Decision", "date": d, "impact": "high"})
    for d in cpi_dates:
        events.append({"name": "CPI Release", "date": d, "impact": "high"})
    for d in jobs_dates:
        events.append({"name": "Jobs Report", "date": d, "impact": "medium"})

    return events
```

**Add at top of file:**

```python
# Placeholder for 2027 (populate early Dec 2026)
FOMC_DATES_2027 = [
    # TODO: Update from https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm
    # date(2027, 1, 26), ...
]
CPI_DATES_2027 = []  # TODO: Monthly ~10-13th
JOBS_DATES_2027 = []  # TODO: First Friday each month
```

**Tests:**
```python
def test_current_year_loads_calendar():
    loader = EventLoader()
    assert len(loader.macro_events) > 0

def test_unsupported_year_logs_warning(caplog):
    # Fake being in 2030
    with patch('event_loader.date.today', return_value=date(2030, 1, 1)):
        loader = EventLoader()
        assert "not available for 2030" in caplog.text
        assert len(loader.macro_events) == 0
```

---

### ✏️ TASK 7: Update Agent Orchestration

**File:** `agent/app.py`

**Change:**

```python
from tools import scan_options, scan_options_with_strategy, check_trade_risk

SYSTEM_PROMPT = """You are a hedge-fund-grade options advisor.

WORKFLOW:
1. Use check_trade_risk() to validate risk profile FIRST.
2. Use scan_options_with_strategy() to find best opportunities with regime routing.
3. Explain the decision log: regime, blocking events, why contracts passed risk checks.

Always disclose: informational only, not financial advice.
"""

def create_agent() -> Agent:
    model = BedrockModel(...)
    return Agent(
        model=model,
        tools=[scan_options, scan_options_with_strategy, check_trade_risk],  # ✅ All three
        system_prompt=SYSTEM_PROMPT,
    )
```

---

### ✏️ TASK 8: Integration Test

**File:** `tests/test_phase2_integration_e2e.py`

**Pseudo-code:**

```python
def test_full_workflow_low_vol_regime():
    """User asks for AAPL trade → agent uses all tools → returns decision log."""
    # Mock Vol Engine to return LOW regime
    # Mock Event Loader to return no blocking events
    # Mock RiskEngine to accept small trade

    # Call agent with "Find best AAPL calls for Mar 2026"
    # Verify agent calls scan_options_with_strategy
    # Verify output includes regime, candidates, decision log

def test_earnings_blocks_trade():
    """Earnings event in window → candidates rejected."""
    # Mock earnings in 5 days
    # Verify agent returns "No opportunities (earnings block)"

def test_high_correlation_filters_candidate():
    """Portfolio has AAPL; candidate MSFT correlated → filtered out."""
    # Mock portfolio_prices with 0.8 correlation
    # Verify MSFT is in candidates_rejected
```

---

## Summary: New Task Order

| Order | Task | File | Purpose |
|-------|------|------|---------|
| 1 | **TASK 6** | `tools.py` | Define 3 tools: `scan_options` (simple), `scan_options_with_strategy` (orchestrated), `check_trade_risk` |
| 2 | **TASK 2** | `orchestrator.py` (NEW) | Vol regime routing + strategy hint |
| 3 | **TASK 3** | `orchestrator.py` | Event blocking (use existing `event_loader`) |
| 4 | **TASK 1** | `orchestrator.py` + `options_scanner.py` | Risk gate (refactor `find_cheapest_options` → `generate_candidates`) |
| 5 | **TASK 4** | `orchestrator.py` | Correlation gate with explicit `portfolio_prices` contract |
| 6 | **TASK 7** | `app.py` | Register 3 tools; update system prompt |
| 7 | **TASK 8** | `tests/` | E2E integration tests (decision log artifacts) |
| 8 | **TASK 5** | `event_loader.py` | Macro year-lock (fail loudly, add 2027 placeholders) |

---

## Key Contracts

### 1. `market_context` dict shape

```python
market_context = {
    "daily_pnl": float,          # Today's P&L
    "portfolio_value": float,    # Total portfolio value
    "portfolio_prices": {        # ← REQUIRED for correlation gate
        "AAPL": [150.2, 150.5, 151.0, ...],  # Last N prices
        "MSFT": [300.1, 299.8, ...],
    },
}
```

### 2. `DecisionLog` structure

```python
{
    "symbol": "AAPL",
    "regime": "LOW",
    "blocking_events": [{"type": "earnings", "date": "2026-02-20"}],
    "candidates_raw": 12,
    "candidates_accepted": 3,
    "candidates_rejected": [
        ("BULL_CALL_SPREAD @ 150/155", "Exceeds max risk $1000"),
        ("BULL_CALL_SPREAD @ 155/160", "Correlation 0.8 vs MSFT"),
    ],
}
```

---

## Implementation Checklist

- [ ] Task 6: Create `tools.py` with 3 tools
- [ ] Task 2: Create `orchestrator.py` with vol/events context
- [ ] Task 3: Integrate event loader into orchestrator
- [ ] Task 1: Refactor scanner, add risk gate to orchestrator
- [ ] Task 4: Add correlation gate with portfolio_prices contract
- [ ] Task 5: Fix macro year-lock (fail loudly)
- [ ] Task 7: Update app.py, register tools, update prompt
- [ ] Task 8: Write integration tests with DecisionLog checks

