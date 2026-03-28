import json
import os
import sys
sys.path.insert(0, '/var/task')

def lambda_handler(event, context):
    from dotenv import load_dotenv
    load_dotenv()

    # Import only what Lambda needs
    from integrations.aws_client import get_ec2_instances
    from integrations.slack_bot import send_approval_request
    from integrations.audit_db import log_action
    from core.math_engine import (
        calculate_zombie_savings,
        calculate_risk_score,
        calculate_econode_roi,
    )

    print("EcoNode Lambda starting...")

    # Get real instances
    instances = get_ec2_instances()
    print(f"Found {len(instances)} instance(s)")

    # Auditor — flag anomalies
    anomalies = []
    for r in instances:
        if r["daily_cost"] >= 0.01:
            anomalies.append(r)
    print(f"Anomalies flagged: {len(anomalies)}")

    # Telemetry — classify
    for r in anomalies:
        cpu = r["cpu_avg"]
        if cpu < 5.0:
            r["classification"] = "ZOMBIE"
        elif cpu < 30.0:
            r["classification"] = "UNDERUTILIZED"
        else:
            r["classification"] = "HEALTHY"

        savings = calculate_zombie_savings(
            r["resource_id"], r["resource_type"], r["hourly_cost"]
        )
        r.update(savings)

    # Risk — score each
    actionable = []
    blocked = []
    for r in anomalies:
        if r["classification"] == "HEALTHY":
            r["risk_label"] = "HEALTHY_SKIP"
            r["risk_score"] = 0.0
            continue

        result = calculate_risk_score(
            tags=r["tags"],
            last_deployment_days=r.get("last_deployment_days", 30),
            network_in_mb=r.get("network_in", 0),
        )
        r["risk_score"] = result["risk_score"]
        r["risk_label"] = result["risk_label"]

        if result["risk_label"] == "SAFE_TO_ACT":
            actionable.append(r)
        else:
            blocked.append(r)

    print(f"Actionable: {len(actionable)}, Blocked: {len(blocked)}")

    # Supervisor — send Slack per actionable resource
    total_savings = sum(r.get("net_savings", 0) for r in actionable)
    roi_data = calculate_econode_roi(total_savings)
    audit_ids = []

    for r in actionable:
        action_str = (
            f"Terminate {r['resource_id']}"
            if r["classification"] == "ZOMBIE"
            else f"Rightsize {r['resource_id']}"
        )

        log_id = log_action(
            resource_id=r["resource_id"],
            resource_type=r["resource_type"],
            action=action_str,
            risk_score=r["risk_score"],
            risk_label=r["risk_label"],
            monthly_savings=r.get("net_savings", 0),
            approval_status="PENDING",
        )
        audit_ids.append(log_id)

        send_approval_request(
            resource_id=r["resource_id"],
            resource_type=r["resource_type"],
            action=action_str,
            monthly_savings=r.get("net_savings", 0),
            risk_score=r["risk_score"],
            risk_label=r["risk_label"],
            log_id=log_id,
        )
        print(f"Slack sent for {r['resource_id']} — Audit ID: {log_id}")

    # Notify blocked resources
    if blocked:
        import requests
        webhook = os.getenv("SLACK_WEBHOOK_URL", "")
        if webhook:
            lines = ["🔴 *EcoNode — SLA Protected (no action taken):*"]
            for r in blocked:
                lines.append(
                    f"• `{r['resource_id']}` ({r['resource_type']}) — "
                    f"Risk: {r['risk_score']} ({r['risk_label']}) — "
                    f"${r.get('monthly_waste', 0):,.2f}/mo protected"
                )
            requests.post(
                webhook,
                json={"text": "\n".join(lines)},
                timeout=5,
            )

    result = {
        "statusCode": 200,
        "body": json.dumps({
            "status": "complete",
            "instances_scanned": len(instances),
            "anomalies_found": len(anomalies),
            "actionable": len(actionable),
            "blocked": len(blocked),
            "total_monthly_savings": round(total_savings, 2),
            "roi_multiplier": roi_data["roi_multiplier"],
            "audit_ids": audit_ids,
        })
    }

    print(f"Result: {result['body']}")
    return result