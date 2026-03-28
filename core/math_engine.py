from typing import Dict, Any

# Hourly rates for common instance types (USD)
INSTANCE_RATES = {
    "p3.2xlarge": 3.06,
    "p3.8xlarge": 12.24,
    "g4dn.xlarge": 0.526,
    "m5.4xlarge": 0.768,
    "m5.2xlarge": 0.384,
    "m5.xlarge": 0.192,
    "m5.large": 0.096,
    "t3.large": 0.0832,
    "t3.medium": 0.0416,
    "t3.small": 0.0208,
    "t2.micro": 0.0116,
    "t2.small": 0.023,
    "t2.medium": 0.0464,
    "c5.2xlarge": 0.34,
    "c5.xlarge": 0.17,
    "r5.2xlarge": 0.504,
}

# Rightsizing map: what to downsize to
RIGHTSIZE_MAP = {
    "p3.2xlarge": "p3.xlarge",
    "m5.4xlarge": "m5.2xlarge",
    "m5.2xlarge": "m5.xlarge",
    "m5.xlarge": "m5.large",
    "t3.large": "t3.medium",
    "t3.medium": "t3.small",
    "c5.2xlarge": "c5.xlarge",
    "r5.2xlarge": "r5.xlarge",
}

RIGHTSIZE_RATES = {
    "p3.xlarge": 1.53,
    "m5.2xlarge": 0.384,
    "m5.xlarge": 0.192,
    "m5.large": 0.096,
    "t3.medium": 0.0416,
    "t3.small": 0.0208,
    "c5.xlarge": 0.17,
    "r5.xlarge": 0.252,
}


def calculate_zombie_savings(resource_id: str, instance_type: str, hourly_cost: float) -> Dict[str, float]:
    """
    Formula 1: Zombie Instance Savings
    Monthly Waste     = Hourly Rate × 24 × 30
    Rightsizing Alt   = Next-tier hourly rate × 24 × 30
    Net Savings       = Monthly Waste - Rightsizing Alt
    (If no rightsize option exists, full termination saving applies)
    """
    monthly_waste = hourly_cost * 24 * 30

    rightsize_type = RIGHTSIZE_MAP.get(instance_type)
    if rightsize_type:
        rightsize_hourly = RIGHTSIZE_RATES.get(rightsize_type, hourly_cost * 0.5)
        rightsizing_savings = (hourly_cost - rightsize_hourly) * 24 * 30
        recommendation = f"Rightsize to {rightsize_type}"
    else:
        rightsizing_savings = monthly_waste
        recommendation = "Terminate (no smaller tier available)"

    net_savings = rightsizing_savings

    return {
        "monthly_waste": round(monthly_waste, 2),
        "rightsizing_savings": round(rightsizing_savings, 2),
        "net_savings": round(net_savings, 2),
        "recommendation": recommendation,
    }


def calculate_risk_score(tags: Dict[str, str], last_deployment_days: int, network_in_mb: float) -> Dict[str, Any]:
    """
    Formula 2: SLA Risk Score
    Risk = (Production Tag Weight × 0.6)
          + (Deployment Recency Score × 0.3)
          + (Network Traffic Score × 0.1)

    Risk > 0.7  → BLOCKED
    Risk 0.3–0.7 → ESCALATE_ONLY
    Risk < 0.3  → SAFE_TO_ACT
    """
    # Production tag weight
    env_tag = tags.get("Environment", tags.get("env", tags.get("Env", ""))).lower()
    if env_tag in ["production", "prod"]:
        prod_weight = 1.0
    elif env_tag in ["staging", "stage"]:
        prod_weight = 0.5
    else:
        prod_weight = 0.0

    # Deployment recency score (more recent = higher risk)
    if last_deployment_days <= 1:
        deploy_score = 1.0
    elif last_deployment_days <= 7:
        deploy_score = 0.6
    elif last_deployment_days <= 30:
        deploy_score = 0.3
    else:
        deploy_score = 0.0

    # Network traffic score (high traffic = higher risk)
    if network_in_mb > 1000:
        traffic_score = 1.0
    elif network_in_mb > 100:
        traffic_score = 0.5
    elif network_in_mb > 10:
        traffic_score = 0.2
    else:
        traffic_score = 0.0

    risk_score = (prod_weight * 0.6) + (deploy_score * 0.3) + (traffic_score * 0.1)
    risk_score = round(risk_score, 3)

    if risk_score > 0.7:
        risk_label = "BLOCKED"
    elif risk_score > 0.3:
        risk_label = "ESCALATE_ONLY"
    else:
        risk_label = "SAFE_TO_ACT"

    return {
        "risk_score": risk_score,
        "risk_label": risk_label,
        "breakdown": {
            "production_weight": round(prod_weight * 0.6, 3),
            "deployment_recency": round(deploy_score * 0.3, 3),
            "network_traffic": round(traffic_score * 0.1, 3),
        }
    }


def calculate_econode_roi(total_monthly_savings: float) -> Dict[str, float]:
    """
    Formula 3: ROI of EcoNode
    Manual FinOps Cost  = 40 hrs/month × $85/hr
    EcoNode Runtime     = ~$0.80/month (API + compute)
    ROI Multiplier      = (Manual Cost + Savings) / Runtime Cost
    """
    manual_finops_cost = 40 * 85        # $3,400
    econode_runtime = 0.80
    roi = (manual_finops_cost + total_monthly_savings) / econode_runtime

    return {
        "manual_finops_cost": manual_finops_cost,
        "econode_runtime_cost": econode_runtime,
        "roi_multiplier": round(roi, 1),
        "net_value_delivered": round(manual_finops_cost + total_monthly_savings - econode_runtime, 2),
    }