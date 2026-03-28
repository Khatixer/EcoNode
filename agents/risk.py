from core.state import AgentState
from core.math_engine import calculate_risk_score


def risk_agent(state: AgentState) -> AgentState:
    """
    Agent 3: SLA Prevention
    Scores each resource's risk using the 3-factor formula.
    Splits into actionable vs blocked lists.
    """
    scored = []

    for r in state["anomalies"]:
        if r["classification"] == "HEALTHY":
            scored.append({**r, "risk_score": 0.0, "risk_label": "HEALTHY_SKIP"})
            continue

        result = calculate_risk_score(
            tags=r["tags"],
            last_deployment_days=r.get("last_deployment_days", 30),
            network_in_mb=r["network_in"],
        )

        scored.append({
            **r,
            "risk_score": result["risk_score"],
            "risk_label": result["risk_label"],
        })

    actionable = [r for r in scored if r["risk_label"] == "SAFE_TO_ACT"]
    blocked = [r for r in scored if r["risk_label"] in ("BLOCKED", "ESCALATE_ONLY")]

    msg = (
        f"[Risk] {len(actionable)} resource(s) SAFE_TO_ACT, "
        f"{len(blocked)} BLOCKED or ESCALATE_ONLY."
    )

    return {
        **state,
        "anomalies": scored,
        "actionable": actionable,
        "blocked": blocked,
        "current_step": "risk_done",
        "messages": state["messages"] + [msg],
    }