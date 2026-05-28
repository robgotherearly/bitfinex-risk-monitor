"""
alerts.py

Turns metrics into actionable alerts. This is the part that mirrors the job's
core loop: check metrics against defined limits, classify severity, and produce
a clean, escalatable record of every breach.

Severity model:
    CRITICAL  -> escalate immediately to senior team
    WARNING   -> log, watch, include in the daily summary
    OK        -> within limits
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime, timezone

import pandas as pd

import config


@dataclass
class Alert:
    timestamp: str
    symbol: str
    metric: str
    value: float
    threshold: float
    severity: str           # "WARNING" | "CRITICAL"
    message: str

    def as_dict(self) -> dict:
        return asdict(self)


def _check(symbol, metric, value, warn, crit, fmt, higher_is_worse=True):
    """Compare a value against warning/critical limits and build an Alert."""
    if value is None or pd.isna(value):
        return None

    breached, severity = False, "OK"
    if higher_is_worse:
        if value >= crit:
            breached, severity, threshold = True, "CRITICAL", crit
        elif value >= warn:
            breached, severity, threshold = True, "WARNING", warn
    else:  # lower (more negative) is worse, e.g. drawdown
        if value <= crit:
            breached, severity, threshold = True, "CRITICAL", crit
        elif value <= warn:
            breached, severity, threshold = True, "WARNING", warn

    if not breached:
        return None

    return Alert(
        timestamp=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        symbol=symbol,
        metric=metric,
        value=round(float(value), 4),
        threshold=threshold,
        severity=severity,
        message=fmt.format(value=value, threshold=threshold),
    )


def evaluate(symbol: str, snapshot: dict, live_spread: float | None = None) -> list[Alert]:
    """Run every threshold check for one symbol and return triggered alerts."""
    t = config.THRESHOLDS
    candidates = [
        _check(symbol, "volatility", snapshot.get("volatility"),
               t["volatility_warning"], t["volatility_critical"],
               "Annualised volatility {value:.1f}% exceeds limit {threshold:.0f}%"),
        _check(symbol, "abs_return", abs(snapshot.get("return_pct") or 0),
               t["return_warning"], t["return_critical"],
               "Single-bar move {value:.2f}% exceeds limit {threshold:.0f}%"),
        _check(symbol, "volume_zscore", snapshot.get("volume_zscore"),
               t["volume_zscore_warning"], t["volume_zscore_critical"],
               "Volume spike {value:.1f}σ above baseline (limit {threshold:.0f}σ)"),
        _check(symbol, "drawdown", snapshot.get("drawdown"),
               t["drawdown_warning"], t["drawdown_critical"],
               "Drawdown {value:.1f}% beyond limit {threshold:.0f}%",
               higher_is_worse=False),
    ]
    if live_spread is not None:
        candidates.append(
            _check(symbol, "spread", live_spread,
                   t["spread_warning"], t["spread_critical"],
                   "Bid-ask spread {value:.3f}% exceeds limit {threshold:.2f}%")
        )
    return [a for a in candidates if a is not None]


def to_dataframe(alerts: list[Alert]) -> pd.DataFrame:
    """Collapse a list of alerts into a sortable DataFrame for the alert log."""
    if not alerts:
        return pd.DataFrame(
            columns=["timestamp", "symbol", "metric", "value",
                     "threshold", "severity", "message"]
        )
    df = pd.DataFrame([a.as_dict() for a in alerts])
    order = {"CRITICAL": 0, "WARNING": 1}
    df["__rank"] = df["severity"].map(order).fillna(2)
    df = df.sort_values(["__rank", "symbol"]).drop(columns="__rank")
    return df.reset_index(drop=True)
