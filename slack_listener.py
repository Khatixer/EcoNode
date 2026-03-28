import os
import sqlite3
from flask import Flask, request
from slack_sdk import WebClient
from dotenv import load_dotenv

load_dotenv()

flask_app = Flask(__name__)
slack_client = WebClient(token=os.getenv("SLACK_BOT_TOKEN"))


def get_boto3_client(service: str):
    """
    Creates a boto3 client.
    On Lambda: uses IAM role automatically.
    Locally: uses keys from environment variables.
    """
    import boto3
    access_key = os.getenv("AWS_ACCESS_KEY_ID")
    secret_key = os.getenv("AWS_SECRET_ACCESS_KEY")
    region = os.getenv("AWS_DEFAULT_REGION", os.getenv("AWS_REGION", "us-east-1"))

    if access_key and secret_key:
        return boto3.client(
            service,
            region_name=region,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
        )
    else:
        return boto3.client(service, region_name=region)


def get_record(log_id: str):
    conn = sqlite3.connect("econode_audit.db")
    c = conn.cursor()
    c.execute(
        "SELECT id, resource_id, resource_type, approval_status FROM audit_log WHERE id=?",
        (log_id.upper(),)
    )
    row = c.fetchone()
    conn.close()
    return row


def mark_approved(log_id: str, user: str):
    conn = sqlite3.connect("econode_audit.db")
    c = conn.cursor()
    c.execute(
        "UPDATE audit_log SET approval_status='APPROVED', approved_by=?, executed=1 WHERE id=?",
        (user, log_id.upper())
    )
    conn.commit()
    conn.close()


def mark_denied(log_id: str, user: str):
    conn = sqlite3.connect("econode_audit.db")
    c = conn.cursor()
    c.execute(
        "UPDATE audit_log SET approval_status='DENIED', approved_by=?, executed=0 WHERE id=?",
        (user, log_id.upper())
    )
    conn.commit()
    conn.close()


def terminate_resource(resource_id: str, resource_type: str) -> str:
    try:
        ec2 = get_boto3_client("ec2")
        if "vol-" in resource_id:
            ec2.delete_volume(VolumeId=resource_id)
            return f"EBS volume `{resource_id}` deleted."
        else:
            ec2.terminate_instances(InstanceIds=[resource_id])
            return f"EC2 instance `{resource_id}` terminated."
    except Exception as e:
        return f"Action failed: {e}"


def send_slack(channel: str, text: str):
    try:
        slack_client.chat_postMessage(channel=channel, text=text)
    except Exception as e:
        print(f"Slack send error: {e}")


@flask_app.route("/slack/events", methods=["GET"])
def verify_get():
    return "EcoNode listener is running.", 200


@flask_app.route("/slack/events", methods=["POST"])
def slack_events():
    print("\n=== INCOMING REQUEST ===")
    print("Body:", request.get_data(as_text=True)[:500])
    print("========================\n")

    data = request.json or {}

    # Slack URL verification
    if data.get("type") == "url_verification":
        return data.get("challenge"), 200

    # Handle message events
    event = data.get("event", {})
    if event.get("type") == "message" and not event.get("bot_id"):
        text = event.get("text", "").strip()
        channel = event.get("channel", "")
        user = event.get("user", "unknown")

        print(f"MESSAGE: '{text}' from {user} in {channel}")

        parts = text.split()
        if len(parts) < 2 or parts[0].lower() != "econode":
            return "ok", 200

        command = parts[1].lower() if len(parts) > 1 else ""

        # --- APPROVE ---
        if command == "approve" and len(parts) >= 3:
            log_id = parts[2].upper()
            row = get_record(log_id)

            if not row:
                send_slack(channel, f"No record found for `{log_id}`. Type `econode status` to see pending items.")
                return "ok", 200

            _, resource_id, resource_type, status = row

            if status != "PENDING":
                send_slack(channel, f"Audit ID `{log_id}` is already `{status}`. No action taken.")
                return "ok", 200

            mark_approved(log_id, user)
            result = terminate_resource(resource_id, resource_type)
            send_slack(
                channel,
                f"✅ *APPROVED* — Audit ID `{log_id}`\n"
                f"Resource: `{resource_id}` ({resource_type})\n"
                f"Result: {result}\n"
                f"Approved by: <@{user}> | Audit record updated."
            )

        # --- DENY ---
        elif command == "deny" and len(parts) >= 3:
            log_id = parts[2].upper()
            row = get_record(log_id)

            if not row:
                send_slack(channel, f"No record found for `{log_id}`.")
                return "ok", 200

            _, resource_id, resource_type, status = row

            if status != "PENDING":
                send_slack(channel, f"Audit ID `{log_id}` is already `{status}`.")
                return "ok", 200

            mark_denied(log_id, user)
            send_slack(
                channel,
                f"❌ *DENIED* — Audit ID `{log_id}`\n"
                f"Resource: `{resource_id}` ({resource_type})\n"
                f"No action taken. Denied by: <@{user}> | Audit record updated."
            )

        # --- STATUS ---
        elif command == "status":
            conn = sqlite3.connect("econode_audit.db")
            c = conn.cursor()
            c.execute(
                "SELECT id, resource_id, monthly_savings, approval_status "
                "FROM audit_log ORDER BY timestamp DESC LIMIT 8"
            )
            rows = c.fetchall()
            conn.close()

            if not rows:
                send_slack(channel, "No audit records found.")
            else:
                lines = ["*Recent EcoNode audit log:*"]
                for log_id, res_id, savings, s in rows:
                    icon = "✅" if s == "APPROVED" else "❌" if s == "DENIED" else "⏳"
                    lines.append(
                        f"{icon} `{log_id}` | `{res_id[:20]}` | ${savings:,.2f}/mo | {s}"
                    )
                send_slack(channel, "\n".join(lines))

        # --- UNKNOWN COMMAND ---
        else:
            send_slack(
                channel,
                "Unknown command. Available commands:\n"
                "• `econode approve <LOG_ID>`\n"
                "• `econode deny <LOG_ID>`\n"
                "• `econode status`"
            )

    return "ok", 200


if __name__ == "__main__":
    channel = os.getenv("SLACK_CHANNEL", "#general")
    print("=" * 50)
    print("EcoNode Slack listener — port 3000")
    print(f"Sending startup message to {channel}")
    print("=" * 50)

    try:
        slack_client.chat_postMessage(
            channel=channel,
            text=(
                "⚡ *EcoNode listener is online*\n"
                "Waiting for scan results.\n"
                "Commands: `econode approve <ID>` | "
                "`econode deny <ID>` | `econode status`"
            )
        )
        print("Startup message sent.")
    except Exception as e:
        print(f"Could not send startup message: {e}")

    flask_app.run(port=3000, debug=False)