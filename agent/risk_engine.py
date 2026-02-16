"""
Risk Engine — Deterministic "No Machine"
=========================================
Phase 1 core: per-trade risk gate, sector concentration, drawdown halt,
and portfolio-level risk analysis.

Key design decisions:
- Dollar-risk weighting (max_loss field), NOT position count
- Trade without max_loss is REJECTED for safety
- NO global singleton — callers instantiate RiskEngine
"""

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from reason_codes import Rules, format_reason_code, GATE_RISK

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Enums & Data Classes
# ---------------------------------------------------------------------------
class RiskSeverity(Enum):
    """Risk alert severity levels."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class ConcentrationAlert:
    """Risk concentration alert."""

    alert_type: str
    severity: RiskSeverity
    current_exposure: float
    limit_exposure: float
    message: str
    recommendation: str
    affected_positions: List[str] = field(default_factory=list)


@dataclass
class RiskMetric:
    """Individual risk metric measurement."""

    metric_name: str
    current_value: float
    limit_value: float
    percentage_of_limit: float
    severity: RiskSeverity
    description: str


# ---------------------------------------------------------------------------
# Sector Mapping (GICS-based fallback)
# ---------------------------------------------------------------------------
SECTOR_MAP: Dict[str, str] = {
    # Technology
    "AAPL": "Technology",
    "MSFT": "Technology",
    "GOOG": "Technology",
    "GOOGL": "Technology",
    "META": "Technology",
    "NVDA": "Technology",
    "AMD": "Technology",
    "INTC": "Technology",
    "CRM": "Technology",
    "ADBE": "Technology",
    "ORCL": "Technology",
    "AVGO": "Technology",
    "QCOM": "Technology",
    "TSM": "Technology",
    # Consumer Discretionary
    "AMZN": "Consumer Discretionary",
    "TSLA": "Consumer Discretionary",
    "NKE": "Consumer Discretionary",
    "HD": "Consumer Discretionary",
    "MCD": "Consumer Discretionary",
    "SBUX": "Consumer Discretionary",
    # Financials
    "JPM": "Financials",
    "GS": "Financials",
    "BAC": "Financials",
    "MS": "Financials",
    "V": "Financials",
    "MA": "Financials",
    # Healthcare
    "JNJ": "Healthcare",
    "UNH": "Healthcare",
    "PFE": "Healthcare",
    "ABBV": "Healthcare",
    "MRK": "Healthcare",
    "LLY": "Healthcare",
    # Energy
    "XOM": "Energy",
    "CVX": "Energy",
    "COP": "Energy",
    "SLB": "Energy",
    # Communication Services
    "DIS": "Communication Services",
    "NFLX": "Communication Services",
    "CMCSA": "Communication Services",
    "T": "Communication Services",
    "VZ": "Communication Services",
    # Industrials
    "BA": "Industrials",
    "CAT": "Industrials",
    "GE": "Industrials",
    "UPS": "Industrials",
    "HON": "Industrials",
    # Consumer Staples
    "PG": "Consumer Staples",
    "KO": "Consumer Staples",
    "PEP": "Consumer Staples",
    "WMT": "Consumer Staples",
    "COST": "Consumer Staples",
    # Indices / ETFs (map to broad market)
    "SPY": "Index",
    "QQQ": "Index",
    "IWM": "Index",
    "DIA": "Index",
}


# ---------------------------------------------------------------------------
# Risk Engine
# ---------------------------------------------------------------------------
class RiskEngine:
    """
    Deterministic risk gate for options trading.

    Enforces:
    - Per-trade max loss limit
    - Sector concentration caps (dollar-risk weighted)
    - Drawdown circuit breaker
    - Portfolio-level concentration analysis
    """

    def __init__(
        self,
        max_risk_per_trade: float = 1000.0,
        max_sector_pct: float = 0.25,
        max_correlation: float = 0.7,
        drawdown_halt_pct: float = 0.02,
    ):
        self.max_risk_per_trade = max_risk_per_trade
        self.max_sector_pct = max_sector_pct
        self.max_correlation = max_correlation
        self.drawdown_halt_pct = drawdown_halt_pct

    # ------------------------------------------------------------------
    # Per-Trade Gate
    # ------------------------------------------------------------------
    def should_reject_trade(
        self,
        trade: Dict[str, Any],
        portfolio: List[Dict[str, Any]],
        market_context: Optional[Dict[str, Any]] = None,
    ) -> Tuple[bool, Optional[str]]:
        """
        Determine whether a proposed trade should be rejected.

        Returns:
            (rejected: bool, reason: Optional[str])
        """
        # 1. Trade MUST declare max_loss
        max_loss = trade.get("max_loss")
        if max_loss is None:
            reason = format_reason_code(
                gate=GATE_RISK,
                rule=Rules.Risk.NO_MAX_LOSS,
                context={
                    "symbol": trade.get("symbol", "?"),
                    "strategy": trade.get("strategy_type", "?"),
                },
            )
            return True, reason

        # 2. Max loss per trade
        if max_loss > self.max_risk_per_trade:
            reason = format_reason_code(
                gate=GATE_RISK,
                rule=Rules.Risk.MAX_LOSS_EXCEEDED,
                context={
                    "symbol": trade.get("symbol", "?"),
                    "proposed": max_loss,
                    "limit": self.max_risk_per_trade,
                    "excess_pct": round((max_loss / self.max_risk_per_trade - 1) * 100),
                },
            )
            return True, reason

        # 3. Sector concentration check
        sector_rejected, sector_reason = self._check_sector_concentration(
            trade, portfolio
        )
        if sector_rejected:
            return True, sector_reason

        # 4. Drawdown circuit breaker via market_context
        if market_context:
            daily_pnl = market_context.get("daily_pnl", 0.0)
            portfolio_value = market_context.get("portfolio_value", 0.0)
            if portfolio_value > 0 and self.check_drawdown_halt(daily_pnl, portfolio_value):
                loss_pct = round(abs(daily_pnl) / portfolio_value * 100, 1)
                reason = format_reason_code(
                    gate=GATE_RISK,
                    rule=Rules.Risk.DRAWDOWN_HALT,
                    context={
                        "symbol": trade.get("symbol", "?"),
                        "daily_loss": abs(daily_pnl),
                        "portfolio_value": portfolio_value,
                        "loss_pct": loss_pct,
                        "limit": round(self.drawdown_halt_pct * 100, 1),
                    },
                )
                return True, reason

        return False, None

    # ------------------------------------------------------------------
    # Sector Concentration
    # ------------------------------------------------------------------
    def _check_sector_concentration(
        self,
        trade: Dict[str, Any],
        portfolio: List[Dict[str, Any]],
    ) -> Tuple[bool, Optional[str]]:
        """
        Check whether adding this trade would breach sector concentration.

        Uses dollar-risk weighting (max_loss), NOT position count.
        Falls back to SECTOR_MAP when position has no 'sector' field.
        """
        trade_sector = self._resolve_sector(trade)
        trade_risk = trade.get("max_loss", 0.0)

        # Sum total risk and sector risk across portfolio
        total_risk = trade_risk
        sector_risk = trade_risk  # the proposed trade's contribution

        for pos in portfolio:
            pos_risk = pos.get("max_loss", 0.0)
            total_risk += pos_risk
            if self._resolve_sector(pos) == trade_sector:
                sector_risk += pos_risk

        if total_risk == 0:
            return False, None

        sector_pct = sector_risk / total_risk
        if sector_pct > self.max_sector_pct:
            reason = format_reason_code(
                gate=GATE_RISK,
                rule=Rules.Risk.SECTOR_CAP,
                context={
                    "symbol": trade.get("symbol", "?"),
                    "sector": trade_sector,
                    "used": sector_risk,
                    "limit": total_risk * self.max_sector_pct,
                    "used_pct": round(sector_pct * 100),
                    "limit_pct": round(self.max_sector_pct * 100),
                },
            )
            return True, reason

        return False, None

    def _resolve_sector(self, position: Dict[str, Any]) -> str:
        """Return sector for a position, falling back to SECTOR_MAP."""
        sector = position.get("sector")
        if sector:
            return sector
        symbol = position.get("symbol", "UNKNOWN")
        return SECTOR_MAP.get(symbol, "Unknown")

    # ------------------------------------------------------------------
    # Drawdown Circuit Breaker
    # ------------------------------------------------------------------
    def check_drawdown_halt(
        self, daily_pnl: float, portfolio_value: float
    ) -> bool:
        """
        Return True if trading should HALT (daily loss exceeds threshold).

        Args:
            daily_pnl: Today's realised + unrealised P&L (negative = loss)
            portfolio_value: Start-of-day portfolio value
        """
        if portfolio_value <= 0:
            return False  # degenerate case — no valid basis, don't halt
        loss_pct = abs(daily_pnl) / portfolio_value if daily_pnl < 0 else 0.0
        return loss_pct >= self.drawdown_halt_pct

    # ------------------------------------------------------------------
    # Portfolio-Level Analysis
    # ------------------------------------------------------------------
    def analyze_portfolio_risk(
        self,
        positions: List[Dict[str, Any]],
        proposed_trades: Optional[List[Dict[str, Any]]] = None,
        market_context: Optional[Dict[str, Any]] = None,
    ) -> Tuple[List[ConcentrationAlert], List[RiskMetric]]:
        """
        Full portfolio risk analysis.

        Returns:
            (alerts, metrics)
        """
        all_positions = list(positions) + (proposed_trades or [])
        alerts: List[ConcentrationAlert] = []
        metrics: List[RiskMetric] = []

        if not all_positions:
            return alerts, metrics

        # Sector concentration
        sec_alerts, sec_metrics = self._analyze_sector_concentration(all_positions)
        alerts.extend(sec_alerts)
        metrics.extend(sec_metrics)

        # Strategy concentration
        strat_alerts, strat_metrics = self._analyze_strategy_concentration(all_positions)
        alerts.extend(strat_alerts)
        metrics.extend(strat_metrics)

        return alerts, metrics

    # ------------------------------------------------------------------
    # Sector Concentration Analysis
    # ------------------------------------------------------------------
    def _analyze_sector_concentration(
        self, positions: List[Dict[str, Any]]
    ) -> Tuple[List[ConcentrationAlert], List[RiskMetric]]:
        """Analyze sector concentration across all positions (dollar-risk weighted)."""
        alerts: List[ConcentrationAlert] = []
        metrics: List[RiskMetric] = []

        sector_risk: Dict[str, float] = {}
        sector_symbols: Dict[str, List[str]] = {}
        total_risk = 0.0

        for pos in positions:
            risk = pos.get("max_loss", 0.0)
            sector = self._resolve_sector(pos)
            symbol = pos.get("symbol", "UNKNOWN")
            total_risk += risk
            sector_risk[sector] = sector_risk.get(sector, 0.0) + risk
            sector_symbols.setdefault(sector, []).append(symbol)

        if total_risk == 0:
            return alerts, metrics

        for sector, risk in sector_risk.items():
            pct = risk / total_risk
            severity = self._severity_from_pct(pct / self.max_sector_pct)

            metrics.append(
                RiskMetric(
                    metric_name=f"Sector: {sector}",
                    current_value=pct,
                    limit_value=self.max_sector_pct,
                    percentage_of_limit=pct / self.max_sector_pct,
                    severity=severity,
                    description=f"{sector} exposure {pct:.0%} of total risk",
                )
            )

            if pct > self.max_sector_pct:
                alerts.append(
                    ConcentrationAlert(
                        alert_type="SECTOR_CONCENTRATION",
                        severity=RiskSeverity.CRITICAL,
                        current_exposure=pct,
                        limit_exposure=self.max_sector_pct,
                        message=f"{sector} sector at {pct:.0%} exceeds {self.max_sector_pct:.0%} limit",
                        recommendation=f"Reduce {sector} exposure before adding new positions",
                        affected_positions=sector_symbols.get(sector, []),
                    )
                )

        return alerts, metrics

    # ------------------------------------------------------------------
    # Strategy Concentration Analysis
    # ------------------------------------------------------------------
    def _analyze_strategy_concentration(
        self, positions: List[Dict[str, Any]]
    ) -> Tuple[List[ConcentrationAlert], List[RiskMetric]]:
        """Analyze strategy concentration (dollar-risk weighted)."""
        alerts: List[ConcentrationAlert] = []
        metrics: List[RiskMetric] = []

        strategy_risk: Dict[str, float] = {}
        strategy_symbols: Dict[str, List[str]] = {}
        total_risk = 0.0

        for pos in positions:
            risk = pos.get("max_loss", 0.0)
            strategy = self._normalize_strategy(pos.get("strategy", "unknown"))
            symbol = pos.get("symbol", "UNKNOWN")
            total_risk += risk
            strategy_risk[strategy] = strategy_risk.get(strategy, 0.0) + risk
            strategy_symbols.setdefault(strategy, []).append(symbol)

        if total_risk == 0:
            return alerts, metrics

        # Use a soft cap of 50% for any single strategy
        strategy_limit = 0.50

        for strategy, risk in strategy_risk.items():
            pct = risk / total_risk
            severity = self._severity_from_pct(pct / strategy_limit)

            metrics.append(
                RiskMetric(
                    metric_name=f"Strategy: {strategy}",
                    current_value=pct,
                    limit_value=strategy_limit,
                    percentage_of_limit=pct / strategy_limit,
                    severity=severity,
                    description=f"{strategy} exposure {pct:.0%} of total risk",
                )
            )

            if pct > strategy_limit:
                alerts.append(
                    ConcentrationAlert(
                        alert_type="STRATEGY_CONCENTRATION",
                        severity=RiskSeverity.HIGH,
                        current_exposure=pct,
                        limit_exposure=strategy_limit,
                        message=f"{strategy} strategy at {pct:.0%} exceeds {strategy_limit:.0%} soft cap",
                        recommendation=f"Diversify away from {strategy}",
                        affected_positions=strategy_symbols.get(strategy, []),
                    )
                )

        return alerts, metrics

    # ------------------------------------------------------------------
    # Correlation Check
    # ------------------------------------------------------------------
    def calculate_correlation(
        self, prices_a: np.ndarray, prices_b: np.ndarray
    ) -> float:
        """
        Calculate correlation between two price series using daily log returns.

        Returns correlation coefficient (-1 to 1), or 0.0 if insufficient data
        (fewer than 10 price points or fewer than 5 returns after log calculation).
        """
        a = np.asarray(prices_a, dtype=float)
        b = np.asarray(prices_b, dtype=float)

        # Use the shorter of the two series
        n = min(len(a), len(b))
        if n < 10:
            return 0.0

        a = a[:n]
        b = b[:n]

        # Daily log returns
        returns_a = np.diff(np.log(a))
        returns_b = np.diff(np.log(b))

        if len(returns_a) < 5:
            return 0.0

        corr_matrix = np.corrcoef(returns_a, returns_b)
        return float(corr_matrix[0, 1])

    def check_correlation_limit(
        self, correlation: float
    ) -> Tuple[bool, Optional[str]]:
        """
        Check whether a correlation value exceeds the configured threshold.

        Returns:
            (rejected: bool, reason: Optional[str])
        """
        if abs(correlation) > self.max_correlation:
            return (
                True,
                f"Rejected: correlation {correlation:.2f} exceeds limit "
                f"{self.max_correlation:.2f}",
            )
        return False, None

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _normalize_strategy(self, strategy: str) -> str:
        """Normalize strategy name to canonical form."""
        s = strategy.upper().replace("-", "_").replace(" ", "_")
        aliases = {
            "BULL_PUT_SPREAD": "PUT_CREDIT_SPREAD",
            "BULL_PUT": "PUT_CREDIT_SPREAD",
            "BEAR_CALL_SPREAD": "CALL_CREDIT_SPREAD",
            "BEAR_CALL": "CALL_CREDIT_SPREAD",
            "BULL_CALL_SPREAD": "CALL_DEBIT_SPREAD",
            "BULL_CALL": "CALL_DEBIT_SPREAD",
            "LONG_CALL": "LONG_OPTIONS",
            "LONG_PUT": "LONG_OPTIONS",
        }
        return aliases.get(s, s)

    def _severity_from_pct(self, pct_of_limit: float) -> RiskSeverity:
        """Convert percentage-of-limit to a severity level."""
        if pct_of_limit >= 1.0:
            return RiskSeverity.CRITICAL
        elif pct_of_limit >= 0.8:
            return RiskSeverity.HIGH
        elif pct_of_limit >= 0.6:
            return RiskSeverity.MEDIUM
        else:
            return RiskSeverity.LOW
