import os
import traceback

from dotenv import load_dotenv
from strands_agents import Agent, tool
from strands_agents.models import BedrockModel
from bedrock_agentcore import BedrockAgentCoreApp

from tools import scan_options

load_dotenv()

app = BedrockAgentCoreApp()

model = BedrockModel(
    model_id=os.environ.get("BEDROCK_MODEL_ID", "us.amazon.nova-lite-v1:0"),
    region_name=os.environ.get("AWS_REGION", "us-east-1"),
    caching=True,
)

agent = Agent(
    model=model,
    tools=[scan_options],
    system_prompt="You are a helpful AWS Bedrock assistant.",
)


@app.entrypoint
def main(payload, context=None):
    try:
        if not payload or not isinstance(payload, dict):
            return {"status": "error", "output": "Invalid payload: expected a JSON object with a 'prompt' key."}

        prompt = payload.get("prompt") or ""
        if not prompt.strip():
            return {"status": "error", "output": "Empty prompt provided."}

        response = agent(prompt)
        return {"status": "success", "output": response.text}
    except Exception as e:
        traceback.print_exc()
        return {"status": "error", "output": f"Agent invocation failed: {type(e).__name__}"}


if __name__ == "__main__":
    app.run()
