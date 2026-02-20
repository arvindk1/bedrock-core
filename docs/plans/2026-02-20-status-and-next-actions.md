# Decision Intelligence UI — Engineering Status Report
**As of:** 2026-02-20  **Time window:** 02/19–02/20

---

## 🔹 A. Executive Summary

- **Overall progress: ~55% of full "real trading platform" vision** (Decision Intelligence UI: 100% done; Data Layer + Live Wiring: 0%)
- **Biggest wins (02/19–02/20):** All 6 tasks in the Decision Intelligence impl plan shipped — pipeline journey per pick, no-trades explanation, display_reason + severity colors, 202/202 tests passing
- **Biggest remaining gap:** The Positions view, market snapshot, and events calendar are 100% hardcoded mock data in `server.py`; no persistent data layer exists
- `config.yaml` exists with `total_cash_balance`, `max_sector_concentration_pct`, etc. — but `server.py` does NOT load it; values are not surfaced to the UI
- `risk_engine.py` does load from `config.yaml` (via `load_risk_config()` at line 29), but `server.py` does not inject `portfolio_value` into scan context
- The `live_backend_migration.md` architecture doc defines exactly what needs to happen in 6 phases — this is the existing plan to build on
- No persistent store (DB, file) exists for portfolios or positions yet

---

## 🔹 B. "Yesterday vs Today" Changelog

**02/19 (yesterday):**
- `014d641` feat: enrich final picks with pipeline journey and strategy reasoning (orchestrator.py)
- `53061ad` fix: no_trades_explanation at all early returns + WARN funnel count
- `d619c1e` feat: display_reason, severity, noTradesExplanation in scan API response (server.py)
- `876be81` feat: pipeline journey panel in expanded trade cards (app.js)
- `6c0f6ae` feat: structured no-trades explanation card (app.js)
- `5450d4e` feat: severity colors in rejection tabs (app.js)

**02/20 (today):**
- `6edfaf6` fix: restore 2026 macro event calendar dates + fix UI title assertion → 202/202 tests passing
- Status report produced; "wire up real data" planning underway

---

## 🔹 C. Task Status Table

| ID | Task | Source Plan | Area | Status | Evidence | Next Step |
|----|------|-------------|------|--------|----------|-----------|
| DI-01 | Per-trade pipeline journey (orchestrator.py) | impl-plan Task 1 | Backend | ✅ Done | commit 014d641; `_build_pipeline_journey` in orchestrator.py | — |
| DI-02 | No-trades explanation (orchestrator.py) | impl-plan Task 1 | Backend | ✅ Done | commit 53061ad; `_build_no_trades_explanation` at all 6 early returns | — |
| DI-03 | display_reason + severity + noTradesExplanation in /api/scan | impl-plan Task 2 | Backend | ✅ Done | commit d619c1e; `_enrich_rejections`, `_severity_for_rule` in server.py | — |
| DI-04 | Pipeline journey panel in trade cards (app.js) | impl-plan Task 3 | UI | ✅ Done | commit 876be81; `renderPipelineJourney()` added | — |
| DI-05 | Zero-picks "Why No Trades" card (app.js) | impl-plan Task 4 | UI | ✅ Done | commit 6c0f6ae; `renderNoTradesCard()` added | — |
| DI-06 | Human-readable rejection reasons with severity colors | impl-plan Task 5 | UI | ✅ Done | commit 5450d4e; `switchRejectionTab` uses display_reason | — |
| DI-07 | Integration verification (202 tests pass) | impl-plan Task 6 | Test | ✅ Done | 202 passed 2026-02-20 | — |
| EC-01 | Create config.yaml with account + risk limits | externalize plan | Config | ✅ Done | config.yaml exists at repo root | — |
| EC-02 | risk_engine.py loads from config.yaml | externalize plan | Backend | ✅ Done | `load_risk_config()` at line 29 of risk_engine.py | — |
| EC-03 | server.py reads config.yaml at startup | externalize plan | Backend | ❌ Not Started | server.py has no config loading code | Add `load_config()` to server.py startup |
| EC-04 | Inject total_cash_balance into scan market_context | externalize plan | Backend | ❌ Not Started | scan endpoint doesn't pass portfolio_value | Wire config → orchestrator market_context |
| EC-05 | Expose /api/config endpoint for frontend | externalize plan | Backend | ❌ Not Started | no such route in server.py | Add GET /api/config |
| LB-P1A | Externalize all hardcoded limits to config | live_backend_migration Phase 1 | Config | 🚧 Partial | config.yaml exists, risk_engine reads it; server.py doesn't | Complete EC-03/04/05 |
| LB-P1B | Setup SQLAlchemy + PostgreSQL/SQLite data layer | live_backend_migration Phase 1 | Data Layer | ❌ Not Started | no DB code anywhere | Schema + SQLAlchemy setup |
| LB-P1C | Define Portfolio, Position, DecisionAudit models | live_backend_migration Phase 1 | Data Layer | ❌ Not Started | no ORM models | Create models.py |
| LB-P2A | /api/portfolio/risk — live from DB + RiskEngine | live_backend_migration Phase 2 | Backend | ❌ Not Started | 100% hardcoded mock in server.py:303 | After DB layer |
| LB-P2B | /api/market/snapshot — live vol + regime | live_backend_migration Phase 2 | Backend | 🚧 Partial | price is live (market_data.get_current_price); IV rank/vol/regime hardcoded | Call vol_engine.detect_regime() live |
| LB-P2C | /api/events/calendar — live from EventLoader | live_backend_migration Phase 2 | Backend | ❌ Not Started | 100% hardcoded AAPL/MSFT dates in server.py:403 | Call EventLoader live |
| LB-P3A | /api/trade/execute endpoint (paper trade to DB) | live_backend_migration Phase 3 | Backend | ❌ Not Started | no route exists | After DB layer |
| LB-P3B | Mark-to-market background daemon | live_backend_migration Phase 3 | Backend | ❌ Not Started | no background worker | After trade execution |
| LB-P4A | Strategy Sandbox (/api/gatekeeper/check wired to UI) | live_backend_migration Phase 4 + roadmap P1 | UI+Backend | 🚧 Partial | /api/gatekeeper/check exists in server.py; no frontend UI for it | Build Option Builder modal |
| RD-P2 | Visual volatility curves + expected move cone | ui_feature_roadmap Priority 2 | UI | ❌ Not Started | static text numbers only | After live market snapshot |
| RD-P3 | Drawdown thermometer + sector heatmap | ui_feature_roadmap Priority 3 | UI | ❌ Not Started | static sector bars only | After live portfolio/risk |
| RD-P4 | Payoff diagram (tent/slope graph) in trade cards | ui_feature_roadmap Priority 4 | UI | ❌ Not Started | text only | After scanner legs wired |

---

## 🔹 D. Coverage Report: Backend → UI

**Fully surfaced:**
- Volatility regime (HIGH/MED/LOW), IV rank → header + scan context
- Event blocking (FOMC/CPI/Jobs/Earnings) → blocking events list
- Pipeline funnel counts (generated → final) → gate funnel bar
- Final picks with leg structure, score, max profit/loss → trade cards
- Per-pick pipeline journey (5 stages, status + display) → Pipeline Journey panel ✅ (new)
- Strategy reasoning → trade card panel ✅ (new)
- "Why no trades" structured explanation → zero-picks card ✅ (new)
- Rejection reasons with display_reason + severity colors → rejection tabs ✅ (new)

**Partially surfaced:**
- Market snapshot (price is live; IV rank / regime / change_pct hardcoded)
- Portfolio risk (sector bars show; values are static mocks)
- Gatekeeper check (API endpoint exists; no UI entry point)

**Not surfaced in UI (backend capability exists):**
- Drawdown halt check (`RiskEngine.check_drawdown_halt`) — no UI indicator
- Correlation matrix — shown as static mock; not from real positions
- Greeks (delta/gamma/theta/vega) — shown in positions table as hardcoded rows
- DecisionAudit log — mock text; scan results not persisted
- Account balance / total_cash_balance — exists in config.yaml; not shown anywhere
- EventLoader calendar — backend live; `/api/events/calendar` returns hardcoded dates

---

## 🔹 E. Externalization Status

| Parameter | Status | Location |
|-----------|--------|----------|
| `max_sector_concentration_pct: 0.25` | ✅ Externalized | config.yaml + risk_engine.py loads it |
| `max_portfolio_correlation: 0.70` | ✅ Externalized | config.yaml + risk_engine.py loads it |
| `drawdown_halt_pct: 0.02` | ✅ Externalized | config.yaml + risk_engine.py loads it |
| `total_cash_balance: 100000.0` | ⚠️ In config, not injected | config.yaml exists; server.py doesn't read it |
| Policy limits (tight=$1000, moderate=$2000, aggressive=$5000) | ❌ Still hardcoded | server.py line 203: `policy_amounts = {'tight': 1000, ...}` |
| Gatekeeper threshold (70) | ❌ Still hardcoded | orchestrator.py pipeline journey context |
| Sector cap 25% in pipeline journey display | ❌ Still hardcoded | `orchestrator.py` `log_context_for_pipeline` |

**Next steps:**
- `server.py`: Load config.yaml at startup, expose `/api/config`, pass `total_cash_balance` into scan context
- Move `policy_amounts` dict into config.yaml under `policy_limits`

---

## 🔹 F. Next Actions (Prioritized by Impact + Dependency)

| # | Action | Files | Dependency | Impact |
|---|--------|-------|------------|--------|
| 1 | **server.py loads config.yaml** — read at startup, expose `/api/config`, pass `total_cash_balance` to scan | `ui/server.py` | config.yaml (✅ exists) | Unblocks account balance display + drawdown math |
| 2 | **Wire /api/market/snapshot live** — call `vol_engine.detect_regime()` + `market_data` for real IV rank, regime, change_pct | `ui/server.py` | none | Replaces 4 hardcoded fields in market snapshot |
| 3 | **Wire /api/events/calendar live** — call `EventLoader` for real macro + portfolio earnings | `ui/server.py` | none | Replaces hardcoded calendar |
| 4 | **Setup SQLite data layer** — SQLAlchemy + `Position` + `Portfolio` models, `.env` `DATABASE_URL` | new `db/models.py` | none | Prerequisite for all position/portfolio live data |
| 5 | **Wire /api/portfolio/risk live** — query Position table → RiskEngine.analyze_portfolio_risk() | `ui/server.py`, `db/models.py` | #4 | Replaces all mock Positions view data |
| 6 | **Surface account balance in UI header** — read from `/api/config`, show alongside ticker | `ui/app.js`, `ui/index.html` | #1 | Makes account value visible |
| 7 | **Add /api/trade/execute** — validate pick → paper-trade to DB | `ui/server.py`, `db/models.py` | #4 | Closes the execution loop |
| 8 | **Move policy_amounts to config.yaml** — externalize tight/moderate/aggressive dollar limits | `config.yaml`, `ui/server.py` | #1 | Removes last hardcoded trading param |
| 9 | **Strategy Sandbox UI** — Option Builder modal calling /api/gatekeeper/check | `ui/app.js`, `ui/index.html` | none (API exists) | Surfaces gatekeeper interactivity |
| 10 | **Mark-to-market daemon** — background task refreshing P&L from yfinance | `ui/server.py` or worker | #4, #7 | Live Greeks + unrealized P&L |

---

## 🔹 Existing Plan to Build On

**`docs/architecture/live_backend_migration.md`** is the authoritative architecture plan for the remaining work. It already defines all 6 phases in the right order. We do NOT need a new plan — we execute its Phase 1 → Phase 2 → Phase 3 sequence.

**Recommended starting point:** Complete EC-03/04/05 (server.py config loading) first — it's the smallest change with the highest unlock (account balance in UI, correct drawdown math). Then tackle the SQLite data layer to replace mock positions.
