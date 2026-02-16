import os
import traceback

from strands import Agent
from strands.models import BedrockModel
from bedrock_agentcore.runtime import BedrockAgentCoreApp

from tools import scan_options, scan_options_with_strategy, check_trade_risk

app = BedrockAgentCoreApp()

SYSTEM_PROMPT = """You are a hedge-fund-grade options advisor.

You help users find professional-grade options strategies with risk-first workflow.

AVAILABLE TOOLS:

1. **check_trade_risk** — Quick validation before trading
   Use this FIRST when a user proposes a specific trade.
   Checks: position sizing, sector concentration, risk limits.

2. **scan_options_with_strategy** — Full orchestration (recommended)
   Use this when user asks to "find opportunities".
   Integrates: Vol regime detection, Event checking, Risk gating, Decision log.

3. **scan_options** — Simple scanner (legacy)
   Basic options ranking, no risk checks.

WORKFLOW:
- For proposals: check_trade_risk() FIRST
- For discovery: scan_options_with_strategy() (shows full decision trace)
- Always explain: regime, blocking events, why contracts passed

Example:
  User: "Find AAPL calls for March"
  → Use scan_options_with_strategy(symbol="AAPL", start_date="2026-03-01", end_date="2026-03-20")
  → Show decision log (regime, events, candidates, picks)

Example:
  User: "Can I trade a MSFT bull call spread for $800?"
  → Use check_trade_risk(symbol="MSFT", strategy="BULL_CALL_DEBIT_SPREAD", max_loss=800)
  → Show approval/rejection + reasoning

RULES:
- Be practical and concise.
- Always include decision rationale (regime, events, risk reasoning).
- Include disclaimer: **Informational only, not financial advice.**
- Ask for portfolio context if user wants correlation checks.
"""

def create_agent() -> Agent:
    """Create the phase 2 orchestrated options advisor."""
    model = BedrockModel(
        model_id=os.environ.get("BEDROCK_MODEL_ID", "deepseek.v3.2"),
        region_name=os.environ.get("AWS_REGION", "us-east-1"),
    )
    return Agent(
        model=model,
        tools=[scan_options, scan_options_with_strategy, check_trade_risk],
        system_prompt=SYSTEM_PROMPT,
    )

@app.entrypoint
async def invoke(payload=None):
    """Main entrypoint for the agent."""
    try:
        if not payload or not isinstance(payload, dict):
            return {"status": "error", "output": "Invalid payload: expected a JSON object with a 'prompt' key."}

        prompt = payload.get("prompt") or ""
        if not prompt.strip():
            return {"status": "error", "output": "Empty prompt provided."}

        agent = create_agent()
        response = agent(prompt)

        # Extract text from response - handle different model output formats
        content = response.message.get("content", [])
        if isinstance(content, str):
            text = content
        elif isinstance(content, list) and content:
            block = content[0]
            text = block.get("text", str(block)) if isinstance(block, dict) else str(block)
        else:
            text = str(response)

        return {"status": "success", "output": text}
    except Exception as e:
        traceback.print_exc()
        return {"status": "error", "output": f"Agent invocation failed: {type(e).__name__}: {e}"}


if __name__ == "__main__":
    app.run()
