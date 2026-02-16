# Tool API Surface — Phase 2 Integration

## Overview

**3 tools** with increasing sophistication, designed for different use cases:

1. **`scan_options`** — Simple, Phase 1 legacy
2. **`scan_options_with_strategy`** — Full orchestrated, Phase 2
3. **`check_trade_risk`** — Risk validation only, quick check

---

## Tool 1: scan_options (Legacy/Simple)

### Purpose
Find and rank the best liquid options contracts using Black-Scholes Greeks (delta, gamma, theta, vega).

### Signature
```python
@tool
def scan_options(
    symbol: str,
    start_date: str,
    end_date: str,
    top_n: int = 5,
) -> str
```

### Parameters
| Param | Type | Required | Default | Example |
|-------|------|----------|---------|---------|
| `symbol` | str | Yes | — | `"AAPL"` |
| `start_date` | str | Yes | — | `"2026-03-01"` |
| `end_date` | str | Yes | — | `"2026-06-01"` |
| `top_n` | int | No | 5 | 10 |

### Returns
```
Formatted table of ranked contracts (or error string)

Example output:
Strategy                    Expiration  Strike  Delta  Theta  Vega  Cost  Bang/Buck
───────────────────────────────────────────────────────────────────────────────
BULL_CALL_DEBIT_SPREAD      2026-03-20  150     0.35   0.12   0.05  $1.50  0.23
BULL_CALL_DEBIT_SPREAD      2026-04-17  155     0.28   0.10   0.04  $1.00  0.28
...
```

### Use Cases
- Quick exploration: "What spreads exist for AAPL in March?"
- No portfolio context needed
- No risk checks applied
- Good for learning / initial scan

### Limitations
- ❌ No event blocking (might trade on earnings)
- ❌ No vol regime routing (might sell premium in low vol)
- ❌ No risk gating (no concentration checks)
- ❌ No portfolio diversification checks

### Example Call
```
User: "Show me the top 10 call spreads for AAPL expiring in Q1 2026"
Agent: scan_options(symbol="AAPL", start_date="2026-01-01", end_date="2026-03-31", top_n=10)
```

---

## Tool 2: scan_options_with_strategy (Orchestrated / Full)

### Purpose
Full Phase 2 orchestration: **Events → Vol → Scan → Risk → Gatekeeper → Correlation → Ranking**

Integrates all Phase 2 engines into a desk-style workflow with full decision logging.

### Signature
```python
@tool
def scan_options_with_strategy(
    symbol: str,
    start_date: str,
    end_date: str,
    top_n: int = 5,
    portfolio_json: str = "[]",
    policy_mode: str = "tight",
) -> str
```

### Parameters
| Param | Type | Required | Default | Example |
|-------|------|----------|---------|---------|
| `symbol` | str | Yes | — | `"AAPL"` |
| `start_date` | str | Yes | — | `"2026-03-01"` |
| `end_date` | str | Yes | — | `"2026-06-01"` |
| `top_n` | int | No | 5 | 3 |
| `portfolio_json` | str | No | `"[]"` | `'[{"symbol":"MSFT","max_loss":500}]'` |
| `policy_mode` | str | No | `"tight"` | `"moderate"` \| `"aggressive"` |

### Portfolio JSON Format
```json
[
  {
    "symbol": "AAPL",
    "max_loss": 1500,
    "strategy": "BULL_CALL_SPREAD"
  },
  {
    "symbol": "MSFT",
    "max_loss": 800,
    "strategy": "PUT_CREDIT_SPREAD"
  }
]
```

### Policy Modes
| Mode | Per-Trade Max Loss |
|------|-------------------|
| `"tight"` | $1,000 |
| `"moderate"` | $2,000 |
| `"aggressive"` | $5,000 |

### Returns
**DecisionLog artifact** as formatted string:

```
================================================================================
📊 DECISION LOG: AAPL
================================================================================

🔍 CONTEXT:
  Regime: LOW
  Strategy Hint: DEBIT_SPREAD
  Blocking Events: 0

📈 CANDIDATES:
  Generated: 18
  After Risk Gate: 12
  After Correlation: 8
  Final Picks: 3

❌ RISK REJECTIONS (6):
  - IRON_CONDOR @ 150/155: Drawdown too high
  - SHORT_CALL @ 160: Sector cap exceeded

❌ CORRELATION REJECTIONS (4):
  - BULL_CALL_SPREAD: Correlation 0.78 with existing MSFT (threshold 0.70)
  - ...

✅ TOP PICKS:
  1. BULL_CALL_DEBIT_SPREAD (Exp: 2026-03-20)
     LONG $150 | Δ 0.35
     SHORT $155 | Δ 0.10
     Cost: $1.50 | Max Profit: $3.50

  2. BULL_CALL_DEBIT_SPREAD (Exp: 2026-04-17)
     ...

⚠️  Disclaimer: Informational only, not financial advice.
================================================================================
```

### Pipeline (What's Checked)

```
1. EVENT BLOCK (Hard Stop)
   ├─ Earnings dates in window?
   ├─ FOMC/CPI/Jobs report in window?
   └─ → NO candidates generated if blocking events exist

2. VOL REGIME DETECTION
   ├─ Detect regime (LOW/MEDIUM/HIGH)
   ├─ Compute strategy hint (DEBIT/CREDIT/VERTICAL)
   └─ → Route candidate generation

3. CANDIDATE GENERATION
   ├─ Scan all option chains
   ├─ Enrich with liquidity context (bid/ask/OI/volume)
   └─ → Raw candidates

4. RISK GATE (Hard Rejection)
   ├─ Per-trade max loss check
   ├─ Sector concentration cap
   ├─ Drawdown circuit breaker
   └─ → Candidates passing risk

5. SCORED GATEKEEPER (Soft Scoring)
   ├─ Liquidity check (OI proxy)
   ├─ Bid/ask spread check
   ├─ Regime alignment (IV rank)
   └─ → Score >= 70 passes

6. CORRELATION GATE (Diversification)
   ├─ Check vs top-3 portfolio positions
   ├─ Real correlations (prices) or fallback (sector heuristic)
   ├─ Pair-specific thresholds (same symbol/sector/different)
   └─ → Diversified candidates

7. FINAL RANKING
   ├─ Sort by: gatekeeper_score (primary)
   ├─ Then by: profit/cost ratio (secondary)
   └─ → Top N picks
```

### Use Cases
- Production trading (full gating + logging)
- Risk-aware scanning (portfolio context considered)
- Event-safe trading (earnings/macro blocked)
- Diversification (no over-concentration)
- Audit trail (DecisionLog shows all decisions)

### Advantages Over Tool 1
| Feature | scan_options | scan_options_with_strategy |
|---------|--------------|---------------------------|
| Event blocking | ❌ | ✅ |
| Vol regime routing | ❌ | ✅ |
| Risk gating | ❌ | ✅ |
| Liquidity scoring | ❌ | ✅ |
| Correlation checks | ❌ | ✅ |
| Decision logging | ❌ | ✅ |
| Portfolio context | ❌ | ✅ |

### Example Call
```
User: "Find 3 spreads for AAPL, considering my MSFT and GLD positions,
       use moderate risk, avoid March earnings window"

Agent: scan_options_with_strategy(
    symbol="AAPL",
    start_date="2026-04-01",  # After earnings
    end_date="2026-06-01",
    top_n=3,
    portfolio_json='[
        {"symbol":"MSFT","max_loss":800,"strategy":"BULL_CALL_SPREAD"},
        {"symbol":"GLD","max_loss":500,"strategy":"PUT_CREDIT_SPREAD"}
    ]',
    policy_mode="moderate"
)
```

---

## Tool 3: check_trade_risk (Risk Only)

### Purpose
Quick validation: Check if a **specific proposed trade** fits your risk policy **before executing**.

Useful for:
- Ad-hoc risk checks on pre-selected trades
- Verification before order submission
- What-if scenarios ("If I add this trade, do I still pass?")

### Signature
```python
@tool
def check_trade_risk(
    symbol: str,
    strategy: str,
    max_loss: float,
    portfolio_json: str = "[]",
) -> str
```

### Parameters
| Param | Type | Required | Default | Example |
|-------|------|----------|---------|---------|
| `symbol` | str | Yes | — | `"AAPL"` |
| `strategy` | str | Yes | — | `"BULL_CALL_DEBIT_SPREAD"` |
| `max_loss` | float | Yes | — | 1500.0 |
| `portfolio_json` | str | No | `"[]"` | `'[{"symbol":"MSFT","max_loss":500}]'` |

### Returns
```
✅ APPROVED: Trade fits risk profile. Max loss: $1500.00

OR

❌ REJECTED: [detailed reason]
  Example: "Sector concentration exceeded for TECHNOLOGY (total: $3200 > limit: $2500)"
```

### Use Cases
- Trader pre-check: "Can I take this trade?"
- Risk validation: "What's the max I can risk on this spread?"
- Portfolio impact: "If I add this, what happens to my concentration?"
- No discovery needed (user already knows the trade they want)

### Example Call
```
User: "I want to buy a BULL_CALL_SPREAD on AAPL with max loss of $1500.
       I already hold MSFT (max_loss=$800) and GLD (max_loss=$500).
       Can I do this?"

Agent: check_trade_risk(
    symbol="AAPL",
    strategy="BULL_CALL_DEBIT_SPREAD",
    max_loss=1500,
    portfolio_json='[
        {"symbol":"MSFT","max_loss":800},
        {"symbol":"GLD","max_loss":500}
    ]'
)

Response: ✅ APPROVED: Trade fits risk profile. Max loss: $1500.00
```

---

## Tool Selection Guide

### When to Use Each

```
┌─────────────────────────────────────────────────────────┐
│ User wants to...                  │ Use Tool            │
├─────────────────────────────────────────────────────────┤
│ Explore options for a symbol      │ scan_options        │
│ (no portfolio, no risk gating)     │                     │
├─────────────────────────────────────────────────────────┤
│ Find safe trades considering:      │ scan_options_with_  │
│ - Portfolio holdings               │ strategy            │
│ - Events (earnings/macro)          │ (RECOMMENDED)       │
│ - Risk limits                       │                     │
│ - Diversification needs            │                     │
├─────────────────────────────────────────────────────────┤
│ Check if a specific trade is OK    │ check_trade_risk    │
│ (already know what they want)      │                     │
└─────────────────────────────────────────────────────────┘
```

### Decision Tree

```
START: User has a request

├─ "Show me options for AAPL"
│  └─ No portfolio context?
│     └─ Use: scan_options ✓

├─ "Find trades for AAPL considering my portfolio"
│  └─ Want full discovery with gating?
│     └─ Use: scan_options_with_strategy ✓ (RECOMMENDED)

└─ "Can I take this trade: BULL_CALL_SPREAD on AAPL, max loss $1500?"
   └─ Already know the trade, just need risk check?
      └─ Use: check_trade_risk ✓
```

---

## Error Handling

All tools return error strings on failure:

```python
# Invalid JSON
"Error: Invalid portfolio JSON: Expecting value: line 1 column 1"

# Data unavailable
"Error scanning options for AAPL: ValueError: No option chain available"

# Risk engine failure
"Error during risk check: AttributeError: 'NoneType' object has no attribute 'get'"
```

---

## Future Tool Additions (Roadmap)

### Possible Phase 3 Tools
- `backtest_strategy()` — Test a strategy on historical data
- `optimize_portfolio()` — Rebalance portfolio for diversification
- `get_market_context()` — Check current vol regime, macro events, etc.
- `analyze_trade()` — Deep dive into Greeks, probabilities, scenarios
- `manage_position()` — Roll, close, or adjust existing trade

---

## Summary Table

| Tool | Complexity | Gating | Portfolio | Logging | Use Case |
|------|-----------|--------|-----------|---------|----------|
| `scan_options` | Simple | None | N/A | None | Exploration |
| `scan_options_with_strategy` | Full | All 6 gates | Yes | DecisionLog | **Production** ⭐ |
| `check_trade_risk` | Risk only | Risk only | Yes | Minimal | Pre-check |

---

## Best Practices

### ✅ DO

- **Use `scan_options_with_strategy`** for production trading (full gating)
- **Include portfolio context** when available (better diversification checks)
- **Use moderate/aggressive modes** only if comfortable with higher risk
- **Check DecisionLog** to understand why trades were rejected
- **Use `check_trade_risk`** before submitting orders (validation)

### ❌ DON'T

- Trade without risk checks (don't use `scan_options` for real money)
- Ignore blocking events (use full orchestration, not simple scan)
- Add unlimited leverage (respect policy_mode limits)
- Trade concentrated sectors (let correlation gate filter)
- Skip portfolio context if you have positions

---

## Implementation Details

### Tool Registration (Strands SDK)
```python
from strands.tools import tool

@tool
def scan_options(...) -> str:
    """Docstring becomes tool description for agent."""
```

### Tool Availability
- All 3 tools available to agent at runtime
- Agent chooses which to call based on user request
- Tools are synchronous (no async)
- Return strings (not structured data)

### Price Data Sources
- `MarketData` class fetches from yfinance
- Caching built-in for performance
- Graceful fallback if data unavailable
