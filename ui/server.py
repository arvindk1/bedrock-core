"""FastAPI server for the Options Scanner UI."""
import json
import os
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any

import boto3
import yaml
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, field_validator

# --- Local Backend Integration ---
# Ensure we can import from 'agent' by adding parent dir to path if needed
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "agent"))

from agent.options_scanner import options_scanner
from agent.market_checks import gatekeeper, TradeScore
from agent.market_data import market_data

# Configure Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("UIServer")


# ============================================================================
# App Config (config.yaml)
# ============================================================================

def _load_app_config() -> Dict[str, Any]:
    """
    Load config.yaml from the repo root at server startup.
    Returns a safe default dict if the file is missing or unreadable.
    """
    _defaults: Dict[str, Any] = {
        "account": {
            "total_cash_balance": 100000.0,
        },
        "risk_limits": {
            "max_sector_concentration_pct": 0.25,
            "max_portfolio_correlation": 0.70,
            "drawdown_halt_pct": 0.02,
        },
        "policy_limits": {
            "tight": 1000,
            "moderate": 2000,
            "aggressive": 5000,
        },
    }

    # config.yaml lives at the repo root, one level above ui/
    config_path = os.path.join(os.path.dirname(__file__), "..", "config.yaml")
    config_path = os.path.abspath(config_path)

    if not os.path.exists(config_path):
        logger.warning(f"config.yaml not found at {config_path}; using defaults")
        return _defaults

    try:
        with open(config_path, "r") as fh:
            loaded = yaml.safe_load(fh) or {}

        # Merge loaded values on top of defaults (shallow per top-level key)
        result = dict(_defaults)
        for key, default_value in _defaults.items():
            if key in loaded:
                if isinstance(default_value, dict):
                    merged = dict(default_value)
                    merged.update(loaded[key])
                    result[key] = merged
                else:
                    result[key] = loaded[key]

        logger.info(f"Loaded config.yaml from {config_path}")
        return result

    except Exception as exc:
        logger.error(f"Failed to load config.yaml: {exc}; using defaults")
        return _defaults


# Module-level config cache — loaded once at import time
APP_CONFIG: Dict[str, Any] = _load_app_config()


app = FastAPI(title="Hedge Fund Options Desk")

# Add CORS middleware to allow frontend requests from different port
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

RUNTIME_ARN = os.environ.get("AGENTCORE_RUNTIME_ARN", "")
REGION = os.environ.get("AWS_REGION", "us-east-1")
UI_DIR = os.path.dirname(__file__)

# Mount static files directory for CSS, JS, etc.
app.mount("/static", StaticFiles(directory=UI_DIR), name="static")


# --- Scan Response Enrichment Helpers ---

def _severity_for_rule(rule: str) -> str:
    """Map a rejection rule code to a UI severity level."""
    critical_rules = {"SECTOR_CAP", "MAX_LOSS_EXCEEDED", "DRAWDOWN_HALT", "EARNINGS", "FOMC", "CPI", "JOBS_REPORT", "EVENT_TIGHT"}
    warning_rules = {"LIQUIDITY", "SPREAD_TOO_WIDE", "CORRELATION_BREACH", "IV_PENALTY"}
    info_rules = {"LOW_SCORE", "NO_MAX_LOSS"}
    if rule in critical_rules:
        return "critical"
    if rule in warning_rules:
        return "warning"
    if rule in info_rules:
        return "info"
    return "info"  # safe default


def _enrich_rejections(rejections: list) -> list:
    """
    Add display_reason and severity to each rejection dict.
    Works for any rejection list (risk, gatekeeper, correlation).
    """
    import sys as _sys, os as _os
    _sys.path.insert(0, _os.path.join(_os.path.dirname(__file__), "..", "agent"))
    from reason_codes import extract_reason_summary, parse_reason_code, is_structured_reason

    enriched = []
    for rej in rejections:
        r = dict(rej)
        reason = r.get("reason", "")
        if is_structured_reason(reason):
            r["display_reason"] = extract_reason_summary(reason)
            parsed = parse_reason_code(reason)
            rule = parsed.get("rule", "UNKNOWN")
            r["severity"] = _severity_for_rule(rule)
        else:
            r["display_reason"] = reason or "Unknown"
            r["severity"] = "info"
        enriched.append(r)
    return enriched



# --- Data Models ---

class ScanRequest(BaseModel):
    symbol: str
    strategy_preference: Optional[str] = None

    @field_validator("symbol")
    @classmethod
    def symbol_not_empty(cls, v):
        if not v.strip():
            raise ValueError("Symbol is required")
        return v.strip().upper()

class GatekeeperRequest(BaseModel):
    symbol: str
    strategy_type: str
    expiration_date: str
    max_loss: float = 500.0
    quantity: int = 1

    @field_validator("symbol")
    @classmethod
    def symbol_upper(cls, v):
        return v.strip().upper()

class ScanRequest(BaseModel):
    """Full scan request for dashboard."""
    symbol: str
    start_date: str
    end_date: str
    top_n: int = 5
    portfolio_json: str = "[]"
    policy_mode: str = "tight"

    @field_validator("symbol")
    @classmethod
    def symbol_upper(cls, v):
        return v.strip().upper()

# --- API Endpoints ---

@app.get("/")
async def index():
    return FileResponse(os.path.join(UI_DIR, "index.html"))

@app.get("/terminal.css")
async def serve_css():
    return FileResponse(os.path.join(UI_DIR, "terminal.css"), media_type="text/css")

@app.get("/app.js")
async def serve_js():
    return FileResponse(os.path.join(UI_DIR, "app.js"), media_type="application/javascript")

@app.post("/api/smart-scan")
async def smart_scan(req: ScanRequest):
    """
    Run the 'Hedge Fund Grade' policy-based scanner.
    """
    logger.info(f"Received scan request for {req.symbol}")
    try:
        # 1. Run the local scanner engine
        opportunities = await options_scanner.scan_opportunities(
            symbol=req.symbol,
            strategy_preference=req.strategy_preference
        )
        
        # 2. Enrich with current price for context
        price = market_data.get_current_price(req.symbol)
        
        return {
            "status": "success",
            "symbol": req.symbol,
            "current_price": price,
            "opportunities": opportunities,
            "message": f"Found {len(opportunities)} opportunities" if opportunities else "No opportunities found matching criteria."
        }
    except Exception as e:
        logger.error(f"Scan failed: {e}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"status": "error", "output": str(e)}
        )

@app.post("/api/scan")
def scan(req: ScanRequest):
    """
    Full orchestrated scan for the Desk Command dashboard.
    Returns decision log, picks, rejections, and market context.
    """
    logger.info(f"Received dashboard scan for {req.symbol} ({req.start_date} to {req.end_date})")
    try:
        # Import here to avoid circular dependencies
        from agent.orchestrator import full_scan_with_orchestration

        # Parse portfolio
        portfolio = []
        if req.portfolio_json.strip():
            portfolio = json.loads(req.portfolio_json)

        # Run full orchestration
        decision_log = full_scan_with_orchestration(
            symbol=req.symbol,
            start_date=req.start_date,
            end_date=req.end_date,
            top_n=req.top_n,
            portfolio=portfolio,
            policy_mode=req.policy_mode,
        )

        # Extract decision log data
        log_dict = decision_log.to_dict() if hasattr(decision_log, 'to_dict') else {}

        # Map policy mode to dollar amount (sourced from config.yaml via APP_CONFIG)
        policy_amounts = APP_CONFIG["policy_limits"]
        policy_amount = policy_amounts.get(req.policy_mode, 1000)

        # Enrich rejections with display_reason + severity
        risk_rejs_enriched = _enrich_rejections(log_dict.get("risk_rejections", []))
        gk_rejs_enriched = _enrich_rejections(log_dict.get("gatekeeper_rejections", []))
        corr_rejs_enriched = _enrich_rejections(log_dict.get("correlation_rejections", []))

        # No-trades explanation (from orchestrator — populated when picks = 0)
        no_trades_explanation = None
        if hasattr(decision_log, 'no_trades_explanation') and decision_log.no_trades_explanation:
            no_trades_explanation = decision_log.no_trades_explanation

        return {
            "regime": log_dict.get("regime", "HIGH"),
            "spyTrend": log_dict.get("spy_trend", "Uptrend"),
            "macroRisk": log_dict.get("macro_risk", "No macro events"),
            "policyMode": f"{req.policy_mode.title()} (${policy_amount})",
            "blockingEvents": log_dict.get("blocking_events", []),
            "gateFunnel": {
                "generated": log_dict.get("total_generated", 0),
                "afterEvent": log_dict.get("after_event_filter", 0),
                "afterRisk": log_dict.get("after_risk_gate", 0),
                "afterGatekeeper": log_dict.get("after_gatekeeper", 0),
                "afterCorrelation": log_dict.get("after_correlation", 0),
                "final": len(log_dict.get("final_picks", [])),
            },
            "picks": log_dict.get("final_picks", []),
            "rejections": {
                "risk": risk_rejs_enriched,
                "gatekeeper": gk_rejs_enriched,
                "event": [],
                "correlation": corr_rejs_enriched,
            },
            "noTradesExplanation": no_trades_explanation,
            "volatilityContext": {
                "annual_vol": log_dict.get("regime_details", {}).get("annual_vol"),
                "daily_vol": log_dict.get("regime_details", {}).get("daily_vol"),
                "iv_rank": log_dict.get("regime_details", {}).get("iv_rank"),
                "expected_move_30d": log_dict.get("regime_details", {}).get("expected_move"),
            },
            "decisionLog": {
                "regime": log_dict.get("regime", "HIGH"),
                "strategyHint": log_dict.get("strategy_hint", "CREDIT_SPREAD"),
                "blockingEvents": log_dict.get("blocking_events_str", "None"),
                "generated": log_dict.get("total_generated", 0),
                "riskPassed": log_dict.get("after_risk_gate", 0),
                "gatekeeperPassed": log_dict.get("after_gatekeeper", 0),
                "correlationPassed": log_dict.get("after_correlation", 0),
                "finalPicks": len(log_dict.get("final_picks", [])),
                "timestamp": log_dict.get("timestamp", datetime.now().isoformat()),
            },
        }

    except json.JSONDecodeError as e:
        logger.error(f"Invalid portfolio JSON: {e}")
        return JSONResponse(
            status_code=400,
            content={"status": "error", "output": f"Invalid portfolio JSON: {str(e)}"}
        )
    except Exception as e:
        logger.error(f"Scan failed: {e}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"status": "error", "output": f"Scan failed: {str(e)}"}
        )

@app.post("/api/gatekeeper/check")
async def gatekeeper_check(req: GatekeeperRequest):
    """
    Run the Scored Gatekeeper validation on a trade proposal.
    """
    logger.info(f"Received gatekeeper check for {req.symbol} - {req.strategy_type}")
    try:
        proposal = {
            "symbol": req.symbol,
            "strategy_type": req.strategy_type,
            "expiration_date": req.expiration_date,
            "max_loss": req.max_loss,
            "quantity": req.quantity
        }

        score_card = gatekeeper.check_trade(proposal)

        return {
            "status": "success",
            "approved": score_card.is_approved,
            "total_score": score_card.total_score,
            "breakdown": score_card.score_breakdown,
            "warnings": score_card.warnings,
            "rejection_reason": score_card.rejection_reason
        }
    except Exception as e:
        logger.error(f"Gatekeeper check failed: {e}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"status": "error", "output": str(e)}
        )

@app.get("/api/portfolio/risk")
def get_portfolio_risk():
    """
    Returns aggregate portfolio risk metrics using RiskEngine.
    Used by Portfolio & Risk view.
    """
    try:
        # TODO: Get current portfolio from session or database
        portfolio = []

        # Mock implementation - returns static risk metrics
        # In production, calculate using RiskEngine and actual portfolio
        return JSONResponse({
            "total_capital_at_risk": 4200,
            "max_risk_per_trade": 1000,
            "daily_drawdown": -150.0,
            "net_delta": 142,
            "sector_exposure": [
                {
                    "name": "Technology",
                    "value": 0.45,
                    "limit": 0.25,
                    "status": "critical",
                },
                {
                    "name": "Finance",
                    "value": 0.25,
                    "limit": 0.25,
                    "status": "normal",
                },
                {
                    "name": "Healthcare",
                    "value": 0.15,
                    "limit": 0.25,
                    "status": "normal",
                },
                {
                    "name": "Energy",
                    "value": 0.15,
                    "limit": 0.25,
                    "status": "normal",
                },
            ],
            "alerts": [
                {
                    "type": "concentration",
                    "severity": "critical",
                    "message": "Technology sector at 45% exceeds limit of 25%",
                    "recommendation": "Consider reducing tech exposure or closing positions",
                }
            ]
        })
    except Exception as e:
        logger.error(f"Portfolio risk error: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)

@app.get("/api/market/snapshot/{symbol}")
def get_market_snapshot(symbol: str):
    """
    Returns comprehensive market snapshot for a symbol.
    Used by live ticker and market regime detection.
    """
    try:
        symbol = symbol.upper()

        # Get price data
        current_price = market_data.get_current_price(symbol)

        # Mock implementation - returns static market snapshot
        # In production, integrate with VolEngine, EventLoader, MarketData
        return JSONResponse({
            "symbol": symbol,
            "current_price": current_price,
            "change_pct": 1.2,
            "volume": 2500000,
            "avg_volume": 2100000,
            "relative_strength": 0.75,
            "volatility": {
                "annual": 0.32,
                "daily": 0.02,
                "iv_rank": 0.78,
                "regime": "HIGH",
                "expected_move_30d": {
                    "dollars": 32.50,
                    "pct": 0.075,
                    "upper": current_price + 32.50,
                    "lower": current_price - 32.50,
                }
            },
            "upcoming_events": [
                {
                    "type": "earnings",
                    "days_until": None,
                    "blocks_dte": [30, 45]
                }
            ]
        })
    except Exception as e:
        logger.error(f"Market snapshot error: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)

@app.get("/api/events/calendar")
def get_event_calendar():
    """
    Returns upcoming earnings and macro events.
    Used by event calendar and dashboard blocking event display.
    """
    try:
        # Mock implementation - returns static event calendar
        # In production, integrate with EventLoader
        return JSONResponse({
            "earnings": {
                "AAPL": {
                    "days_until": 15,
                    "date": "2026-03-01",
                },
                "MSFT": {
                    "days_until": 22,
                    "date": "2026-03-08",
                },
                "NVDA": {
                    "days_until": 8,
                    "date": "2026-02-24",
                },
            },
            "macro": [
                {
                    "name": "FOMC Meeting",
                    "date": "2026-03-15",
                    "days_until": 28,
                    "impact": "high"
                },
                {
                    "name": "CPI Release",
                    "date": "2026-03-10",
                    "days_until": 23,
                    "impact": "high"
                },
            ]
        })
    except Exception as e:
        logger.error(f"Event calendar error: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)

@app.get("/api/config")
def get_config():
    """
    Returns the current app configuration sourced from config.yaml.
    Exposes account balance, risk limits, and policy limits to the UI.
    """
    return {
        "account": {
            "total_cash_balance": APP_CONFIG["account"]["total_cash_balance"],
        },
        "risk_limits": {
            "max_sector_concentration_pct": APP_CONFIG["risk_limits"]["max_sector_concentration_pct"],
            "max_portfolio_correlation": APP_CONFIG["risk_limits"]["max_portfolio_correlation"],
            "drawdown_halt_pct": APP_CONFIG["risk_limits"]["drawdown_halt_pct"],
        },
        "policy_limits": {
            "tight": APP_CONFIG["policy_limits"]["tight"],
            "moderate": APP_CONFIG["policy_limits"]["moderate"],
            "aggressive": APP_CONFIG["policy_limits"]["aggressive"],
        },
    }


# --- Legacy/Agent Endpoint (Optional) ---
def invoke_agent(prompt: str) -> dict:
    """Call the deployed AgentCore runtime (Legacy)."""
    if not RUNTIME_ARN:
        return {"output": "Agent Runtime ARN not configured."}
        
    client = boto3.client("bedrock-agentcore", region_name=REGION)
    resp = client.invoke_agent_runtime(
        agentRuntimeArn=RUNTIME_ARN,
        qualifier="DEFAULT",
        contentType="application/json",
        accept="application/json",
        payload=json.dumps({"prompt": prompt}).encode(),
    )
    body = resp["response"].read().decode()
    return json.loads(body)
