# Live Backend Migration Plan

Moving from a stateless, partially-mocked backend to a fully live, persistent backend requires introducing a data layer and connecting the remaining empty pipes.

## Current State of Data Storage
**There is currently NO persistent data store in the application.** 
- Portfolios, capital usage, and risk alerts are hardcoded mock JSON objects in `ui/server.py` (e.g., `/api/portfolio/risk` always returns the same static data).
- Market snapshots and event calendars are returning hardcoded dicts.
- The `OptionsScanner` and `Orchestrator` pull live data from `yfinance`, but they don't *store* the results anywhere. The `DecisionLog` is generated dynamically and sent to the UI, but lost immediately after.

---

## Design Principles for Cloud Readiness & Cost Efficiency
1. **Zero Hardcoding**: All configurations (thresholds, policies, limits) must live outside the code. They will be stored in configuration files (JSON/YAML) locally, mounted via ConfigMaps, or fetched from the database.
2. **Ultra-Low Cost Persistence**: For a persistent store with a seamless path to the cloud, we will use **PostgreSQL**. 
   - *Local/Dev*: Run generic Postgres or SQLite as a local dev replica.
   - *Cloud Target*: Use a Serverless Postgres provider like **Neon** or **Supabase**. They offer extremely generous free tiers, scale to zero when not in use (costing literally pennies per month), and require zero changes to our `psycopg2` or `SQLAlchemy` connection logic.
3. **Seamless Migration**: By using environment variables for the `DATABASE_URL` and JSON/YAML for configs, moving from local to Docker to AWS/GCP simply means injecting different environment variables. No code changes required.

---

## Prioritized Implementation List (No More Mock Data)

To make this a fully live app with zero mock data, we must execute the following prioritized phases:

### Phase 1: Establish Config Management & Persistent Storage
We need to decouple hardcoded values and establish our serverless-ready Postgres database.
1. **Externalize Configuration**:
   - Move all hardcoded limits (e.g., sector max 25%, $1000 tight policy limit) into a `config/app_settings.yaml` or `.json` file.
   - The backend will load this on startup, making tweaks trivial without redeploys.
2. **Setup Serverless-Ready PostgreSQL**: 
   - Integrate `SQLAlchemy`.
   - Use a `.env` file to define `DATABASE_URL`. Locally, this can point to a local Postgres instance or SQLite. In production, it points to a Neon/Supabase connection string.
3. **Define Core Data Models**:
   - `Portfolio`: Tracks total capital, available cash.
   - `Position`: Tracks active trades (symbol, strikes, entry price, quantity, open date).
   - `DecisionAudit`: Stores the structured JSON `DecisionLog` of every scan.

### Phase 2: Rip Out the Mocks in `ui/server.py`
Replace the hardcoded JSON endpoints with live logic.
1. **`/api/portfolio/risk`**: 
   - *Current*: Hardcoded `$4200` capital at risk and static sector alerts.
   - *Fix*: Query the database for active `Position` records -> pass them to `RiskEngine.analyze_portfolio_risk(positions)` -> return live calculated Greeks, drawdowns, and dynamic sector concentration alerts.
2. **`/api/market/snapshot/{symbol}`**:
   - *Current*: Hardcoded volume, IV rank, and regime.
   - *Fix*: Call `market_data.get_current_price()` and `vol_engine.detect_regime()` live to return real 1σ/2σ expected moves and volatility context.
3. **`/api/events/calendar`**:
   - *Current*: Hardcoded AAPL/MSFT earnings dates.
   - *Fix*: Call `EventLoader` to fetch real upcoming macroeconomic blackout periods and actual earnings dates for the active portfolio.

### Phase 3: Connect the Execution Loop
Currently, the scanner finds "Picks", but you can't *do* anything with them. The loop needs to be closed.
1. **Trade Execution Endpoint (`/api/trade/execute`)**:
   - Create a route that takes a "Pick" from the scanner.
   - Run it through a final `Gatekeeper` check.
   - If approved, save it to the `Position` database table (simulating paper trading) or route it to a true broker API (Alpaca/Schwab).
2. **Mark-to-Market Daemon**:
   - Create a background worker that runs every 5 minutes.
   - It iterates over all open records in the `Position` table, pulls live pricing via `yfinance`, and calculates Unrealized P&L in real-time. This feeds the UI's Status Bar.

### Phase 4: Strategy Sandbox (Interactive Gatekeeper)
1. **`/api/gatekeeper/check`**:
   - Wire up the frontend so the user can construct custom option legs manually.
   - Send the custom legs to the backend, run `gatekeeper.check_trade()`, and return the true 0-100 score dynamically instead of relying purely on the automated scanner.

### Phase 5: Multi-Tenant Data Isolation & Authentication
Authentication (who you are) is easy; **Data Isolation (what you can see)** is the critical engineering challenge for a trading terminal. We must guarantee that a user can *never* access another user's portfolio, trades, or API keys.
1. **Authentication Provider**: Integrating a modern Auth-as-a-Service like **Clerk** or **Supabase Auth** to handle sessions and JWTs securely.
2. **Database Tenant Isolation (Row-Level Security)**:
   - Because we chose **PostgreSQL** (specifically Supabase or Neon), we can leverage **Row-Level Security (RLS)** at the database engine level.
   - We add a `user_id` foreign key to every table (`Portfolio`, `Position`, `DecisionAudit`, `BrokerCredentials`).
   - We write Postgres RLS policies: `CREATE POLICY "User can only view own data" ON Position FOR SELECT USING (auth.uid() = user_id);`
   - *Why this is bulletproof*: Even if a backend API route has a bug and forgets to add `WHERE user_id = ?`, the database itself will physically block the query from returning another user's data.
3. **Backend Middleware**: 
   - A FastAPI middleware intercepts the session token, verifies the user, and sets the DB connection context so RLS can do its job.

### Phase 6: Live Broker Routing
When ready to move from "Paper Trading" (just saving rows to our `Position` table) to real money:
1. **Broker Abstraction Layer**:
   - Create a `BrokerClient` interface with methods like `submit_order()`, `get_positions()`, and `get_buying_power()`.
2. **API Integrations**:
   - Implement the interface for modern API-first brokers like **Alpaca** (great for options/crypto), **TradeStation**, or **Tradier**.
   - Store the user's Broker API keys securely (encrypted) in the database.
3. **Execution**:
   - Update the `/api/trade/execute` route. If `live_trading=True`, it calls `BrokerClient.submit_order()` instead of just writing to the local `Position` table.

---

## Verification Plan

### Automated Tests
- Run `pytest tests/` to ensure we don't break existing `RiskEngine` or `ScoredGatekeeper` logic when wiring them to live data.
- Write new integration tests for `ui/server.py` that verify `/api/portfolio/risk` returns dynamic values based on injected `Position` test data, rather than static mocks.

### Manual Verification
- Start the server (`./run-ui.sh`).
- Add a simulated trade to the new database.
- Refresh the UI's "Portfolio" tab and visually confirm the "Capital Utilization", "Daily P&L", and "Sector Concentration" charts instantly update to reflect the newly inserted trade.
- Run a live scan on `SPY` and verify the Volatility context matches live market data on a third-party tool like ThinkOrSwim.
