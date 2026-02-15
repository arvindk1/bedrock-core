from strands.tools import tool

from options_scanner import find_cheapest_options

@tool
def scan_options(symbol: str, start_date: str, end_date: str, top_n: int = 5) -> str:
    """
    Find and rank the best (highest-scoring) liquid options contracts for a symbol
    within an expiration date window.

    Uses Black-Scholes Greeks (delta, gamma, theta, vega) and ranks contracts by a
    bang-for-buck score (delta exposure per dollar of premium and theta decay).

    Args:
        symbol: Stock ticker (e.g., 'AAPL')
        start_date: Earliest expiration date to consider (YYYY-MM-DD)
        end_date: Latest expiration date to consider (YYYY-MM-DD)
        top_n: Number of top results to return (default 5)

    Returns:
        A formatted table of ranked contracts, or an error string.
    """
    try:
        return find_cheapest_options(symbol, start_date, end_date, top_n)
    except ValueError as e:
        return f"Error: {e}"
    except Exception as e:
        # Helps debug egress/yfinance/runtime failures without leaking a stack trace
        return f"Error scanning options for {symbol}: {type(e).__name__}: {e}"
