"""FastAPI server for the Options Scanner UI."""
import json
import os
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any

import boto3
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, JSONResponse
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

app = FastAPI(title="Hedge Fund Options Desk")

RUNTIME_ARN = os.environ.get("AGENTCORE_RUNTIME_ARN", "")
REGION = os.environ.get("AWS_REGION", "us-east-1")
UI_DIR = os.path.dirname(__file__)


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

        # Map policy mode to dollar amount
        policy_amounts = {'tight': 1000, 'moderate': 2000, 'aggressive': 5000}
        policy_amount = policy_amounts.get(req.policy_mode, 1000)

        # Return formatted response for dashboard
        return {
            "regime": log_dict.get("regime", "HIGH"),
            "spyTrend": log_dict.get("spy_trend", "Uptrend"),
            "macroRisk": log_dict.get("macro_risk", "No macro events"),
            "policyMode": f"{req.policy_mode.title()} (${policy_amount})",
            "blockingEvents": log_dict.get("blocking_events", []),
            "gateFunnel": {
                "generated": log_dict.get("total_generated", 0),
                "afterRisk": log_dict.get("after_risk_gate", 0),
                "afterGatekeeper": log_dict.get("after_gatekeeper", 0),
                "afterCorrelation": log_dict.get("after_correlation", 0),
                "final": len(log_dict.get("final_picks", [])),
            },
            "picks": log_dict.get("final_picks", []),
            "rejections": {
                "risk": log_dict.get("risk_rejections", []),
                "gatekeeper": log_dict.get("gatekeeper_rejections", []),
                "correlation": log_dict.get("correlation_rejections", []),
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
