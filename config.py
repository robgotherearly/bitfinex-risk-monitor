"""
Central configuration for the Bitfinex Risk Monitor.

Everything an analyst would want to tune lives here: which markets to watch,
the lookback window, and the risk thresholds that trigger alerts. Keeping
thresholds in one declarative place mirrors how a real risk desk operates —
limits are defined, reviewed, and version-controlled, not buried in code.
"""

# --- Markets to monitor -----------------------------------------------------
# Bitfinex trading symbols are prefixed with "t" (e.g. tBTCUSD).
SYMBOLS = ["tBTCUSD", "tETHUSD", "tSOLUSD", "tLTCUSD", "tXRPUSD"]

# Candle timeframe for historical risk metrics.
# Valid Bitfinex values: 1m, 5m, 15m, 30m, 1h, 3h, 6h, 12h, 1D, 1W, 14D, 1M
TIMEFRAME = "1h"

# Number of historical candles to pull per symbol (max 10000 on Bitfinex).
HISTORY_LIMIT = 720  # 720 hourly candles ~= 30 days

# --- Risk thresholds (the "limits" the desk monitors) -----------------------
# Each breach is assigned a severity so issues can be escalated proportionately,
# exactly as the role describes ("escalate issues clearly and promptly").
THRESHOLDS = {
    # Annualised rolling volatility (%). Crypto runs hot, so these are wide.
    "volatility_warning": 60.0,
    "volatility_critical": 100.0,

    # Single-candle absolute return (%). A large jump in one bar is a red flag.
    "return_warning": 3.0,
    "return_critical": 6.0,

    # Volume z-score: how many standard deviations above the rolling mean.
    "volume_zscore_warning": 3.0,
    "volume_zscore_critical": 5.0,

    # Max drawdown from rolling peak (%), reported as a negative number.
    "drawdown_warning": -15.0,
    "drawdown_critical": -25.0,

    # Bid-ask spread as a fraction of mid price (%). Wide spreads = thin liquidity.
    "spread_warning": 0.10,
    "spread_critical": 0.30,
}

# Rolling window (in candles) used for volatility, volume baseline, drawdown.
ROLLING_WINDOW = 24  # 24 hourly candles = 1 day

# Annualisation factor for volatility. For hourly candles: sqrt(24 * 365).
# Adjust if you change TIMEFRAME.
ANNUALISATION = (24 * 365) ** 0.5

# --- Data source ------------------------------------------------------------
BITFINEX_REST_BASE = "https://api-pub.bitfinex.com/v2"
REQUEST_TIMEOUT = 15  # seconds

# If the API is unreachable (offline demo, rate limit, firewall), fall back to
# locally generated sample data so the dashboard always renders.
USE_SAMPLE_FALLBACK = True
SAMPLE_DATA_DIR = "data"
