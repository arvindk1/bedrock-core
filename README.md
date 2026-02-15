# Bedrock AgentCore - Options Scanner Agent

An AI agent deployed on [Amazon Bedrock AgentCore](https://docs.aws.amazon.com/bedrock/latest/userguide/agentcore.html) that scans stock options chains and ranks contracts by Greeks and bang-for-buck score.

## Prerequisites

- Python 3.10+
- AWS CLI configured with valid credentials
- Access to Amazon Bedrock models

## Setup

```bash
# Clone and create virtual environment
git clone <repo-url> && cd bedrock-core
python -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install .
pip install bedrock-agentcore-starter-toolkit  # CLI tooling (Only for small projects - Not Prod Grade)

# Configure environment
cp .env.example .env
# Edit .env with your settings (AWS_REGION, BEDROCK_MODEL_ID)
```

## Create & Configure the Agent

```bash
# Scaffold a new AgentCore project (first time only)
agentcore create

# Configure the agent with your entrypoint
agentcore configure -e app.py
```

This generates a `.bedrock_agentcore/` directory with a Dockerfile and deployment config.

## Run Locally

```bash
agentcore dev   #For local 
```

## Deploy to AWS

```bash
agentcore deploy    # For Production (AWS)
```

This builds an ARM64 container via CodeBuild, pushes to ECR, and deploys to AgentCore Runtime.

## Invoke

```bash
# Via CLI
agentcore invoke '{"prompt": "Find the cheapest AAPL calls expiring between 2026-03-01 and 2026-06-01"}'

# Check status
agentcore status
```

## Test

```bash
pytest tests/ -v
```

## Project Structure

```
app.py              # Entrypoint - agent setup and request handling
tools.py            # Agent tools (scan_options)
options_scanner.py  # Options chain fetching, Black-Scholes Greeks, scoring
tests/              # Unit tests
.env.example        # Environment variable template
```

## Cleanup

```bash
agentcore destroy
```


Steps:
Summary: 9 tasks to add CDK infrastructure to bedrock-core:
  1. Create agent/Dockerfile and agent/requirements.txt
  2. Copy agent source code into agent/
  3. Create cdk/cdk.json and cdk/requirements.txt
  4. Create cdk/build_trigger.py (Lambda custom resource)
  5. Create cdk/stack.py (the main CDK stack)
  6. Create cdk/app.py (CDK entry point)
  7. Set up CDK venv and verify cdk synth
  8. Verify existing tests still pass