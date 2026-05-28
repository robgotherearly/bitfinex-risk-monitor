"""
app.py

Live risk-monitoring dashboard. Run with:

    streamlit run app.py

Pulls real data from Bitfinex (public API, no key needed). If the API is
unreachable it falls back to the bundled sample data, so the dashboard always
renders. Auto-refreshes the live spread and re-evaluates all limits on each run.
"""

from __future__ import annotations

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

import streamlit as st

import config
from data_fetcher import load_candles, get_live_spread, BitfinexClient
import risk_engine as re
import alerts
import charts

st.set_page_config(page_title="Bitfinex Risk Monitor", layout="wide",
                   initial_sidebar_state="collapsed")

st.markdown("""
<style>
  .stApp { background:#0d1117; }
  h1,h2,h3,h4,p,span,div { color:#c9d1d9; font-family: ui-monospace, monospace; }
  .tile { background:#161b22; border:1px solid #1f2630; border-radius:8px;
          padding:12px 14px; }
  .tile .label { color:#6e7681; font-size:11px; letter-spacing:.08em; }
  .tile .value { font-size:22px; font-weight:600; }
  .crit { color:#f6465d; } .warn { color:#e3b341; } .ok { color:#26a17b; }
</style>
""", unsafe_allow_html=True)

st.title("◢ BITFINEX RISK MONITOR")

client = BitfinexClient()

# --- evaluate every symbol -------------------------------------------------
rows, all_alerts, frames = [], [], {}
for sym in config.SYMBOLS:
    df = re.enrich(load_candles(sym, client))
    frames[sym] = df
    snap = re.latest_snapshot(df)
    spread = get_live_spread(sym, client)
    sym_alerts = alerts.evaluate(sym, snap, spread)
    all_alerts += sym_alerts
    sev = ("CRITICAL" if any(a.severity == "CRITICAL" for a in sym_alerts)
           else "WARNING" if sym_alerts else "OK")
    rows.append((sym, snap, sev, df.attrs.get("source", "?")))

source = rows[0][3] if rows else "?"
crit = sum(1 for a in all_alerts if a.severity == "CRITICAL")
warn = sum(1 for a in all_alerts if a.severity == "WARNING")
st.caption(f"data source: **{source}**  ·  markets: {len(config.SYMBOLS)}  "
           f"·  🔴 {crit} critical  ·  🟡 {warn} warning")

# --- status tiles ----------------------------------------------------------
cols = st.columns(len(rows))
for col, (sym, snap, sev, _) in zip(cols, rows):
    cls = {"CRITICAL": "crit", "WARNING": "warn", "OK": "ok"}[sev]
    col.markdown(f"""
      <div class="tile">
        <div class="label">{sym}</div>
        <div class="value {cls}">{sev}</div>
        <div class="label">vol {snap['volatility']:.0f}%  ·  dd {snap['drawdown']:.1f}%</div>
        <div class="label">VaR95 {snap['var_95']:.2f}%</div>
      </div>""", unsafe_allow_html=True)

# --- alert log -------------------------------------------------------------
st.subheader("⚠ ACTIVE ALERTS")
log = alerts.to_dataframe(all_alerts)
if len(log):
    st.dataframe(log[["severity", "symbol", "metric", "value",
                      "threshold", "message"]], use_container_width=True,
                 hide_index=True)
else:
    st.success("All monitored markets within limits.")

# --- per-symbol charts -----------------------------------------------------
st.subheader("📈 MARKET DETAIL")
focus = st.selectbox("symbol", config.SYMBOLS)
df = frames[focus]
st.plotly_chart(charts.price_drawdown_chart(df, config.THRESHOLDS),
                use_container_width=True)
c1, c2 = st.columns(2)
c1.plotly_chart(charts.volatility_chart(df, config.THRESHOLDS),
                use_container_width=True)
c2.plotly_chart(charts.volume_zscore_chart(df, config.THRESHOLDS),
                use_container_width=True)
