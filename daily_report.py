"""
daily_report.py
===============
The scheduled entry point. Runs the full daily risk process:

    1. Pull data for every configured market (live, with sample fallback).
    2. Compute risk metrics and evaluate them against the defined limits.
    3. Build a dated HTML report + a text summary.
    4. Escalate: post to Slack, and email on any critical breach.
    5. Exit non-zero if there were critical breaches (so CI surfaces it).

Run manually:   python daily_report.py
On a schedule:  see .github/workflows/daily-risk-report.yml
"""

from __future__ import annotations

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

import config
from data_fetcher import load_candles
import risk_engine as re
import alerts
import report_builder as rb
import notifier


def run() -> int:
    print("Running daily risk process...")
    market_rows, all_alerts, source = [], [], "?"

    for sym in config.SYMBOLS:
        df = re.enrich(load_candles(sym))
        source = df.attrs.get("source", "?")
        snap = re.latest_snapshot(df)
        sym_alerts = alerts.evaluate(sym, snap)
        all_alerts += sym_alerts
        market_rows.append({
            "symbol": sym,
            "snapshot": snap,
            "status": rb._status_for(sym_alerts),
        })
        print(f"  {sym}: {rb._status_for(sym_alerts)}")

    log = alerts.to_dataframe(all_alerts)
    has_critical = bool(len(log) and (log["severity"] == "CRITICAL").any())

    html = rb.build_html(market_rows, log, source)
    path = rb.save_html(html)
    summary = rb.build_text_summary(log, source)
    print(f"\nReport written to {path}")
    print("-" * 60)
    print(summary)
    print("-" * 60)

    print("Escalation:")
    notifier.escalate(summary, html, has_critical)

    # Non-zero exit on critical breach makes the scheduled job show as "failed"
    # in CI, which is a free, visible escalation signal on top of Slack/email.
    return 1 if has_critical else 0


if __name__ == "__main__":
    sys.exit(run())
