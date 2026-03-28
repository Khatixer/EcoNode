import os
import boto3
from datetime import datetime, timedelta
from typing import List, Dict, Any
from dotenv import load_dotenv

load_dotenv(override=True)

USE_MOCK = os.getenv("USE_MOCK", "False").lower() == "true"

print(f"[AWS] USE_MOCK = {USE_MOCK} (raw value: {repr(os.getenv('USE_MOCK'))})")

MOCK_INSTANCES = [
    {
        "resource_id": "i-0994c72aef3b1d2e8",
        "resource_type": "p3.2xlarge",
        "service": "EC2",
        "region": "us-east-1",
        "hourly_cost": 3.06,
        "daily_cost": 73.44,
        "cost_spike_pct": 0.0,
        "cpu_avg": 0.4,
        "network_in": 2.1,
        "network_out": 1.8,
        "tags": {"Environment": "dev", "Team": "ml-research", "Owner": "john.doe"},
        "last_deployment_days": 45,
    },
]


def get_boto3_client(service: str):
    access_key = os.getenv("AWS_ACCESS_KEY_ID")
    secret_key = os.getenv("AWS_SECRET_ACCESS_KEY")
    region = os.getenv("AWS_DEFAULT_REGION", os.getenv("AWS_REGION", "us-east-1"))

    if os.environ.get("LAMBDA_TASK_ROOT"):
        return boto3.client(service, region_name=region)

    if access_key and secret_key:
        return boto3.client(
            service,
            region_name=region,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
        )
    return boto3.client(service, region_name=region)


def get_ec2_instances() -> List[Dict[str, Any]]:
    if USE_MOCK:
        print("[AWS] USE_MOCK is True, returning mock data.")
        return MOCK_INSTANCES

    print("[AWS] USE_MOCK is False, calling real AWS...")

    try:
        ec2 = get_boto3_client("ec2")
        cw = get_boto3_client("cloudwatch")

        response = ec2.describe_instances(
            Filters=[{"Name": "instance-state-name", "Values": ["running"]}]
        )

        instances = []
        for reservation in response.get("Reservations", []):
            for inst in reservation.get("Instances", []):
                instance_id = inst["InstanceId"]
                itype = inst.get("InstanceType", "t2.micro")

                end = datetime.utcnow()
                start = end - timedelta(hours=24)

                cpu_resp = cw.get_metric_statistics(
                    Namespace="AWS/EC2",
                    MetricName="CPUUtilization",
                    Dimensions=[{"Name": "InstanceId", "Value": instance_id}],
                    StartTime=start,
                    EndTime=end,
                    Period=86400,
                    Statistics=["Average"],
                )
                datapoints = cpu_resp.get("Datapoints", [])
                cpu_avg = datapoints[0]["Average"] if datapoints else 0.0

                net_in_resp = cw.get_metric_statistics(
                    Namespace="AWS/EC2",
                    MetricName="NetworkIn",
                    Dimensions=[{"Name": "InstanceId", "Value": instance_id}],
                    StartTime=start,
                    EndTime=end,
                    Period=86400,
                    Statistics=["Sum"],
                )
                net_datapoints = net_in_resp.get("Datapoints", [])
                network_in_mb = (
                    net_datapoints[0]["Sum"] / (1024 * 1024)
                    if net_datapoints else 0.0
                )

                tags = {t["Key"]: t["Value"] for t in inst.get("Tags", [])}

                from core.math_engine import INSTANCE_RATES
                hourly = INSTANCE_RATES.get(itype, 0.05)

                launch_time = inst.get("LaunchTime")
                last_deployment_days = (
                    (datetime.utcnow() - launch_time.replace(tzinfo=None)).days
                    if launch_time else 30
                )

                instances.append({
                    "resource_id": instance_id,
                    "resource_type": itype,
                    "service": "EC2",
                    "region": inst.get("Placement", {}).get("AvailabilityZone", "us-east-1"),
                    "hourly_cost": hourly,
                    "daily_cost": round(hourly * 24, 4),
                    "cost_spike_pct": 0.0,
                    "cpu_avg": round(cpu_avg, 2),
                    "network_in": round(network_in_mb, 2),
                    "network_out": 0.0,
                    "tags": tags,
                    "last_deployment_days": last_deployment_days,
                })

        print(f"[AWS] Found {len(instances)} running instance(s).")
        return instances if instances else MOCK_INSTANCES

    except Exception as e:
        print(f"[AWS] Real call failed: {e}")
        return MOCK_INSTANCES