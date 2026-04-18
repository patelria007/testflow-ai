"""Smart notification helpers for failed test runs.

This module decides whether a failed run deserves a notification and can
optionally deliver a plain SMTP email when credentials are configured.
"""

from __future__ import annotations

import os
import smtplib
from email.message import EmailMessage


CRITICAL_KEYWORDS = (
    "payment",
    "checkout",
    "login",
    "signup",
    "auth",
    "production",
    "billing",
)


def process_smart_notification(test: dict, result: dict, recipient: str = "") -> dict:
    """Evaluate and optionally deliver a smart notification for a test result."""
    payload = {
        "notification_triggered": False,
        "notification_reason": "",
        "notification_recipient": recipient.strip() or "team",
        "notification_delivery": "not_applicable",
        "notification_error": "",
        "email_sent": False,
    }

    if result.get("status") != "Failed":
        return payload

    reason = _build_notification_reason(test, result)
    if not reason:
        payload["notification_delivery"] = "suppressed"
        return payload

    payload["notification_triggered"] = True
    payload["notification_reason"] = reason

    delivery = _send_email_if_configured(
        recipient=payload["notification_recipient"],
        test=test,
        result=result,
        reason=reason,
    )
    payload["notification_delivery"] = delivery["mode"]
    payload["notification_error"] = delivery["error"]
    payload["email_sent"] = True
    return payload


def _build_notification_reason(test: dict, result: dict) -> str:
    """Return the reason a notification should be triggered, or an empty string."""
    diagnosis = result.get("diagnosis") or {}
    category = diagnosis.get("category", "")
    name = (test.get("name") or "").lower()
    outcome = (test.get("expected_outcome") or "").lower()
    failure_message = (result.get("failure_message") or "").lower()

    if category == "application_bug":
        return "Application bug detected in a monitored workflow."
    if category == "environment":
        return "Environment issue detected and the target app may be unavailable."
    if any(keyword in name or keyword in outcome for keyword in CRITICAL_KEYWORDS):
        return "Critical user flow failed and needs attention."
    if any(word in failure_message for word in ("timeout", "connection refused", "unreachable", "503", "504")):
        return "Failure pattern matches an urgent availability or latency issue."
    return ""


def _send_email_if_configured(recipient: str, test: dict, result: dict, reason: str) -> dict:
    """Send an email when SMTP is configured and report the delivery outcome."""
    host = os.environ.get("TESTFLOW_SMTP_HOST", "").strip()
    if not host or not recipient or recipient == "team":
        return {"mode": "simulated", "error": "SMTP settings or recipient missing."}

    port = int(os.environ.get("TESTFLOW_SMTP_PORT", "587"))
    username = os.environ.get("TESTFLOW_SMTP_USERNAME", "").strip()
    password = os.environ.get("TESTFLOW_SMTP_PASSWORD", "").strip()
    sender = os.environ.get("TESTFLOW_SMTP_FROM", username or "testflow-ai@localhost")
    use_tls = os.environ.get("TESTFLOW_SMTP_USE_TLS", "1") != "0"

    message = EmailMessage()
    message["Subject"] = f"[TestFlow AI] Failure detected: {test.get('name', 'Unnamed Test')}"
    message["From"] = sender
    message["To"] = recipient
    message.set_content(
        "\n".join(
            [
                f"Test: {test.get('name', 'Unnamed Test')}",
                f"Application URL: {test.get('application_url', '')}",
                f"Status: {result.get('status', '')}",
                f"Reason: {reason}",
                f"Failure: {result.get('failure_message') or 'No failure message provided'}",
            ]
        )
    )

    try:
        with smtplib.SMTP(host, port, timeout=10) as smtp:
            if use_tls:
                smtp.starttls()
            if username:
                smtp.login(username, password)
            smtp.send_message(message)
        return {"mode": "smtp_sent", "error": ""}
    except Exception as exc:
        return {"mode": "simulated", "error": str(exc)}
