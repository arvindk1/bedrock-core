# Options Scanner UI Design

**Date:** 2026-02-15
**Approach:** FastAPI proxy + single HTML file (Approach A)

## Architecture

```
ui/
  server.py    — FastAPI app (serves HTML + /api/scan endpoint)
  index.html   — Form + results card (vanilla HTML/CSS/JS)
```

- `server.py`: One POST endpoint `/api/scan` that takes `{symbol, start_date, end_date, top_n}`, builds a prompt, calls AgentCore via boto3, returns JSON.
- `index.html`: Served as static file at `/`. Form submits via fetch(), shows spinner, renders results in a styled card.
- Run with: `uvicorn ui.server:app --reload`

## Data Flow

```
Form submit → JS fetch POST /api/scan {symbol, start_date, end_date, top_n}
  → FastAPI builds prompt string
  → boto3 invoke_agent_runtime(agent_runtime_arn, payload={"prompt": ...})
  → AgentCore returns {"status": "success", "output": "..."}
  → FastAPI returns JSON to browser
  → JS renders output in results card (preformatted text)
```

- Agent returns pre-formatted text (LLM markdown), not structured JSON.
- Results card renders as styled preformatted text.
- Runtime ARN configured via `AGENTCORE_RUNTIME_ARN` env var.

## UI Layout

**Form (top):**
- Symbol text input (placeholder: "AAPL")
- Start date + End date (type=date)
- Top N dropdown (3, 5, 10) — default 5
- "Scan Options" submit button

**Results (below form):**
- Hidden until results arrive
- Loading spinner during request
- Success: card with agent's formatted output, subtle border/shadow
- Error: red error card with message

**Styling:** Clean, minimal. Dark-on-white, monospace for results. Inline CSS. Basic responsive.

## Error Handling

- Frontend: Disable button + spinner during request. 60s timeout for cold starts.
- Backend: Catch boto3 exceptions, return error JSON. No stack traces to browser.
- Validation: Both frontend and backend validate symbol non-empty, dates filled, start <= end.

## Dependencies

- `fastapi`, `uvicorn`, `boto3` (boto3 likely already available via AWS env)
