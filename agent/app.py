import os
import traceback

from strands import Agent
from strands.models import BedrockModel
from bedrock_agentcore.runtime import BedrockAgentCoreApp

from tools import scan_options

app = BedrockAgentCoreApp()

SYSTEM_PROMPT = """You are an options contract recommender.

You help users identify liquid options contracts for a given symbol and expiration window.
When the user asks for "best options", use the scan_options tool.

Rules:
- Be practical and concise.
- Briefly explain why the top contracts rank well (delta, theta, liquidity, pricing).
- Add a short disclaimer: informational only, not financial advice.
"""

def create_agent() -> Agent:
    """Create the options scanner agent."""
    model = BedrockModel(
        model_id=os.environ.get("BEDROCK_MODEL_ID", "deepseek.v3.2"),
        region_name=os.environ.get("AWS_REGION", "us-east-1"),
    )
    return Agent(
        model=model,
        tools=[scan_options],
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
