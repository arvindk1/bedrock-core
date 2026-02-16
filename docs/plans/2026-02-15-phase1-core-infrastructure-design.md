# Phase 1 Design: Core Infrastructure (Risk, Volatility, Events)

## Goal
Audit, harden, and test the three Phase 1 modules from the Hedge Fund Grade Options System plan. Treat existing code as inspiration — review every line, follow Strands/AgentCore patterns, use bare imports, and create unit tests.

## Decisions
- **Data source**: yfinance (free, no API key)
- **Import style**: Bare imports (`from risk_engine import ...`) — matches Dockerfile flat COPY
- **No global singletons** — instantiate classes for testability
- **Thresholds as constructor params** with defaults matching the plan spec
- **Tests**: pytest with mocks (no network calls), parametrized edge cases

---

## Module 1: `risk_engine.py` — The "No" Machine

### What to keep (from existing)
- `RiskSeverity` enum (LOW/MEDIUM/HIGH/CRITICAL)
- `ConcentrationAlert` and `RiskMetric` dataclasses
- Strategy concentration limits with vol-regime adjustments
- `should_reject_trade()` → `(bool, reason)` interface
- `analyze_portfolio_risk()` → `(alerts, metrics)` interface

### What to add (gaps from plan)
- `MAX_RISK_PER_TRADE`: Dollar-based max loss check (cost of debit spread at entry)
- `MAX_SECTOR_EXPOSURE`: GICS sector grouping with 25% hard cap (not count-based)
- `MAX_CORRELATION`: 60-day rolling correlation vs portfolio, reject if > 0.7
- **Drawdown circuit breaker**: Halt new trades if daily portfolio loss > 2%
- Fix concentration calc: Use **dollar risk weighting**, not position count

### What to change
- Remove global `risk_engine = RiskConcentrationMonitor()` singleton
- Make all thresholds configurable via constructor params
- Move `VolRegime` enum to `vol_engine.py` (single source of truth)

### Interface
```python
class RiskEngine:
    def __init__(self, max_risk_per_trade=1000, max_sector_pct=0.25,
                 max_correlation=0.7, drawdown_halt_pct=0.02):
        ...

    def should_reject_trade(self, trade, portfolio, market_context) -> (bool, str|None)
    def analyze_portfolio_risk(self, positions, proposed, market_ctx) -> (alerts, metrics)
    def check_drawdown_halt(self, daily_pnl, portfolio_value) -> bool
    def check_correlation(self, symbol, portfolio_symbols) -> (bool, float)
```

---

## Module 2: `vol_engine.py` — Volatility Model

### What to keep
- Multi-model approach: Historical, GARCH(1,1), EWMA, IV, Hybrid ensemble
- `VolatilityResult` dataclass
- `GARCHParameters` dataclass
- `EnhancedExpectedMoveCalculator`

### What to add
- `VolRegime` enum (move here from risk_engine — LOW/MEDIUM/HIGH)
- `detect_regime(symbol)` — classify using IV vs HV comparison + IV percentile
- `calculate_iv_rank(symbol)` — real 52-week IV rank (replace placeholder `50.0`)
- `calculate_iv_percentile(symbol)` — percentile-based complement

### What to fix
- Async consistency: yfinance is sync — don't wrap sync calls in async without benefit
- Expected move formula: verify `sqrt(days/365)` vs `sqrt(days/252)` (trading vs calendar days)
- GARCH: Validate parameter bounds more carefully (alpha + beta < 1 stationarity)

### Interface
```python
class VolEngine:
    def calculate_volatility(self, symbol, model=HYBRID) -> VolatilityResult
    def detect_regime(self, symbol) -> (VolRegime, dict)
    def calculate_iv_rank(self, symbol, lookback_days=252) -> float  # 0-100
    def calculate_expected_move(self, symbol, price, days, confidence=0.68) -> dict
```

---

## Module 3: `event_loader.py` — Event Calendar

### What to keep
- `EarningsEvent` dataclass
- `check_earnings_before_expiry(symbol, dte)` → hard reject logic
- `get_earnings_proximity(symbol)` → days until earnings (7-day window)
- Cache with 4-hour TTL

### What to add
- **Macro event calendar**: Static FOMC/CPI/Jobs dates for current year
- `is_macro_blackout(date)` — returns True if within 1 trading day of FOMC/CPI
- `get_blocking_events(symbol, dte)` — unified check for earnings + macro events

### What to fix
- Replace mock earnings data with real yfinance `.earnings_dates` + fallback
- Simplify `get_earnings_analysis()` — remove unused fields
- Remove hardcoded forward dates

### Interface
```python
class EventLoader:
    def check_earnings_before_expiry(self, symbol, dte) -> dict|None
    def is_macro_blackout(self, target_date) -> (bool, str|None)
    def get_blocking_events(self, symbol, dte) -> list[dict]
    def get_earnings_proximity(self, symbol) -> int|None
```

---

## Testing Plan

| Test File | Covers | Key Cases |
|-----------|--------|-----------|
| `tests/test_risk_engine.py` | RiskEngine | Trade rejection, sector cap, correlation > 0.7, drawdown halt, empty portfolio |
| `tests/test_vol_engine.py` | VolEngine | Historical vol calc, GARCH convergence/fallback, regime detection, IV rank, expected move |
| `tests/test_event_loader.py` | EventLoader | Earnings inside/outside trade window, macro blackout, cache TTL, missing data fallback |

All tests use mocked yfinance data — no network calls.

---

## File Changes Summary

| File | Action |
|------|--------|
| `agent/risk_engine.py` | Rewrite — keep structure, add missing checks, fix concentration math |
| `agent/vol_engine.py` | Rewrite — add regime detection, IV rank, fix async, move VolRegime here |
| `agent/event_loader.py` | Rewrite — add macro calendar, use real earnings dates, simplify |
| `tests/test_risk_engine.py` | New |
| `tests/test_vol_engine.py` | New |
| `tests/test_event_loader.py` | New |
