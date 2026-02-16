"""
Standardized Reason Codes Across Phase 2 Gates
================================================

Unified format for all rejection/warning reasons:
  [GATE_NAME]|rule=[RULE]|[context_fields]

Hard gates (block or reject trades):
  EVENT_BLOCK|rule=EARNINGS|symbol=AAPL|days_until=5
  RISK_REJECT|rule=MAX_LOSS_EXCEEDED|symbol=AAPL|proposed=1500|limit=1000
  GATEKEEP_REJECT|rule=LOW_SCORE|symbol=AAPL|score=65|threshold=70
  CORR_REJECT|rule=CORRELATION_BREACH|candidate=AAPL|vs=MSFT|corr=0.78|threshold=0.70

Soft gates (warnings, don't reject):
  GATEKEEP_WARN|rule=IV_PENALTY|symbol=AAPL|iv=0.60|condition=high_vol_debit
  EVENT_WARN|rule=EARNINGS_NEARBY|symbol=AAPL|days_until=10

DATA CONVENTIONS (critical for UI consistency):
  - All percentages stored as FRACTIONS (0.02 = 2%, 0.25 = 25%)
  - All dollars stored as dollars (e.g., proposed=1500, not 1500.00)
  - All dates in ISO format (YYYY-MM-DD)
  - All floats rounded to 4 decimals when needed (e.g., corr=0.7823)
  - Percent fields named with "_pct" (e.g., impact_pct, loss_pct)
"""

from typing import Any, Dict, Optional, Union


# Hard gate (reject/block - stops trade)
GATE_EVENT_BLOCK = "EVENT_BLOCK"
GATE_RISK_REJECT = "RISK_REJECT"
GATE_GATEKEEP_REJECT = "GATEKEEP_REJECT"
GATE_CORR_REJECT = "CORR_REJECT"

# Soft gate (warn - informational, allows trade)
GATE_GATEKEEP_WARN = "GATEKEEP_WARN"
GATE_EVENT_WARN = "EVENT_WARN"
GATE_RISK_WARN = "RISK_WARN"

# Legacy name mappings for backward compatibility
GATE_EVENT = GATE_EVENT_BLOCK
GATE_RISK = GATE_RISK_REJECT
GATE_GATEKEEP = GATE_GATEKEEP_REJECT
GATE_CORRELATION = GATE_CORR_REJECT

# Rule Definitions
class Rules:
    """All possible rejection/warning rules by gate."""

    class Event:
        # Hard blocks
        EARNINGS = "EARNINGS"
        FOMC = "FOMC"
        CPI = "CPI"
        JOBS_REPORT = "JOBS_REPORT"

    class Risk:
        # Hard rejections
        NO_MAX_LOSS = "NO_MAX_LOSS"
        MAX_LOSS_EXCEEDED = "MAX_LOSS_EXCEEDED"
        SECTOR_CAP = "SECTOR_CAP"
        DRAWDOWN_HALT = "DRAWDOWN_HALT"

    class Gatekeep:
        # Hard rejections
        LIQUIDITY = "LIQUIDITY"
        SPREAD_TOO_WIDE = "SPREAD_TOO_WIDE"
        LOW_SCORE = "LOW_SCORE"
        # Soft warnings
        IV_PENALTY = "IV_PENALTY"

    class Correlation:
        # Hard rejections
        CORRELATION_BREACH = "CORRELATION_BREACH"


# Recommended context fields for each rule (helps validate completeness)
RECOMMENDED_FIELDS = {
    # Risk rejects
    "MAX_LOSS_EXCEEDED": ["symbol", "proposed", "limit", "excess_pct"],
    "NO_MAX_LOSS": ["symbol", "strategy"],
    "SECTOR_CAP": ["symbol", "sector", "used", "limit", "used_pct"],
    "DRAWDOWN_HALT": ["daily_loss", "portfolio_value", "loss_pct", "limit"],
    # Gatekeeper
    "LIQUIDITY": ["symbol", "impact_pct", "threshold", "min_oi"],
    "SPREAD_TOO_WIDE": ["symbol", "leg", "spread_pct", "bid", "threshold"],
    "LOW_SCORE": ["symbol", "strategy", "score", "threshold", "deficit"],
    "IV_PENALTY": ["symbol", "strategy", "condition", "iv", "threshold"],
    # Events
    "EARNINGS": ["symbol", "days_until", "dte"],
    "FOMC": ["symbol", "name", "days_until", "dte"],
    "CPI": ["symbol", "name", "days_until", "dte"],
    "JOBS_REPORT": ["symbol", "name", "days_until", "dte"],
    # Correlation
    "CORRELATION_BREACH": ["candidate", "vs", "corr", "threshold", "basis"],
}


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

        # Parse value types: bool, null, int, float, string
        if val == "true":
            val = True
        elif val == "false":
            val = False
        elif val == "null":
            val = None
        else:
            # Try int first (including negatives), then float, then string
            try:
                val = int(val)
            except ValueError:
                try:
                    # Handles floats, negatives, scientific notation
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

    # Check gate name is known (hard rejects or soft warns)
    valid_gates = [
        GATE_EVENT_BLOCK,
        GATE_RISK_REJECT,
        GATE_GATEKEEP_REJECT,
        GATE_CORR_REJECT,
        GATE_GATEKEEP_WARN,
        GATE_EVENT_WARN,
        GATE_RISK_WARN,
    ]
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
    # NOTE: Percentages stored as fractions (0.02 = 2%), use :.0f format after *100
    if rule == "MAX_LOSS_EXCEEDED":
        return f"Max loss ${context.get('proposed')} exceeds limit ${context.get('limit')}"
    elif rule == "SECTOR_CAP":
        sector = context.get("sector", "UNKNOWN")
        used_pct = context.get("used_pct", 0)
        # used_pct is already in percent units (e.g., 125 for 125%)
        return f"Sector {sector} cap exceeded: {used_pct:.0f}% used"
    elif rule == "DRAWDOWN_HALT":
        # loss_pct is already in percent units (e.g., 2.5 for 2.5%)
        loss_pct = context.get("loss_pct", 0)
        limit_pct = context.get("limit", 0)
        return f"Daily drawdown {loss_pct:.1f}% exceeds {limit_pct:.1f}% limit"
    elif rule == "LIQUIDITY":
        # impact_pct is already in percent units (e.g., 3.2 for 3.2%)
        impact_pct = context.get("impact_pct", 0)
        threshold = context.get("threshold", 0)
        return f"Market impact {impact_pct:.1f}% exceeds {threshold:.1f}% threshold"
    elif rule == "SPREAD_TOO_WIDE":
        # spread_pct is in percent units (e.g., 10 for 10%)
        leg = context.get("leg", 0)
        spread_pct = context.get("spread_pct", 0)
        return f"Leg {leg} bid/ask spread {spread_pct:.1f}% too wide"
    elif rule == "LOW_SCORE":
        return f"Score {context.get('score', 0):.0f} below threshold {context.get('threshold', 0):.0f}"
    elif rule == "IV_PENALTY":
        condition = context.get("condition", "UNKNOWN")
        iv = context.get("iv", 0)
        threshold = context.get("threshold", 0)
        return f"IV penalty ({condition}): IV {iv:.3f} vs threshold {threshold:.3f}"
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
def is_legacy_reason(code: Union[str, dict, list, None]) -> bool:
    """
    Check if a reason appears to be old free-text format (not structured).

    Returns True if:
    - code is None or empty
    - code is a dict or list (shouldn't be serialized as code)
    - code is a string but doesn't match structured format
    """
    if code is None or code == "":
        return True
    if isinstance(code, (dict, list)):
        return True
    if not isinstance(code, str):
        return True
    return not is_structured_reason(code)
