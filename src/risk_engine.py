"""
risk_engine.py

The analytical core. Takes an OHLCV DataFrame and computes the risk metrics a
monitoring desk watches in real time. Every function is pure (input -> output),
which keeps the logic easy to test and reason about.

Metrics:
  * log returns (per candle, %)
  * rolling annualised volatility (%)
  * rolling max drawdown from peak (%)
  * volume z-score vs rolling baseline (anomaly detection)
  * Historical Value at Risk (VaR) and Expected Shortfall (ES)
"""

from __future__ import annotations

import numpy as np
import pandas as pd

import config


def add_returns(df: pd.DataFrame) -> pd.DataFrame:
    """Add per-candle log returns (as a %) to the frame."""
    df = df.copy()
    df["log_return"] = np.log(df["close"] / df["close"].shift(1))
    df["return_pct"] = df["log_return"] * 100
    return df


def add_volatility(df: pd.DataFrame,
                   window: int = config.ROLLING_WINDOW,
                   annualisation: float = config.ANNUALISATION) -> pd.DataFrame:
    """Rolling realised volatility, annualised and expressed in %."""
    df = df.copy()
    if "log_return" not in df:
        df = add_returns(df)
    df["volatility"] = (
        df["log_return"].rolling(window).std() * annualisation * 100
    )
    return df


def add_drawdown(df: pd.DataFrame,
                 window: int = config.ROLLING_WINDOW) -> pd.DataFrame:
    """Rolling drawdown: % below the highest close in the trailing window."""
    df = df.copy()
    rolling_peak = df["close"].rolling(window, min_periods=1).max()
    df["drawdown"] = (df["close"] / rolling_peak - 1) * 100
    return df


def add_volume_zscore(df: pd.DataFrame,
                      window: int = config.ROLLING_WINDOW) -> pd.DataFrame:
    """Volume anomaly score: standard deviations above the rolling mean volume."""
    df = df.copy()
    mean = df["volume"].rolling(window).mean()
    std = df["volume"].rolling(window).std()
    df["volume_zscore"] = (df["volume"] - mean) / std.replace(0, np.nan)
    return df


def compute_var(df: pd.DataFrame, confidence: float = 0.95) -> dict:
    """Historical VaR and Expected Shortfall on per-candle returns.

    Returned as positive % loss figures (the convention a risk report uses).
    """
    returns = df["return_pct"].dropna()
    if returns.empty:
        return {"var": float("nan"), "es": float("nan"), "confidence": confidence}
    var = np.percentile(returns, (1 - confidence) * 100)
    es = returns[returns <= var].mean()
    return {
        "var": abs(var),
        "es": abs(es) if not np.isnan(es) else abs(var),
        "confidence": confidence,
    }


def enrich(df: pd.DataFrame) -> pd.DataFrame:
    """Run the full metric pipeline on a raw OHLCV frame."""
    df = add_returns(df)
    df = add_volatility(df)
    df = add_drawdown(df)
    df = add_volume_zscore(df)
    return df


def latest_snapshot(df: pd.DataFrame) -> dict:
    """Most recent value of each metric — what the dashboard tiles display."""
    last = df.iloc[-1]
    var = compute_var(df)
    return {
        "close": float(last["close"]),
        "return_pct": float(last.get("return_pct", float("nan"))),
        "volatility": float(last.get("volatility", float("nan"))),
        "drawdown": float(last.get("drawdown", float("nan"))),
        "volume_zscore": float(last.get("volume_zscore", float("nan"))),
        "var_95": var["var"],
        "es_95": var["es"],
    }
