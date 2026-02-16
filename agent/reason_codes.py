"""
Standardized Reason Codes Across Phase 2 Gates
================================================

Unified format for all rejection reasons:
  [GATE_NAME]_[STATUS]|rule=[RULE]|[context_fields]

Examples:
  EVENT_BLOCK|rule=EARNINGS|symbol=AAPL|days_until=5|dte=30
  RISK_REJECT|rule=MAX_LOSS_EXCEEDED|symbol=AAPL|proposed=1500|limit=1000
  GATEKEEP_REJECT|rule=SPREAD_TOO_WIDE|leg=0|spread_pct=2.5|threshold=1.5
  CORR_REJECT|candidate=AAPL|vs=MSFT|corr=0.78|threshold=0.70|basis=prices
"""

from typing import Any, Dict, Optional


# Gate Names
GATE_EVENT = "EVENT_BLOCK"
GATE_RISK = "RISK_REJECT"
GATE_GATEKEEP = "GATEKEEP_REJECT"
GATE_CORRELATION = "CORR_REJECT"

# Status Values
STATUS_BLOCK = "BLOCK"
STATUS_REJECT = "REJECT"

# Rule Definitions
class Rules:
    """All possible rejection rules by gate."""

    class Event:
        EARNINGS = "EARNINGS"
        FOMC = "FOMC"
        CPI = "CPI"
        JOBS_REPORT = "JOBS_REPORT"

    class Risk:
        NO_MAX_LOSS = "NO_MAX_LOSS"
        MAX_LOSS_EXCEEDED = "MAX_LOSS_EXCEEDED"
        SECTOR_CAP = "SECTOR_CAP"
        DRAWDOWN_HALT = "DRAWDOWN_HALT"

    class Gatekeep:
        LIQUIDITY = "LIQUIDITY"
        SPREAD_TOO_WIDE = "SPREAD_TOO_WIDE"
        IV_PENALTY = "IV_PENALTY"
        LOW_SCORE = "LOW_SCORE"

    class Correlation:
        CORRELATION_BREACH = "CORRELATION_BREACH"


def format_reason_code(
    gate: str,
    rule: str,
    context: Optional[Dict[str, Any]] = None,
) -> str:
    """
    Format a reason code from gate, rule, and context.

    Args:
        gate: Gate name (e.g., "EVENT_BLOCK", "RISK_REJECT")
        rule: Rule name (e.g., "EARNINGS", "MAX_LOSS_EXCEEDED")
        context: Dict of context fields to append (e.g., {"symbol": "AAPL", "proposed": 1500})

    Returns:
        Formatted reason code: "GATE|rule=RULE|key1=val1|key2=val2"

    Example:
        format_reason_code(
            gate="RISK_REJECT",
            rule="MAX_LOSS_EXCEEDED",
            context={"symbol": "AAPL", "proposed": 1500, "limit": 1000}
        )
        → "RISK_REJECT|rule=MAX_LOSS_EXCEEDED|symbol=AAPL|proposed=1500|limit=1000"
    """
    parts = [f"{gate}|rule={rule}"]

    if context:
        for key, val in context.items():
            # Format booleans, None, numbers, strings
            if isinstance(val, bool):
                val_str = "true" if val else "false"
            elif val is None:
                val_str = "null"
            elif isinstance(val, (int, float)):
                # Format floats without trailing zeros
                if isinstance(val, float) and val == int(val):
                    val_str = str(int(val))
                else:
                    val_str = str(val)
            else:
                val_str = str(val)

            parts.append(f"{key}={val_str}")

    return "|".join(parts)


def parse_reason_code(code: str) -> Dict[str, Any]:
    """
    Parse a formatted reason code into components.

    Args:
        code: Formatted reason code (e.g., "RISK_REJECT|rule=MAX_LOSS_EXCEEDED|symbol=AAPL|proposed=1500")

    Returns:
        Dict with keys:
        - "gate": Gate name (e.g., "RISK_REJECT")
        - "rule": Rule name (e.g., "MAX_LOSS_EXCEEDED")
        - "context": Dict of context fields

    Example:
        parse_reason_code("RISK_REJECT|rule=MAX_LOSS_EXCEEDED|symbol=AAPL|proposed=1500|limit=1000")
        → {
            "gate": "RISK_REJECT",
            "rule": "MAX_LOSS_EXCEEDED",
            "context": {"symbol": "AAPL", "proposed": 1500, "limit": 1000}
        }
    """
    if not code or "|" not in code:
        return {
            "gate": "UNKNOWN",
            "rule": "UNKNOWN",
            "context": {},
            "raw": code,
        }

    parts = code.split("|")
    gate = parts[0]
    context = {}

    rule = None
    for part in parts[1:]:
        if "=" not in part:
            continue

        key, val = part.split("=", 1)

        # Parse value types
        if val == "true":
            val = True
        elif val == "false":
            val = False
        elif val == "null":
            val = None
        elif val.isdigit():
            val = int(val)
        else:
            try:
                val = float(val)
            except ValueError:
                pass  # Keep as string

        if key == "rule":
            rule = val
        else:
            context[key] = val

    return {
        "gate": gate,
        "rule": rule,
        "context": context,
        "raw": code,
    }


def is_structured_reason(code: str) -> bool:
    """Check if a reason code is structured format."""
    if not code:
        return False
    return "|rule=" in code


def validate_reason_code(code: str) -> bool:
    """Validate that a reason code has correct format."""
    if not code or not isinstance(code, str):
        return False

    parsed = parse_reason_code(code)
    gate = parsed.get("gate", "")
    rule = parsed.get("rule", "")

    # Check gate name is known
    valid_gates = [GATE_EVENT, GATE_RISK, GATE_GATEKEEP, GATE_CORRELATION]
    if gate not in valid_gates:
        return False

    # Check rule is not empty
    if not rule:
        return False

    return True


def extract_reason_summary(code: str) -> str:
    """
    Extract a human-readable summary from a reason code.

    Args:
        code: Formatted reason code

    Returns:
        Human-readable summary

    Example:
        extract_reason_summary("RISK_REJECT|rule=MAX_LOSS_EXCEEDED|proposed=1500|limit=1000")
        → "MAX_LOSS_EXCEEDED (proposed=$1500 > limit=$1000)"
    """
    if not is_structured_reason(code):
        return code

    parsed = parse_reason_code(code)
    rule = parsed.get("rule", "UNKNOWN")
    context = parsed.get("context", {})

    # Build summary based on rule type
    if rule == "MAX_LOSS_EXCEEDED":
        return f"Max loss ${context.get('proposed')} exceeds limit ${context.get('limit')}"
    elif rule == "SECTOR_CAP":
        sector = context.get("sector", "UNKNOWN")
        return f"Sector {sector} cap exceeded: {context.get('used_pct', 0):.0f}% used"
    elif rule == "DRAWDOWN_HALT":
        return f"Daily drawdown {context.get('loss_pct', 0):.1f}% exceeds {context.get('limit', 0):.1f}% limit"
    elif rule == "LIQUIDITY":
        return f"Market impact {context.get('impact_pct', 0):.1f}% exceeds {context.get('threshold', 0):.1f}% threshold"
    elif rule == "SPREAD_TOO_WIDE":
        leg = context.get("leg", 0)
        return f"Leg {leg} bid/ask spread {context.get('spread_pct', 0):.2%} too wide"
    elif rule == "LOW_SCORE":
        return f"Score {context.get('score', 0):.0f} below threshold {context.get('threshold', 0):.0f}"
    elif rule == "CORRELATION_BREACH":
        return (
            f"Correlation {context.get('corr', 0):.2f} with {context.get('vs')} "
            f"exceeds threshold {context.get('threshold', 0):.2f}"
        )
    elif rule in ["EARNINGS", "FOMC", "CPI", "JOBS_REPORT"]:
        return f"{rule} event {context.get('days_until', 0)} days away"
    else:
        return f"{rule} {context}"


# Legacy reason code detection
def is_legacy_reason(code: str) -> bool:
    """Check if a reason appears to be old free-text format (not structured)."""
    if not code or isinstance(code, dict):
        return True
    return not is_structured_reason(code)
