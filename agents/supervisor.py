import os
from core.state import AgentState
from core.math_engine import calculate_econode_roi
from integrations.slack_bot import send_approval_request
from integrations.audit_db import log_action

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")


def supervisor_agent(state: AgentState) -> AgentState:
    actionable = state.get("actionable", [])
    blocked = state.get("blocked", [])

    if not actionable:
        return {
            **state,
            "current_step": "supervisor_done",
            "messages": state["messages"] + ["[Supervisor] No actionable resources found."],
            "total_monthly_savings": 0.0,
            "approval_status": "N/A",
        }

    total_savings = sum(r["net_savings"] for r in actionable)
    roi_data = calculate_econode_roi(total_savings)

    audit_ids = []

    # Variance analysis — root cause attribution
    variance_lines = []
    for r in actionable:
        if r["cost_spike_pct"] > 50:
            variance_lines.append(
                f"Cost spike {r['cost_spike_pct']:.0f}% on {r['resource_id']} "
                f"({r['resource_type']}, {r['cpu_avg']}% CPU). "
                f"Team: {r['tags'].get('Team', 'untagged')}."
            )

    # One Slack message per actionable resource
    for r in actionable:
        action_str = (
            f"Terminate {r['resource_id']}"
            if r["classification"] == "ZOMBIE"
            else f"Rightsize {r['resource_id']} to smaller tier"
        )

        log_id = log_action(
            resource_id=r["resource_id"],
            resource_type=r["resource_type"],
            action=action_str,
            risk_score=r["risk_score"],
            risk_label=r["risk_label"],
            monthly_savings=r["net_savings"],
            approval_status="PENDING",
        )
        audit_ids.append(log_id)

        # Send individual Slack message for each resource
        send_approval_request(
            resource_id=r["resource_id"],
            resource_type=r["resource_type"],
            action=action_str,
            monthly_savings=r["net_savings"],
            risk_score=r["risk_score"],
            risk_label=r["risk_label"],
            log_id=log_id,
        )

    msgs = [
        f"[Supervisor] Playbook ready. Total: ${total_savings:,.2f}/month. "
        f"ROI: {roi_data['roi_multiplier']:,.0f}x. "
        f"Sent {len(actionable)} individual Slack approval request(s). "
        f"Audit IDs: {', '.join(audit_ids)}"
    ]
    if variance_lines:
        msgs.append(f"[Supervisor] Variance: {' | '.join(variance_lines)}")
    if blocked:
        blocked_lines = ["🔴 *EcoNode — SLA Protected Resources (no action taken):*"]
        for r in blocked:
            blocked_lines.append(
                f"• `{r['resource_id']}` ({r['resource_type']}) — "
                f"Risk score: {r['risk_score']} ({r['risk_label']}) — "
                f"${r['monthly_waste']:,.2f}/mo waste identified but protected"
            )
        from integrations.slack_bot import SLACK_WEBHOOK_URL
        import requests, json
        if SLACK_WEBHOOK_URL:
            requests.post(
                SLACK_WEBHOOK_URL,
                data=json.dumps({"text": "\n".join(blocked_lines)}),
                headers={"Content-Type": "application/json"},
                timeout=5,
            )
    return {
        **state,
        "total_monthly_savings": round(total_savings, 2),
        "manual_finops_cost": roi_data["manual_finops_cost"],
        "econode_runtime_cost": roi_data["econode_runtime_cost"],
        "roi_multiplier": roi_data["roi_multiplier"],
        "current_step": "supervisor_done",
        "approval_status": "PENDING",
        "audit_log_id": audit_ids[0] if audit_ids else None,
        "messages": msgs,
    }