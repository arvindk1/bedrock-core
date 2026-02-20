# Externalize Risk Configuration Plan

## Goal
Right now, critical trading safety limits (like max loss per trade, sector concentration caps, and drawdown thresholds) are hardcoded directly into `agent/risk_engine.py`. Furthermore, the scanner is disjointed from any "Total Account Value"; it relies solely on the UI "Policy" dropdown (Tight/Moderate/Aggressive). 

The goal is to externalize these parameters into a `config.yaml` file so they can be tuned without code changes, and to update `ui/server.py` and `agent/risk_engine.py` to ingest these configurations and actually use a defined Account Value.

## Proposed Changes

### `config.yaml` [NEW]
Create a new configuration file at the root to hold these parameters:
```yaml
account:
  total_cash_balance: 100000.0  # Simulated total account value for risk math

risk_limits:
  max_sector_concentration_pct: 0.25  # 25% max in one sector
  max_portfolio_correlation: 0.70     # 0.7 max correlation 
  drawdown_halt_pct: 0.02             # Halt trading if daily loss > 2% of total_cash_balance
```

### `agent/risk_engine.py` [MODIFY]
- Update `RiskEngine.__init__` to load parameter defaults from `config.yaml` (if it exists) rather than hardcoding `0.25` and `0.02`. 
- Modify the logic to ensure that if a user specifies an override (via the UI or orchestrator), it takes precedence, but otherwise, it falls back to the YAML.

### `ui/server.py` [MODIFY]
- Read `config.yaml` at startup.
- In the `/api/scan` endpoint, inject the `total_cash_balance` from the config into the `market_context` that gets passed down to the orchestrator and RiskEngine. This ensures that features like "Drawdown Halt" actually have a baseline Account Value to calculate percentages against.
- Expose a new endpoint (e.g., `/api/config`) so the frontend can display the current account balance and risk limits if desired in the future.

## Verification Plan

### Automated/Local Testing
1. Restart the backend server (`./run-ui.sh`).
2. Verify the server successfully reads `config.yaml` on startup without crashing.
3. Submit a scan via the UI (or `curl`) for AAPL and verify the scan succeeds.
4. Temporarily change `max_sector_concentration_pct` in `config.yaml` to `0.01` (1%), submit a scan, and verify that the Risk Engine immediately blocks it with a `SECTOR_CAP` reason (assuming the dummy portfolio has tech exposure). 
5. Revert the config back to normal and verify scans pass again.
