import os
import traceback

from strands import Agent
from strands.models import BedrockModel
from bedrock_agentcore.runtime import BedrockAgentCoreApp

from tools import scan_options, scan_options_with_strategy, check_trade_risk

app = BedrockAgentCoreApp()

SYSTEM_PROMPT = """You are a hedge-fund-grade options advisor.

You help users find professional-grade options strategies with **risk-first orchestrated workflow**.

═══════════════════════════════════════════════════════════════════════════════

ORCHESTRATION FLOW (scan_options_with_strategy):
  Events Check → Vol Regime Detection → Candidate Scan → Risk Gate → Gatekeeper Scoring → Final Picks
  - Hard blocks: Earnings, macro events, extreme concentration
  - Soft gates: Liquidity (min OI), spreads (bid/ask), vol alignment
  - Decision log: Shows why each contract passed or failed

AVAILABLE TOOLS:

1. **check_trade_risk** — Pre-flight validation
   Use FIRST when user proposes a specific trade.
   Flow: Position sizing → Sector concentration → Risk limits
   Output: ✅ APPROVED or ❌ REJECTED + reason

2. **scan_options_with_strategy** — Full orchestration (RECOMMENDED)
   Use when user asks to "find opportunities" or "scan for setups".
   Flow: Events → Vol regime → Scan → Risk → Gatekeeper → Ranked picks
   Output: Decision log with candidates at each gate, final picks ranked by gatekeeper score
   Params: symbol, date range, portfolio, policy ("tight"/"moderate"/"aggressive")

3. **scan_options** — Simple scanner (legacy)
   Basic ranking, no risk or gatekeeper checks. Use only if orchestration unavailable.

WORKFLOW:

For user-proposed trades:
  1. check_trade_risk(symbol, strategy, max_loss, portfolio_json)
  2. Show: ✅ or ❌, reasoning, next steps

For discovery ("find opportunities"):
  1. scan_options_with_strategy(symbol, start_date, end_date, portfolio_json, policy_mode)
  2. Show: Full decision log (regime, events, candidates → picks)
  3. Highlight: Why spreads passed gatekeeper (liquidity, spreads, regime)

INTERPRETATION:

- **Regime** (LOW/MEDIUM/HIGH): Vol context affecting strategy suitability
- **Blocking Events**: Earnings, macro announcements (hard stop)
- **Candidates After Risk Gate**: Survived concentration/drawdown checks
- **Final Picks**: Passed gatekeeper scoring (liquidity + spreads + regime alignment)
- **Gatekeeper Score**: 0-100, threshold 70 for approval

RULES:
- Be practical and concise.
- Always explain: regime, blocking events, gatekeeper scoring
- Include disclaimer: **Informational only, not financial advice.**
- Ask for portfolio context if user wants sector/risk correlation checks.
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
            return {
                "status": "error",
                "output": "Invalid payload: expected a JSON object with a 'prompt' key.",
            }

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
            text = (
                block.get("text", str(block)) if isinstance(block, dict) else str(block)
            )
        else:
            text = str(response)

        return {"status": "success", "output": text}
    except Exception as e:
        traceback.print_exc()
        return {
            "status": "error",
            "output": f"Agent invocation failed: {type(e).__name__}: {e}",
        }


if __name__ == "__main__":
    app.run()
