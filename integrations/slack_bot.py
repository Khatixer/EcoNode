import os
import json
import requests
from dotenv import load_dotenv

load_dotenv()

SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL", "")


def send_approval_request(
    resource_id: str,
    resource_type: str,
    action: str,
    monthly_savings: float,
    risk_score: float,
    risk_label: str,
    log_id: str,
) -> bool:
    """
    Sends a formatted Slack message with the optimization recommendation.
    Returns True if sent successfully.
    """
    if not SLACK_WEBHOOK_URL:
        print("[Slack] No webhook URL configured — skipping notification.")
        return False

    risk_emoji = {"SAFE_TO_ACT": "🟢", "ESCALATE_ONLY": "🟡", "BLOCKED": "🔴"}.get(risk_label, "⚪")

    message = {
        "blocks": [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": "⚡ EcoNode: Cost Optimization Detected",
                }
            },
            {
                "type": "section",
                "fields": [
                    {"type": "mrkdwn", "text": f"*Resource ID:*\n`{resource_id}`"},
                    {"type": "mrkdwn", "text": f"*Type:*\n{resource_type}"},
                    {"type": "mrkdwn", "text": f"*Recommended Action:*\n{action}"},
                    {"type": "mrkdwn", "text": f"*Monthly Savings:*\n*${monthly_savings:,.2f}*"},
                    {"type": "mrkdwn", "text": f"*SLA Risk Score:*\n{risk_score} / 1.0"},
                    {"type": "mrkdwn", "text": f"*Risk Label:*\n{risk_emoji} {risk_label}"},
                    {"type": "mrkdwn", "text": f"*Audit Log ID:*\n`{log_id}`"},
                ]
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": (
                        f"EcoNode has identified a *${monthly_savings:,.2f}/month* savings opportunity.\n"
                        f"Risk assessment: {risk_emoji} *{risk_label}*\n\n"
                        f"_Human approval required before any action is taken._"
                    )
                }
            },
            {"type": "divider"},
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": (
                        f"✅ To *APPROVE*, reply: `econode approve {log_id}`\n"
                        f"❌ To *DENY*, reply: `econode deny {log_id}`"
                    )
                }
            }
        ]
    }

    try:
        resp = requests.post(
            SLACK_WEBHOOK_URL,
            data=json.dumps(message),
            headers={"Content-Type": "application/json"},
            timeout=5,
        )
        return resp.status_code == 200
    except Exception as e:
        print(f"[Slack] Failed to send: {e}")
        return False