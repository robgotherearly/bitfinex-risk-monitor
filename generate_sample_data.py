"""
generate_sample_data.py
========================
Generates realistic synthetic hourly OHLCV data for each configured symbol so
the dashboard runs with zero network access. The series uses geometric Brownian
motion with per-asset volatility, plus a few deliberately injected stress events
(a volatility spike, a sharp drawdown, a volume surge) so the alert logic has
something to catch in the demo.

Run once:  python generate_sample_data.py
"""

from __future__ import annotations

import os
import numpy as np
import pandas as pd

import config

RNG = np.random.default_rng(42)

# Rough starting prices and hourly vols per asset (purely illustrative).
PROFILES = {
    "tBTCUSD": dict(start=68000, vol=0.0050),
    "tETHUSD": dict(start=3500,  vol=0.0060),
    "tSOLUSD": dict(start=160,   vol=0.0085),
    "tLTCUSD": dict(start=85,    vol=0.0065),
    "tXRPUSD": dict(start=0.55,  vol=0.0070),
}


def _simulate(start: float, vol: float, n: int, inject: bool) -> pd.DataFrame:
    drift = -0.00002
    shocks = RNG.normal(drift, vol, n)

    if inject:
        # Volatility regime change in the final third.
        shocks[int(n * 0.66):] *= 2.0
        # A sharp single-bar drop to trigger return + drawdown alerts.
        shocks[int(n * 0.80)] = -0.055

    close = start * np.exp(np.cumsum(shocks))
    high = close * (1 + np.abs(RNG.normal(0, vol / 2, n)))
    low = close * (1 - np.abs(RNG.normal(0, vol / 2, n)))
    open_ = np.concatenate([[start], close[:-1]])

    base_vol = RNG.lognormal(mean=6, sigma=0.4, size=n)
    if inject:
        base_vol[int(n * 0.80)] *= 8  # volume surge alongside the price shock
    volume = base_vol

    idx = pd.date_range(end=pd.Timestamp.now("UTC").tz_localize(None).floor("h"),
                        periods=n, freq="h")
    return pd.DataFrame(
        {"open": open_, "high": high, "low": low, "close": close, "volume": volume},
        index=idx,
    ).rename_axis("timestamp")


def main():
    os.makedirs(config.SAMPLE_DATA_DIR, exist_ok=True)
    for symbol in config.SYMBOLS:
        prof = PROFILES.get(symbol, dict(start=100, vol=0.02))
        df = _simulate(prof["start"], prof["vol"], config.HISTORY_LIMIT, inject=True)
        path = os.path.join(config.SAMPLE_DATA_DIR, f"{symbol}.csv")
        df.to_csv(path)
        print(f"  wrote {len(df):>4} rows -> {path}")


if __name__ == "__main__":
    print("Generating synthetic sample data...")
    main()
    print("Done.")
