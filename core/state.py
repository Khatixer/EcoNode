from typing import TypedDict, List, Optional, Dict, Any

class ResourceAnomaly(TypedDict):
    resource_id: str
    resource_type: str
    service: str
    region: str
    hourly_cost: float
    daily_cost: float
    cost_spike_pct: float
    cpu_avg: float
    network_in: float
    network_out: float
    classification: str        # ZOMBIE | UNDERUTILIZED | HEALTHY
    tags: Dict[str, str]
    risk_score: float          # 0.0 to 1.0
    risk_label: str            # SAFE_TO_ACT | ESCALATE_ONLY | BLOCKED
    monthly_waste: float
    rightsizing_savings: float
    net_savings: float

class AgentState(TypedDict):
    # Pipeline data
    anomalies: List[ResourceAnomaly]
    actionable: List[ResourceAnomaly]
    blocked: List[ResourceAnomaly]

    # Math outputs
    total_monthly_savings: float
    manual_finops_cost: float
    econode_runtime_cost: float
    roi_multiplier: float

    # Workflow state
    current_step: str
    approval_status: str       # PENDING | APPROVED | DENIED
    action_executed: bool
    audit_log_id: Optional[str]

    # Messages between agents
    messages: List[str]
    playbook_path: Optional[str]