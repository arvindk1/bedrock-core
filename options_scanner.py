import math
from datetime import datetime

import pandas as pd
import yfinance as yf
from scipy.stats import norm


def get_risk_free_rate():
    """Fetch 10-year Treasury yield as risk-free rate, default to 4%."""
    try:
        tnx = yf.Ticker("^TNX")
        hist = tnx.history(period="1d")
        if not hist.empty:
            return hist["Close"].iloc[-1] / 100
    except Exception:
        pass
    return 0.04


def calculate_greeks(S, K, T, r, sigma, option_type="call"):
    """Calculate Black-Scholes Greeks.

    Args:
        S: Current stock price
        K: Strike price
        T: Time to expiration in years
        r: Risk-free rate
        sigma: Implied volatility
        option_type: 'call' or 'put'

    Returns:
        dict with delta, gamma, theta, vega
    """
    if T <= 0 or sigma <= 0 or S <= 0 or K <= 0:
        return {"delta": 0, "gamma": 0, "theta": 0, "vega": 0}

    sqrt_T = math.sqrt(T)
    d1 = (math.log(S / K) + (r + sigma**2 / 2) * T) / (sigma * sqrt_T)
    d2 = d1 - sigma * sqrt_T

    n_d1 = norm.pdf(d1)  # N'(d1)

    gamma = n_d1 / (S * sigma * sqrt_T)
    vega = S * n_d1 * sqrt_T / 100  # per 1% move in IV

    if option_type == "call":
        delta = norm.cdf(d1)
        theta = (-(S * n_d1 * sigma) / (2 * sqrt_T)
                 - r * K * math.exp(-r * T) * norm.cdf(d2)) / 365
    else:
        delta = norm.cdf(d1) - 1
        theta = (-(S * n_d1 * sigma) / (2 * sqrt_T)
                 + r * K * math.exp(-r * T) * norm.cdf(-d2)) / 365

    return {"delta": delta, "gamma": gamma, "theta": theta, "vega": vega}


def score_option(delta, ask, theta):
    """Score an option by bang-for-buck: high delta exposure per dollar of premium and theta decay.

    Returns:
        float score (higher = better), or 0 if inputs are invalid
    """
    if ask <= 0 or abs(theta) < 1e-8:
        return 0.0
    return abs(delta) / (ask * abs(theta))


def fetch_options_chain(symbol, start_date, end_date):
    """Fetch options chain from yfinance for expirations within date range.

    Args:
        symbol: Stock ticker
        start_date: YYYY-MM-DD string
        end_date: YYYY-MM-DD string

    Returns:
        tuple: (ticker object, list of (expiration_str, chain_dataframe) pairs)
    """
    ticker = yf.Ticker(symbol)

    # Validate ticker has options
    try:
        expirations = ticker.options
    except Exception:
        raise ValueError(f"Could not fetch options for '{symbol}'. Verify the ticker is valid.")

    if not expirations:
        raise ValueError(f"No options available for '{symbol}'.")

    start = datetime.strptime(start_date, "%Y-%m-%d").date()
    end = datetime.strptime(end_date, "%Y-%m-%d").date()

    if start > end:
        raise ValueError(f"start_date ({start_date}) is after end_date ({end_date}).")

    filtered = [exp for exp in expirations
                if start <= datetime.strptime(exp, "%Y-%m-%d").date() <= end]

    if not filtered:
        raise ValueError(
            f"No expirations for '{symbol}' between {start_date} and {end_date}. "
            f"Available: {', '.join(expirations[:5])}{'...' if len(expirations) > 5 else ''}"
        )

    results = []
    for exp in filtered:
        chain = ticker.option_chain(exp)
        calls = chain.calls.copy()
        calls["optionType"] = "call"
        puts = chain.puts.copy()
        puts["optionType"] = "put"
        combined = _concat_frames(calls, puts)
        results.append((exp, combined))

    return ticker, results


def _concat_frames(calls, puts):
    """Concatenate calls and puts DataFrames."""
    return pd.concat([calls, puts], ignore_index=True)


def find_cheapest_options(symbol, start_date, end_date, top_n=5):
    """Find the cheapest options with the best Greeks profile.

    Args:
        symbol: Stock ticker
        start_date: YYYY-MM-DD start of expiration range
        end_date: YYYY-MM-DD end of expiration range
        top_n: Number of results to return

    Returns:
        str: Formatted results table
    """
    ticker, chains = fetch_options_chain(symbol, start_date, end_date)

    # Current stock price
    hist = ticker.history(period="1d")
    if hist.empty:
        raise ValueError(f"Could not fetch current price for '{symbol}'.")
    S = hist["Close"].iloc[-1]

    r = get_risk_free_rate()
    today = datetime.now().date()

    scored_options = []

    for exp_str, chain in chains:
        exp_date = datetime.strptime(exp_str, "%Y-%m-%d").date()
        T = (exp_date - today).days / 365.0
        if T <= 0:
            continue

        for _, row in chain.iterrows():
            K = row["strike"]
            sigma = row.get("impliedVolatility", 0)
            ask = row.get("ask", 0)
            bid = row.get("bid", 0)
            volume = row.get("volume", 0) or 0
            open_interest = row.get("openInterest", 0) or 0
            option_type = row["optionType"]

            # Filter illiquid
            if volume < 10 or open_interest < 10:
                continue
            if ask <= 0:
                continue
            if sigma <= 0:
                continue

            greeks = calculate_greeks(S, K, T, r, sigma, option_type)

            # Filter deep OTM
            if abs(greeks["delta"]) < 0.05:
                continue

            sc = score_option(greeks["delta"], ask, greeks["theta"])

            scored_options.append({
                "symbol": symbol.upper(),
                "type": option_type,
                "strike": K,
                "expiration": exp_str,
                "bid": bid,
                "ask": ask,
                "IV": sigma,
                "delta": greeks["delta"],
                "gamma": greeks["gamma"],
                "theta": greeks["theta"],
                "vega": greeks["vega"],
                "score": sc,
            })

    if not scored_options:
        return f"No liquid options found for {symbol} between {start_date} and {end_date}."

    scored_options.sort(key=lambda x: x["score"], reverse=True)
    top = scored_options[:top_n]

    return _format_results(top, S)


def _format_results(options, current_price):
    """Format options results as a readable text table."""
    lines = [f"Current Price: ${current_price:.2f}", ""]
    header = (
        f"{'Type':<5} {'Strike':>8} {'Exp':>12} {'Bid':>7} {'Ask':>7} "
        f"{'IV':>6} {'Delta':>7} {'Gamma':>7} {'Theta':>7} {'Vega':>6} {'Score':>8}"
    )
    lines.append(header)
    lines.append("-" * len(header))

    for o in options:
        lines.append(
            f"{o['type']:<5} {o['strike']:>8.2f} {o['expiration']:>12} "
            f"{o['bid']:>7.2f} {o['ask']:>7.2f} {o['IV']:>6.1%} "
            f"{o['delta']:>7.4f} {o['gamma']:>7.4f} {o['theta']:>7.4f} "
            f"{o['vega']:>6.2f} {o['score']:>8.2f}"
        )

    return "\n".join(lines)
