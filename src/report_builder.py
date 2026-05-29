"""
report_builder.py
=================
Turns the day's risk evaluation into two artefacts:

  * a self-contained HTML report (saved to reports/, suitable for emailing,
    committing, or serving as a static page), and
  * a compact plain-text / Markdown summary used as the body of Slack and
    email alerts.

Both share the same palette as the dashboard so the whole project looks like
one coherent tool.
"""

from __future__ import annotations

import os
from datetime import datetime, timezone

import pandas as pd

import charts  # for the shared PALETTE

P = charts.PALETTE


# --- HTML report ------------------------------------------------------------
def _status_for(symbol_alerts) -> str:
    if any(a.severity == "CRITICAL" for a in symbol_alerts):
        return "CRITICAL"
    if symbol_alerts:
        return "WARNING"
    return "OK"


def build_html(market_rows: list[dict], alert_log: pd.DataFrame,
               source: str) -> str:
    """market_rows: list of {symbol, snapshot, status} dicts."""
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    crit = int((alert_log["severity"] == "CRITICAL").sum()) if len(alert_log) else 0
    warn = int((alert_log["severity"] == "WARNING").sum()) if len(alert_log) else 0

    def market_row(r):
        s, snap, status = r["symbol"], r["snapshot"], r["status"]
        cls = {"CRITICAL": "crit", "WARNING": "warn", "OK": "ok"}[status]
        return (f"<tr><td>{s}</td><td>{snap['close']:.4g}</td>"
                f"<td>{snap['volatility']:.0f}%</td><td>{snap['drawdown']:.1f}%</td>"
                f"<td>{snap['return_pct']:.2f}%</td><td>{snap['volume_zscore']:.1f}</td>"
                f"<td>{snap['var_95']:.2f}%</td>"
                f"<td class='{cls}'>{status}</td></tr>")

    def alert_row(r):
        cls = "crit" if r["severity"] == "CRITICAL" else "warn"
        return (f"<tr><td class='{cls}'>{r['severity']}</td><td>{r['symbol']}</td>"
                f"<td>{r['metric']}</td><td>{r['value']}</td>"
                f"<td>{r['threshold']}</td><td>{r['message']}</td></tr>")

    markets = "\n".join(market_row(r) for r in market_rows)
    if len(alert_log):
        alerts_html = "\n".join(alert_row(r) for _, r in alert_log.iterrows())
    else:
        alerts_html = "<tr><td colspan='6' class='ok'>All markets within limits.</td></tr>"

    return f"""<!doctype html><html><head><meta charset="utf-8">
<title>Daily Risk Report — {now}</title>
<style>
  body {{ margin:0; background:{P['bg']}; color:{P['text']};
          font-family:ui-monospace,SFMono-Regular,Menlo,monospace; }}
  .wrap {{ max-width:920px; margin:0 auto; padding:32px 24px 56px; }}
  header {{ border-bottom:1px solid {P['grid']}; padding-bottom:14px; margin-bottom:22px; }}
  h1 {{ font-size:18px; letter-spacing:.14em; margin:0 0 6px; color:#fff; }}
  .meta {{ color:{P['muted']}; font-size:12px; }}
  .badge {{ border:1px solid {P['grid']}; border-radius:6px; padding:2px 8px; color:{P['accent']}; }}
  .summary {{ display:flex; gap:14px; margin:18px 0 6px; }}
  .card {{ background:#161b22; border:1px solid {P['grid']}; border-radius:10px;
           padding:14px 18px; flex:1; }}
  .card .n {{ font-size:26px; font-weight:700; }}
  .card .l {{ color:{P['muted']}; font-size:11px; letter-spacing:.08em; }}
  h2 {{ font-size:12px; letter-spacing:.16em; color:{P['muted']}; text-transform:uppercase;
        margin:30px 0 10px; }}
  table {{ width:100%; border-collapse:collapse; font-size:12px; }}
  th,td {{ text-align:left; padding:8px 10px; border-bottom:1px solid {P['grid']}; }}
  th {{ color:{P['muted']}; font-weight:500; }}
  .crit {{ color:{P['critical']}; }} .warn {{ color:{P['warning']}; }} .ok {{ color:{P['up']}; }}
  footer {{ color:{P['muted']}; font-size:11px; margin-top:34px; }}
</style></head><body><div class="wrap">
  <header>
    <h1>◢ DAILY RISK REPORT</h1>
    <div class="meta">{now} &nbsp;·&nbsp; data source <span class="badge">{source}</span></div>
  </header>

  <div class="summary">
    <div class="card"><div class="n crit">{crit}</div><div class="l">CRITICAL BREACHES</div></div>
    <div class="card"><div class="n warn">{warn}</div><div class="l">WARNINGS</div></div>
    <div class="card"><div class="n">{len(market_rows)}</div><div class="l">MARKETS MONITORED</div></div>
  </div>

  <h2>Market Summary</h2>
  <table>
    <tr><th>Symbol</th><th>Close</th><th>Vol</th><th>Drawdown</th><th>1-bar</th>
        <th>Vol z</th><th>VaR95</th><th>Status</th></tr>
    {markets}
  </table>

  <h2>Alerts &amp; Escalations</h2>
  <table>
    <tr><th>Severity</th><th>Symbol</th><th>Metric</th><th>Value</th><th>Limit</th><th>Detail</th></tr>
    {alerts_html}
  </table>

  <footer>Generated automatically by the Bitfinex Risk Monitor pipeline.
  CRITICAL items require escalation to the senior risk team. Market data © Bitfinex.</footer>
</div></body></html>"""


# --- text / markdown summary for notifications -----------------------------
def build_text_summary(alert_log: pd.DataFrame, source: str) -> str:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    crit = int((alert_log["severity"] == "CRITICAL").sum()) if len(alert_log) else 0
    warn = int((alert_log["severity"] == "WARNING").sum()) if len(alert_log) else 0

    lines = [f"*Daily Risk Report* — {now} (source: {source})",
             f"{crit} critical · {warn} warning"]
    if crit:
        lines.append("\nCRITICAL — escalate:")
        for _, r in alert_log[alert_log["severity"] == "CRITICAL"].iterrows():
            lines.append(f"  • {r['symbol']} {r['metric']}: {r['message']}")
    elif not len(alert_log):
        lines.append("\nAll monitored markets within limits.")
    return "\n".join(lines)


def save_html(html: str, out_dir: str = "reports") -> str:
    os.makedirs(out_dir, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d")
    dated = os.path.join(out_dir, f"risk_report_{stamp}.html")
    latest = os.path.join(out_dir, "latest_report.html")
    for path in (dated, latest):
        with open(path, "w", encoding="utf-8") as f:
            f.write(html)
    return latest