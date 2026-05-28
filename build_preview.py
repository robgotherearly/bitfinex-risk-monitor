"""
build_preview.py

Renders a self-contained static HTML snapshot of the dashboard to
reports/dashboard_preview.html. Useful for a README screenshot or for sharing a
view of the tool with someone who doesn't want to run Streamlit.

    python build_preview.py
"""

from __future__ import annotations

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

import config
from data_fetcher import load_candles, BitfinexClient
import risk_engine as re
import alerts
import charts

OUT = os.path.join("reports", "dashboard_preview.html")
P = charts.PALETTE


def tile(sym, snap, sev):
    cls = {"CRITICAL": "crit", "WARNING": "warn", "OK": "ok"}[sev]
    return f"""
      <div class="tile">
        <div class="sym">{sym}</div>
        <div class="status {cls}">{sev}</div>
        <div class="metrics">
          <span>vol <b>{snap['volatility']:.0f}%</b></span>
          <span>dd <b>{snap['drawdown']:.1f}%</b></span>
          <span>VaR95 <b>{snap['var_95']:.2f}%</b></span>
        </div>
      </div>"""


def alert_rows(log):
    if not len(log):
        return "<tr><td colspan='5' class='ok'>All markets within limits.</td></tr>"
    out = []
    for _, r in log.iterrows():
        cls = "crit" if r["severity"] == "CRITICAL" else "warn"
        out.append(
            f"<tr><td class='{cls}'>{r['severity']}</td><td>{r['symbol']}</td>"
            f"<td>{r['metric']}</td><td>{r['value']}</td><td>{r['message']}</td></tr>")
    return "\n".join(out)


def main():
    client = BitfinexClient()
    rows, all_alerts, charts_html, source = [], [], [], "?"

    focus = config.SYMBOLS[0]
    for sym in config.SYMBOLS:
        df = re.enrich(load_candles(sym, client))
        source = df.attrs.get("source", "?")
        snap = re.latest_snapshot(df)
        sym_alerts = alerts.evaluate(sym, snap)
        all_alerts += sym_alerts
        sev = ("CRITICAL" if any(a.severity == "CRITICAL" for a in sym_alerts)
               else "WARNING" if sym_alerts else "OK")
        rows.append(tile(sym, snap, sev))
        if sym == focus:
            for i, fig in enumerate((charts.price_drawdown_chart(df, config.THRESHOLDS),
                        charts.volatility_chart(df, config.THRESHOLDS),
                        charts.volume_zscore_chart(df, config.THRESHOLDS))):
                charts_html.append(fig.to_html(full_html=False,
                                                include_plotlyjs=("inline" if i == 0 else False),
                                                config={"displayModeBar": False}))

    log = alerts.to_dataframe(all_alerts)
    crit = (log["severity"] == "CRITICAL").sum() if len(log) else 0
    warn = (log["severity"] == "WARNING").sum() if len(log) else 0

    html = f"""<!doctype html><html><head><meta charset="utf-8">
<title>Bitfinex Risk Monitor</title>
<style>
  :root {{ --bg:{P['bg']}; --card:#161b22; --grid:{P['grid']};
           --text:{P['text']}; --muted:{P['muted']}; --accent:{P['accent']}; }}
  * {{ box-sizing:border-box; }}
  body {{ margin:0; background:var(--bg); color:var(--text);
          font-family:ui-monospace,SFMono-Regular,Menlo,monospace; }}
  .wrap {{ max-width:1180px; margin:0 auto; padding:28px 24px 56px; }}
  header {{ display:flex; align-items:baseline; gap:16px; border-bottom:1px solid var(--grid);
            padding-bottom:14px; margin-bottom:20px; }}
  h1 {{ font-size:20px; letter-spacing:.12em; margin:0; color:#fff; }}
  .meta {{ color:var(--muted); font-size:12px; }}
  .meta b.crit {{ color:{P['critical']}; }} .meta b.warn {{ color:{P['warning']}; }}
  .tiles {{ display:grid; grid-template-columns:repeat(5,1fr); gap:12px; margin-bottom:24px; }}
  .tile {{ background:var(--card); border:1px solid var(--grid); border-radius:10px; padding:14px; }}
  .tile .sym {{ color:var(--muted); font-size:11px; letter-spacing:.1em; }}
  .tile .status {{ font-size:20px; font-weight:700; margin:6px 0; }}
  .tile .metrics {{ display:flex; flex-direction:column; gap:2px; font-size:11px; color:var(--muted); }}
  .tile .metrics b {{ color:var(--text); }}
  .crit {{ color:{P['critical']}; }} .warn {{ color:{P['warning']}; }} .ok {{ color:{P['up']}; }}
  h2 {{ font-size:13px; letter-spacing:.14em; color:var(--muted); margin:26px 0 12px;
        text-transform:uppercase; }}
  table {{ width:100%; border-collapse:collapse; font-size:12px; }}
  th,td {{ text-align:left; padding:9px 12px; border-bottom:1px solid var(--grid); }}
  th {{ color:var(--muted); font-weight:500; letter-spacing:.06em; }}
  .charts {{ background:var(--card); border:1px solid var(--grid); border-radius:10px; padding:8px 6px; }}
  .row2 {{ display:grid; grid-template-columns:1fr 1fr; gap:8px; }}
  .badge {{ background:var(--card); border:1px solid var(--grid); border-radius:6px;
            padding:2px 8px; font-size:11px; color:var(--accent); }}
</style></head><body><div class="wrap">
  <header>
    <h1>◢ BITFINEX RISK MONITOR</h1>
    <span class="meta">source <span class="badge">{source}</span> &nbsp; {len(config.SYMBOLS)} markets &nbsp;
      <b class="crit">● {crit} critical</b> &nbsp; <b class="warn">● {warn} warning</b></span>
  </header>

  <div class="tiles">{''.join(rows)}</div>

  <h2>⚠ Active Alerts</h2>
  <table>
    <tr><th>Severity</th><th>Symbol</th><th>Metric</th><th>Value</th><th>Detail</th></tr>
    {alert_rows(log)}
  </table>

  <h2>📈 Market Detail — {focus}</h2>
  <div class="charts">{charts_html[0]}
    <div class="row2">{charts_html[1]}{charts_html[2]}</div>
  </div>
</div></body></html>"""

    os.makedirs("reports", exist_ok=True)
    with open(OUT, "w") as f:
        f.write(html)
    print(f"Wrote {OUT}  ({crit} critical, {warn} warning)")


if __name__ == "__main__":
    main()
