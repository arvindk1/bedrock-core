"""FastAPI server for the Options Scanner UI."""
import json
import os

import boto3
from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, field_validator

app = FastAPI(title="Options Scanner")

RUNTIME_ARN = os.environ.get("AGENTCORE_RUNTIME_ARN", "")
REGION = os.environ.get("AWS_REGION", "us-east-1")

UI_DIR = os.path.dirname(__file__)


class ScanRequest(BaseModel):
    symbol: str
    start_date: str
    end_date: str
    top_n: int = 5

    @field_validator("symbol")
    @classmethod
    def symbol_not_empty(cls, v):
        if not v.strip():
            raise ValueError("Symbol is required")
        return v.strip().upper()

    @field_validator("end_date")
    @classmethod
    def dates_in_order(cls, v, info):
        start = info.data.get("start_date", "")
        if start and v < start:
            raise ValueError("end_date must be >= start_date")
        return v


def invoke_agent(prompt: str) -> dict:
    """Call the deployed AgentCore runtime."""
    client = boto3.client("bedrock-agentcore", region_name=REGION)
    response = client.invoke_agent_runtime(
        agentRuntimeArn=RUNTIME_ARN,
        qualifier="DEFAULT",
        contentType="application/json",
        accept="application/json",
        payload=json.dumps({"prompt": prompt}).encode(),
    )
    body = response["payload"].read().decode()
    return json.loads(body)


@app.post("/api/scan")
async def scan_options(req: ScanRequest):
    prompt = (
        f"Find the best options for {req.symbol} "
        f"expiring between {req.start_date} and {req.end_date}, "
        f"top {req.top_n}"
    )
    try:
        result = invoke_agent(prompt)
        return result
    except Exception as e:
        return JSONResponse(
            status_code=502,
            content={"status": "error", "output": str(e)},
        )


@app.get("/")
async def index():
    return FileResponse(os.path.join(UI_DIR, "index.html"))
