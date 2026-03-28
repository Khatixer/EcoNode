from core.state import AgentState
from core.math_engine import calculate_zombie_savings


def telemetry_agent(state: AgentState) -> AgentState:
    """
    Agent 2: Resource Optimization
    Classifies each anomaly as ZOMBIE, UNDERUTILIZED, or HEALTHY.
    Calculates savings math for each.
    """
    enriched = []

    for r in state["anomalies"]:
        cpu = r["cpu_avg"]

        if cpu < 5.0:
            classification = "ZOMBIE"
        elif cpu < 30.0:
            classification = "UNDERUTILIZED"
        else:
            classification = "HEALTHY"

        savings = calculate_zombie_savings(
            r["resource_id"],
            r["resource_type"],
            r["hourly_cost"],
        )

        enriched.append({
            **r,
            "classification": classification,
            "monthly_waste": savings["monthly_waste"],
            "rightsizing_savings": savings["rightsizing_savings"],
            "net_savings": savings["net_savings"],
        })

    actionable_count = sum(1 for r in enriched if r["classification"] != "HEALTHY")
    msg = (
        f"[Telemetry] {actionable_count}/{len(enriched)} resource(s) classified as "
        f"ZOMBIE or UNDERUTILIZED."
    )

    return {
        **state,
        "anomalies": enriched,
        "current_step": "telemetry_done",
        "messages": state["messages"] + [msg],
    }