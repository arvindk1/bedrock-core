from strands_agents import tool

from options_scanner import find_cheapest_options


@tool
def scan_options(symbol: str, start_date: str, end_date: str, top_n: int = 5) -> str:
    """
    Scans the options chain for the cheapest contracts with favorable Greeks.
    Calculates Black-Scholes Greeks (delta, gamma, theta, vega) and ranks
    options by bang-for-buck score (high delta exposure per dollar of premium
    and theta decay).

    Args:
        symbol: Stock ticker (e.g., 'AAPL')
        start_date: Start of expiration date range (YYYY-MM-DD)
        end_date: End of expiration date range (YYYY-MM-DD)
        top_n: Number of top results to return (default 5)
    """
    try:
        return find_cheapest_options(symbol, start_date, end_date, top_n)
    except ValueError as e:
        return f"Error: {e}"
    except Exception:
        return f"Error scanning options for {symbol}. Please verify the ticker and date range."
