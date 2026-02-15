"""
Event Loader — Earnings & Macro Event Intelligence
====================================================
Provides earnings proximity checks, macro blackout detection,
and blocking-event aggregation for context-aware options trading.
"""

import logging
from datetime import date, datetime, timedelta
from typing import Dict, List, Optional, Tuple

import yfinance as yf

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# 2026 Macro Calendar Constants
# ---------------------------------------------------------------------------

FOMC_DATES_2026: List[date] = [
    date(2026, 1, 28),
    date(2026, 3, 18),
    date(2026, 5, 6),
    date(2026, 6, 17),
    date(2026, 7, 29),
    date(2026, 9, 16),
    date(2026, 10, 28),
    date(2026, 12, 9),
]

CPI_DATES_2026: List[date] = [
    date(2026, 1, 13),
    date(2026, 2, 11),
    date(2026, 3, 11),
    date(2026, 4, 14),
    date(2026, 5, 12),
    date(2026, 6, 10),
    date(2026, 7, 14),
    date(2026, 8, 12),
    date(2026, 9, 11),
    date(2026, 10, 13),
    date(2026, 11, 12),
    date(2026, 12, 10),
]

JOBS_DATES_2026: List[date] = [
    date(2026, 1, 2),
    date(2026, 2, 6),
    date(2026, 3, 6),
    date(2026, 4, 3),
    date(2026, 5, 1),
    date(2026, 6, 5),
    date(2026, 7, 3),
    date(2026, 8, 7),
    date(2026, 9, 4),
    date(2026, 10, 2),
    date(2026, 11, 6),
    date(2026, 12, 4),
]


# ---------------------------------------------------------------------------
# EventLoader
# ---------------------------------------------------------------------------

class EventLoader:
    """
    Earnings and macro-event intelligence for options trading.

    Checks:
    - Whether earnings fall inside a trade window (DTE)
    - Earnings proximity (within 7 days)
    - Macro blackout windows (FOMC, CPI, Jobs)
    - Combined blocking events for a symbol + DTE
    """

    def __init__(self, cache_duration_hours: int = 4, blackout_days: int = 1):
        self.cache_duration_hours = cache_duration_hours
        self.blackout_days = blackout_days
        self._cache: Dict[str, Dict] = {}
        self.macro_events: List[Dict] = self._build_macro_calendar()

    # ------------------------------------------------------------------
    # Macro calendar
    # ------------------------------------------------------------------

    def _build_macro_calendar(self) -> List[Dict]:
        """Combine FOMC, CPI, and Jobs dates into a unified event list."""
        events: List[Dict] = []

        for d in FOMC_DATES_2026:
            events.append({"name": "FOMC Meeting", "date": d, "impact": "high"})

        for d in CPI_DATES_2026:
            events.append({"name": "CPI Release", "date": d, "impact": "high"})

        for d in JOBS_DATES_2026:
            events.append({"name": "Jobs Report", "date": d, "impact": "medium"})

        return events

    # ------------------------------------------------------------------
    # Earnings helpers
    # ------------------------------------------------------------------

    def _get_days_until_earnings(self, symbol: str) -> Optional[int]:
        """Return days until next earnings for *symbol*, or None."""
        cache_key = f"earnings_{symbol}"
        if self._is_cache_valid(cache_key):
            return self._cache[cache_key]["data"]

        try:
            ticker = yf.Ticker(symbol)
            earnings_dates = ticker.earnings_dates

            if earnings_dates is None or earnings_dates.empty:
                self._set_cache(cache_key, None)
                return None

            now = datetime.now()
            future_mask = earnings_dates.index > now
            future_dates = earnings_dates.index[future_mask]

            if future_dates.empty:
                self._set_cache(cache_key, None)
                return None

            nearest = future_dates.min()
            days = (nearest - now).days
            self._set_cache(cache_key, days)
            return days

        except Exception as e:
            logger.warning("Could not fetch earnings for %s: %s", symbol, e)
            return None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def check_earnings_before_expiry(
        self, symbol: str, days_to_expiry: int
    ) -> Optional[Dict]:
        """
        Return a dict if earnings fall within *days_to_expiry*, else None.

        The dict contains:
          - earnings_days: int
          - affects_trade: True
          - warning: str
        """
        days = self._get_days_until_earnings(symbol)
        if days is None:
            return None

        if 0 <= days <= days_to_expiry:
            return {
                "earnings_days": days,
                "affects_trade": True,
                "type": "earnings",
                "warning": "Earnings event occurs before expiration.",
            }
        return None

    def get_earnings_proximity(self, symbol: str) -> Optional[int]:
        """Return days until earnings if within 7 days, else None."""
        days = self._get_days_until_earnings(symbol)
        if days is not None and 0 <= days <= 7:
            return days
        return None

    def is_macro_blackout(
        self, target_date
    ) -> Tuple[bool, Optional[str]]:
        """
        Check whether *target_date* falls within *blackout_days* of a
        macro event.  Accepts both ``date`` and ``datetime`` objects.

        Returns (is_blackout, event_name | None).
        """
        if isinstance(target_date, datetime):
            target_date = target_date.date()

        for event in self.macro_events:
            evt_date = event["date"]
            delta = abs((target_date - evt_date).days)
            if delta <= self.blackout_days:
                return True, event["name"]

        return False, None

    def get_blocking_events(
        self, symbol: str, days_to_expiry: int
    ) -> List[Dict]:
        """
        Aggregate earnings and macro events that fall within the trade
        window defined by *days_to_expiry*.
        """
        events: List[Dict] = []

        # Earnings check
        earnings = self.check_earnings_before_expiry(symbol, days_to_expiry)
        if earnings is not None:
            events.append(earnings)

        # Macro events within trade window
        today = date.today()
        expiry = today + timedelta(days=days_to_expiry)
        for evt in self.macro_events:
            if today <= evt["date"] <= expiry:
                events.append({
                    "type": "macro",
                    "name": evt["name"],
                    "date": evt["date"].isoformat(),
                    "impact": evt["impact"],
                })

        return events

    # ------------------------------------------------------------------
    # Cache helpers
    # ------------------------------------------------------------------

    def _is_cache_valid(self, key: str) -> bool:
        if key not in self._cache:
            return False
        ts = self._cache[key]["timestamp"]
        return (datetime.now() - ts).total_seconds() < self.cache_duration_hours * 3600

    def _set_cache(self, key: str, data) -> None:
        self._cache[key] = {"data": data, "timestamp": datetime.now()}
