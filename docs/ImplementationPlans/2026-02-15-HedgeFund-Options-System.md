# Implementation Plan: "Hedge Fund Grade" Options System

Document status: Aspirational plan plus current-state alignment snapshot.
Last reviewed: 2026-02-17.

## Purpose
Build a robust, risk-first options scanning and decisioning system that is realistic enough for desk-style workflows.

## Vision (Aspirational Goals)

### Phase 1: Core Infrastructure (Risk and Data Layers)
1. Risk engine as a deterministic "No" machine.
- Max risk per trade based on max loss at entry.
- Sector concentration hard cap.
- Correlation guard against concentrated portfolio exposure.
- Drawdown circuit breaker.

2. Volatility engine with standardized signals.
- Hybrid volatility model (historical + garch + iv-style signal).
- Regime detection: low/medium/high.
- Expected move computation.

3. Event and calendar layer.
- Earnings-aware routing/blocking.
- Macro event blackout windows.

### Phase 2: Logic Engines (Gatekeeper and Scanner)
4. Scored gatekeeper.
- Liquidity viability scoring.
- Bid/ask spread quality checks.

5. Policy-based scanner.
- Regime-driven strategy routing.
- Candidate generation and ranking by risk-adjusted quality.

### Phase 3: Trade Management
6. Execution realism model.
- Slippage assumptions and fill realism.

7. Thesis-based exits.
- Invalidation rules.
- Time and profit management.

### Phase 4: Feedback and Continuous Improvement
8. Structured decision loop.
- Scout, risk, analyst, execution style orchestration.

9. Statistical feedback loop.
- Feature store and post-trade learning loop.

## Current State Snapshot (As of 2026-02-17)

### What is accomplished
1. Phase 1 modules exist and run.
- `agent/risk_engine.py`
- `agent/vol_engine.py`
- `agent/event_loader.py`

2. Phase 2 core pipeline exists and runs through `/api/scan`.
- `agent/orchestrator.py`
- `agent/options_scanner.py`
- `agent/market_checks.py`
- `agent/correlation_gate.py`
- `ui/server.py` (`POST /api/scan`)

3. Tests are in strong shape for the implemented surface.
- In venv: `194 passed`.

4. UI-to-backend integration for main flow is present.
- `ui/index.html` + `ui/app.js` call `/api/scan` and render funnel, picks, rejections, and audit panel.

### What is only partially achieved
1. Scanner strategy routing is partial.
- Current scanner is heavily skewed to bullish call debit spread generation.
- High-vol regime routing to bull put / iron condor is not fully implemented.

2. Event blocking behavior is partial.
- Macro events route into policy, but earnings integration has field mismatch risk between event payload and policy evaluation.

3. Risk semantics are partially misaligned.
- Candidate `max_loss` unit handling is inconsistent (per-share vs contract-dollar risk).

4. Data realism is mixed.
- Live market data is used where available.
- Some fetch paths fail open to mock data, which can produce misleading results under outages.

### What is missing
1. Phase 3 modules are not implemented in this repo.
- `agent/execution_model.py` does not exist.
- `agent/trade_manager.py` does not exist.

2. Phase 4 feedback loop is not implemented in this repo.
- No feature store.
- No shapley-based optimization loop.

## Alignment Matrix (Vision vs Current)

| Capability | Vision Target | Current State | Alignment |
| --- | --- | --- | --- |
| Risk engine | Deterministic hard risk gates | Implemented, but sector-cap behavior and risk units need correction | Partial |
| Vol engine | Hybrid vol + regime + expected move | Implemented and integrated | Strong |
| Event layer | Earnings + macro hard routing | Implemented, but earnings policy edge cases remain | Partial |
| Gatekeeper | Liquidity + spread quality checks | Implemented and integrated | Strong |
| Strategy router | Regime-based multi-strategy routing | Implemented at high level, limited strategy realization | Partial |
| Orchestration pipeline | Events -> vol -> scan -> risk -> gatekeeper -> correlation | Implemented and running via `/api/scan` | Strong |
| Execution realism | Slippage/fill model | Not implemented | Missing |
| Thesis-based exits | Technical invalidation + time/profit logic | Not implemented | Missing |
| Statistical feedback loop | Post-trade learning and rule optimization | Not implemented | Missing |

## Execution Quality Assessment

### Works reliably today
1. Main orchestrated scan endpoint exists and returns structured data.
2. Gate sequencing and decision logging are wired.
3. Test coverage for current modules is substantial.

### Fragile or misleading scenarios
1. Empty/default portfolio flow can eliminate all candidates via sector concentration logic.
2. Risk-dollar units are inconsistent in candidate payloads.
3. Provider outages or parser dependency gaps can degrade output quality silently.

### Broken or out-of-sync surfaces
1. `/api/smart-scan` contract is currently broken.
2. Some docs referenced old `ui-aistudio`/react flow that no longer matches current `ui/` implementation.

## Doc Sync Policy

1. This file is the authoritative "vision + alignment" document.
2. `BACKEND_INTEGRATION.md` is the authoritative API and runtime integration contract.
3. `docs/UI_ANALYSIS.md` is design analysis/reference, not source-of-truth runtime contract.
4. Every backend behavior change touching endpoints, payload schema, or gating logic must update docs in the same PR.
5. Each updated doc must include a "Last reviewed" date.

## Near-Term Priorities to Improve Alignment

1. Correct risk-unit consistency (`max_loss` in contract dollars end-to-end).
2. Fix earnings policy field mapping for hard/warn/tight event handling.
3. Stabilize default scan behavior so empty-portfolio scans are still meaningful.
4. Repair or remove `/api/smart-scan` until its contract is valid.
5. Keep docs current after each functional change.
