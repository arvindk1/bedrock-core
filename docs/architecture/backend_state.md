# Bedrock Core - Backend Architecture State (Live Code Analysis)

This document represents the actual, implemented state of the Python backend contained within the `agent/` and `ui/server.py` directories.

## 1. Core Orchestration Pipeline (`orchestrator.py`)
The main entry point for generating trades is `full_scan_with_orchestration()`. The pipeline consists of 7 explicit stages:
1. **Events Check**: Hard-blocks trades if an earnings or critical macro event (FOMC, CPI, Jobs) falls within the trade's Expiration. Managed by `EventLoader`.
2. **Volatility Regime Detection**: Evaluates current volatility to classify the regime as LOW, MEDIUM, or HIGH. Managed by `VolEngine`.
3. **Candidate Scan**: Generates a raw list of vertical spread candidates (Debit/Credit/Generic) based on the detected vol regime. Managed by `OptionsScanner.generate_candidates`.
4. **Risk Gate (Hard Gate)**: Deterministic evaluation of max loss per trade, sector concentration caps (dollar-weighted), and daily drawdown circuit breakers. Managed by `RiskEngine`.
5. **Scored Gatekeeper (Soft Gate)**: Evaluates pre-filtered candidates for execution viability. Scores (0-100) based on Liquidity (min Open Interest capacity), Spreads (Ask-Bid tightness), and Regime Alignment (e.g., penalizing selling premium in low vol). Managed by `ScoredGatekeeper` in `market_checks.py`. Minimum passing score is 70.
6. **Correlation Gate**: Prevents portfolio over-concentration. Checks correlation of remaining candidates against the top 3 existing portfolio positions (by risk dollars). It rejects candidates exceeding dynamic thresholds based on symbol/sector similarity. Managed by `CorrelationGate`.
7. **Final Ranking**: Sorts the accepted candidates.

## 2. API Surface (`ui/server.py`)
The backend provides a FastAPI layer primarily serving as a proxy to the orchestrator:
- `POST /api/scan`: Invokes `full_scan_with_orchestration`. Translates the resulting `DecisionLog` into a JSON response formatting accepted, rejected, and candidate trades.
- `POST /api/gatekeeper/check`: Endpoint to run just the `ScoredGatekeeper` viability checks.
- `POST /api/portfolio/risk`: Runs `RiskEngine.analyze_portfolio_risk` to get concentration alerts and metrics.
- `GET /api/market/snapshot/{symbol}`: Returns a snapshot including next earnings and regime.

## 3. Telemetry and Audit (`DecisionLog` & `reason_codes.py`)
- The entire process is recorded in a `DecisionLog` dataclass, preserving context (regime, events), candidates at each phase, rejections, and final picks.
- Rejections are standardized via `reason_codes.py` using pipes, e.g., `GATEKEEP_REJECT|rule=LOW_SCORE|symbol=AAPL|score=65|threshold=70`. This structured logging enables the UI to display precise feedback.

## 4. Key Engines Overview
- **`OptionsScanner`**: Finds strikes focusing on ATM/ITM long legs (delta 0.40 - 0.60) and OTM short legs. It enriches legs with open interest and bid/ask, and calculates max profit and risk/reward ratios.
- **`VolEngine`**: A hybrid engine capable of historical, GARCH, and EWMA models to produce a weighted annual volatility. Regime is determined using a blend of the ratio of short/long term vol and Implied Volatility (IV) Rank.
- **`EventLoader`**: Hardcodes 2026 macro dates (FOMC, CPI, Jobs) and queries `yfinance` for earnings dates.
- **`CorrelationGate`**: Computes Pearson correlation on daily log returns (default 60 days) with fallback heuristic thresholds: `0.90` (same symbol), `0.70` (same sector), `0.30` (different sector).

*Conclusion*: The backend is fully operational with a robust multi-stage pipeline designed for risk-averse, context-aware options trading, aligning perfectly with the Phase 2 goals of the project.
