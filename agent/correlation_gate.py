"""
Correlation Gate v2 — Portfolio Diversification Check
=======================================================

Prevent over-concentration in correlated assets using:
1. Real correlations (rolling daily returns, default 60 days)
2. Heuristic fallback (sector-based) if prices unavailable
3. Top-3 risk-weighted positions only
4. Pair-specific thresholds (same symbol > same sector > different sector)
5. Standardized rejection reason codes

Threshold structure:
- Same symbol (e.g., AAPL ↔ AAPL): 0.90 (very strict)
- Same sector (e.g., AAPL ↔ MSFT): 0.70 (moderate)
- Different sector (e.g., AAPL ↔ GLD): 0.30 (lenient)

Rejection logic:
- For each candidate, check correlation against each top-3 position
- Compare corr to pair-specific threshold
- Reject on ANY violation; keep most severe reason
"""

import logging
from typing import Any, Optional

import numpy as np

logger = logging.getLogger(__name__)


class CorrelationGate:
    """
    Portfolio diversification check using return correlations (preferred),
    with conservative heuristic fallback.

    Reject if corr(candidate, position) > threshold(pair relationship).
    Only evaluate top N positions by risk dollars (default 3).
    """

    # Sector mapping (shared with correlation thresholds)
    SECTOR_MAP = {
        # Tech
        "AAPL": "TECHNOLOGY",
        "MSFT": "TECHNOLOGY",
        "NVDA": "TECHNOLOGY",
        "GOOGL": "TECHNOLOGY",
        "META": "TECHNOLOGY",
        "TSLA": "TECHNOLOGY",
        "AMZN": "TECHNOLOGY",
        # Finance
        "JPM": "FINANCE",
        "BAC": "FINANCE",
        "GS": "FINANCE",
        "WFC": "FINANCE",
        # Healthcare
        "PFE": "HEALTHCARE",
        "JNJ": "HEALTHCARE",
        "UNH": "HEALTHCARE",
        "LLY": "HEALTHCARE",
        # Energy
        "XOM": "ENERGY",
        "CVX": "ENERGY",
        "COP": "ENERGY",
        # Industrials
        "BA": "INDUSTRIALS",
        "GE": "INDUSTRIALS",
        "CAT": "INDUSTRIALS",
        # Consumer
        "WMT": "CONSUMER",
        "KO": "CONSUMER",
        "PG": "CONSUMER",
        # Utilities
        "NEE": "UTILITIES",
        "DUK": "UTILITIES",
        # Materials
        "NEM": "MATERIALS",
        "FCX": "MATERIALS",
        # Real Estate
        "SPG": "REALESTATE",
        "DLR": "REALESTATE",
        # Communication
        "VZ": "COMMUNICATION",
        "T": "COMMUNICATION",
        # Commodities/Index
        "GLD": "COMMODITIES",
        "USO": "COMMODITIES",
        "DBC": "COMMODITIES",
        "SPY": "INDEX",
        "QQQ": "INDEX",
        "IWM": "INDEX",
    }

    def __init__(
        self,
        lookback: int = 60,
        top_n_positions: int = 3,
        fallback_unknown_corr: float = 0.80,
        thresholds: Optional[dict[str, float]] = None,
    ):
        """
        Initialize correlation gate.

        Args:
            lookback: Days of price history to use for correlation (default 60)
            top_n_positions: Only check correlation against top N positions by risk (default 3)
            fallback_unknown_corr: Default correlation if can't compute (conservative)
            thresholds: Dict with "same_symbol", "same_sector", "different_sector" thresholds
        """
        self.lookback = lookback
        self.top_n_positions = top_n_positions
        self.fallback_unknown_corr = fallback_unknown_corr
        self.thresholds = thresholds or {
            "same_symbol": 0.90,
            "same_sector": 0.70,
            "different_sector": 0.30,
        }

    def filter_candidates(
        self,
        candidates: list[dict[str, Any]],
        portfolio: Optional[list[dict[str, Any]]] = None,
        portfolio_prices: Optional[dict[str, list[float]]] = None,
        candidate_prices: Optional[dict[str, list[float]]] = None,
    ) -> tuple[list[dict[str, Any]], list[tuple[dict[str, Any], str]]]:
        """
        Filter candidates based on correlation with top portfolio positions.

        Args:
            candidates: List of candidate spreads
            portfolio: List of existing positions with symbol, risk_dollars/notional
            portfolio_prices: Dict of {symbol: [price1, price2, ...]}
            candidate_prices: Dict of {symbol: [price1, price2, ...]} or alternate price source

        Returns:
            (accepted_candidates, rejections_with_reason_codes)
            Reason format: "CORR_REJECT|candidate=AAPL|vs=MSFT|corr=0.78|threshold=0.70|basis=prices"
        """
        portfolio = portfolio or []
        portfolio_prices = portfolio_prices or {}
        candidate_prices = candidate_prices or {}

        # No portfolio = no correlation concerns
        if not portfolio:
            logger.debug("Empty portfolio: all candidates pass correlation gate")
            return candidates, []

        # Select top N positions by risk dollars (descending)
        ranked = sorted(
            portfolio,
            key=lambda p: float(p.get("risk_dollars", p.get("notional", 0.0)) or 0.0),
            reverse=True,
        )
        check_positions = ranked[: self.top_n_positions]

        logger.debug(
            f"Checking correlation against top {len(check_positions)} positions "
            f"(of {len(portfolio)} total portfolio)"
        )

        accepted: list[dict[str, Any]] = []
        rejections: list[tuple[dict[str, Any], str]] = []

        for cand in candidates:
            c_sym = cand.get("symbol", "?")
            c_sector = self.SECTOR_MAP.get(c_sym, "UNKNOWN")

            worst_violation = None  # (severity, corr, threshold, p_sym, basis)

            for pos in check_positions:
                p_sym = pos.get("symbol", "?")
                p_sector = self.SECTOR_MAP.get(p_sym, "UNKNOWN")

                # Get pair-specific threshold
                threshold = self._pair_threshold(c_sym, c_sector, p_sym, p_sector)

                # Compute correlation (prices first, fallback to heuristic)
                corr, basis = self._corr_from_prices_or_fallback(
                    c_sym=c_sym,
                    c_sector=c_sector,
                    p_sym=p_sym,
                    p_sector=p_sector,
                    portfolio_prices=portfolio_prices,
                    candidate_prices=candidate_prices,
                )

                if corr is None:
                    continue

                # Check threshold
                if corr > threshold:
                    # Keep most severe violation: max(corr - threshold)
                    severity = corr - threshold
                    if (worst_violation is None) or (severity > worst_violation[0]):
                        worst_violation = (severity, corr, threshold, p_sym, basis)

            # If any pair violated, reject with most severe reason
            if worst_violation:
                _, corr, threshold, p_sym, basis = worst_violation
                reason = (
                    f"CORR_REJECT|candidate={c_sym}|vs={p_sym}|corr={corr:.2f}"
                    f"|threshold={threshold:.2f}|basis={basis}"
                )
                rejections.append((cand, reason))
                logger.debug(f"Correlation gate rejected {c_sym}: {reason}")
                continue

            accepted.append(cand)

        logger.info(
            f"Correlation gate: {len(accepted)} accepted, "
            f"{len(rejections)} rejected (checked against top {len(check_positions)} positions)"
        )
        return accepted, rejections

    def _pair_threshold(
        self, c_sym: str, c_sector: str, p_sym: str, p_sector: str
    ) -> float:
        """
        Determine threshold for this specific pair.

        Args:
            c_sym, c_sector: Candidate symbol and sector
            p_sym, p_sector: Portfolio position symbol and sector

        Returns:
            Correlation threshold (anything > this gets rejected)
        """
        # Same symbol = strictest threshold
        if c_sym == p_sym:
            return self.thresholds["same_symbol"]

        # Same sector = moderate threshold
        if c_sector != "UNKNOWN" and p_sector != "UNKNOWN" and c_sector == p_sector:
            return self.thresholds["same_sector"]

        # Different sector = lenient threshold
        return self.thresholds["different_sector"]

    def _corr_from_prices_or_fallback(
        self,
        c_sym: str,
        c_sector: str,
        p_sym: str,
        p_sector: str,
        portfolio_prices: dict[str, list[float]],
        candidate_prices: dict[str, list[float]],
    ) -> tuple[Optional[float], str]:
        """
        Compute correlation on return prices (preferred),
        fallback to sector heuristic if prices missing or too short.

        Returns:
            (correlation: 0.0-1.0 or None, basis: "prices" | "heuristic" | "unknown_default")
        """
        # Get price series for candidate and position
        c_px = candidate_prices.get(c_sym) or portfolio_prices.get(c_sym)
        p_px = portfolio_prices.get(p_sym)

        # Try real correlation on returns
        corr = self._rolling_corr(c_px, p_px, self.lookback)
        if corr is not None:
            return corr, "prices"

        # Fallback: sector heuristic (deterministic and explicit)
        if c_sym == p_sym:
            # Same symbol = very correlated
            return 0.95, "heuristic"

        if c_sector != "UNKNOWN" and p_sector != "UNKNOWN":
            if c_sector == p_sector:
                # Same sector = correlated
                return 0.70, "heuristic"
            # Different sector = uncorrelated
            return 0.20, "heuristic"

        # If we truly can't determine relationship, conservative default
        return self.fallback_unknown_corr, "unknown_default"

    @staticmethod
    def _rolling_corr(
        a_prices: Optional[list[float]], b_prices: Optional[list[float]], lookback: int
    ) -> Optional[float]:
        """
        Compute Pearson correlation of daily returns over lookback period.

        Args:
            a_prices: Price series for asset A
            b_prices: Price series for asset B
            lookback: Number of days to use

        Returns:
            Correlation (-1.0 to 1.0) or None if can't compute
        """
        if not a_prices or not b_prices:
            return None

        a = np.asarray(a_prices, dtype=float)
        b = np.asarray(b_prices, dtype=float)

        # Take most recent N prices (up to lookback)
        n = min(len(a), len(b), lookback)
        if n < 20:
            # Need at least 20 days to compute correlation reliably
            return None

        a = a[-n:]
        b = b[-n:]

        # Compute daily returns
        ra = np.diff(a) / a[:-1]
        rb = np.diff(b) / b[:-1]

        if len(ra) < 20:
            return None

        # Pearson correlation
        c = np.corrcoef(ra, rb)[0, 1]

        if np.isnan(c) or np.isinf(c):
            return None

        return float(c)
