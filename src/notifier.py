"""
notifier.py
===========
Escalation channels. Sends the daily summary (and any critical breaches) to
Slack and/or email. Both are configured purely through environment variables
so secrets never touch the codebase — locally you set them in your shell, and
in CI you store them as GitHub Actions secrets.

If a channel isn't configured, it's skipped quietly. This means the pipeline
runs end-to-end with zero setup (report only), and gains alerting the moment
you add the relevant secrets.

Environment variables
----------------------
Slack : SLACK_WEBHOOK_URL
Email : SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASS, ALERT_EMAIL_TO
"""

from __future__ import annotations

import os
import smtplib
import ssl
from email.message import EmailMessage

import requests


def notify_slack(text: str) -> bool:
    """Post the summary to a Slack incoming webhook. Returns True if sent."""
    url = os.environ.get("SLACK_WEBHOOK_URL")
    if not url:
        print("  slack: skipped (SLACK_WEBHOOK_URL not set)")
        return False
    try:
        resp = requests.post(url, json={"text": text}, timeout=10)
        resp.raise_for_status()
        print("  slack: sent")
        return True
    except Exception as exc:  # noqa: BLE001
        print(f"  slack: failed ({exc})")
        return False


def notify_email(subject: str, body: str, html: str | None = None) -> bool:
    """Send the summary by email via SMTP. Returns True if sent."""
    host = os.environ.get("SMTP_HOST")
    to_addr = os.environ.get("ALERT_EMAIL_TO")
    user = os.environ.get("SMTP_USER")
    password = os.environ.get("SMTP_PASS")
    port = int(os.environ.get("SMTP_PORT", "587"))

    if not (host and to_addr and user and password):
        print("  email: skipped (SMTP_* / ALERT_EMAIL_TO not set)")
        return False

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = user
    msg["To"] = to_addr
    msg.set_content(body)
    if html:
        msg.add_alternative(html, subtype="html")

    try:
        ctx = ssl.create_default_context()
        with smtplib.SMTP(host, port, timeout=15) as server:
            server.starttls(context=ctx)
            server.login(user, password)
            server.send_message(msg)
        print("  email: sent")
        return True
    except Exception as exc:  # noqa: BLE001
        print(f"  email: failed ({exc})")
        return False


def escalate(summary_text: str, html_report: str, has_critical: bool) -> None:
    """Fan out the summary to all configured channels.

    Slack always receives the daily summary. Email is reserved for days with a
    critical breach (so the inbox only pings when action is genuinely needed) —
    tune this policy to taste.
    """
    notify_slack(summary_text)
    if has_critical:
        notify_email(
            subject="[RISK] Critical limit breach — action required",
            body=summary_text,
            html=html_report,
        )
    else:
        print("  email: skipped (no critical breaches today)")
