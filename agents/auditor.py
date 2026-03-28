from core.state import AgentState
from integrations.aws_client import get_ec2_instances

SPIKE_THRESHOLD = 50.0   # flag if cost spiked >50%
ANOMALY_MIN_DAILY = 0.01  # only care about resources costing >$1/day


def auditor_agent(state: AgentState) -> AgentState:
    """
    Agent 1: Spend Intelligence
    Fetches all running resources, filters for cost anomalies.
    """
    raw = get_ec2_instances()

    anomalies = []
    for r in raw:
        if r["daily_cost"] >= ANOMALY_MIN_DAILY or r["cost_spike_pct"] >= SPIKE_THRESHOLD:
            anomalies.append({
                "resource_id": r["resource_id"],
                "resource_type": r["resource_type"],
                "service": r["service"],
                "region": r["region"],
                "hourly_cost": r["hourly_cost"],
                "daily_cost": r["daily_cost"],
                "cost_spike_pct": r["cost_spike_pct"],
                "cpu_avg": r["cpu_avg"],
                "network_in": r["network_in"],
                "network_out": r["network_out"],
                "tags": r["tags"],
                "last_deployment_days": r.get("last_deployment_days", 30),
                # Fields to be filled by later agents
                "classification": "",
                "risk_score": 0.0,
                "risk_label": "",
                "monthly_waste": 0.0,
                "rightsizing_savings": 0.0,
                "net_savings": 0.0,
            })

    msg = f"[Auditor] Found {len(anomalies)} resource(s) flagged for review."
    return {
        **state,
        "anomalies": anomalies,
        "current_step": "auditor_done",
        "messages": state["messages"] + [msg],
    }