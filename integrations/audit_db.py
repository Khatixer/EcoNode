import os
import sqlite3
import uuid
import json
from datetime import datetime
# This ensures it works on both your local machine and Lambda
DB_PATH = os.path.join("/tmp", "audit.db") if os.environ.get("LAMBDA_TASK_ROOT") else "audit.db"


def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS audit_log (
            id TEXT PRIMARY KEY,
            timestamp TEXT NOT NULL,
            resource_id TEXT NOT NULL,
            resource_type TEXT NOT NULL,
            action TEXT NOT NULL,
            risk_score REAL,
            risk_label TEXT,
            monthly_savings REAL,
            approval_status TEXT,
            approved_by TEXT,
            executed INTEGER DEFAULT 0,
            metadata TEXT
        )
    """)
    conn.commit()
    conn.close()


def log_action(
    resource_id: str,
    resource_type: str,
    action: str,
    risk_score: float,
    risk_label: str,
    monthly_savings: float,
    approval_status: str = "PENDING",
    approved_by: str = "system",
    executed: bool = False,
    metadata: dict = None,
) -> str:
    init_db()
    log_id = str(uuid.uuid4())[:8].upper()
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        INSERT INTO audit_log VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
    """, (
        log_id,
        datetime.utcnow().isoformat(),
        resource_id,
        resource_type,
        action,
        risk_score,
        risk_label,
        monthly_savings,
        approval_status,
        approved_by,
        int(executed),
        json.dumps(metadata or {}),
    ))
    conn.commit()
    conn.close()
    return log_id


def update_approval(
    log_id: str,
    status: str,
    approved_by: str = "human",
    executed: bool = True
):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        UPDATE audit_log
        SET approval_status=?, approved_by=?, executed=?
        WHERE id=?
    """, (status, approved_by, int(executed), log_id))
    conn.commit()
    conn.close()


def get_all_logs():
    init_db()
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT * FROM audit_log ORDER BY timestamp DESC")
    rows = c.fetchall()
    conn.close()
    return rows


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


def execute_termination(
    resource_id: str,
    resource_type: str,
    dry_run: bool = True
) -> str:
    """
    Executes the approved action on AWS.
    dry_run=True  → logs what WOULD happen, no real action.
    dry_run=False → real termination.
    """
    if dry_run:
        return f"[DRY RUN] Would terminate {resource_id} ({resource_type}). No real action taken."

    try:
        ec2 = get_boto3_client("ec2")
        if "vol-" in resource_id or "EBS" in resource_type:
            ec2.delete_volume(VolumeId=resource_id)
            return f"EBS volume `{resource_id}` deleted."
        else:
            ec2.terminate_instances(InstanceIds=[resource_id])
            return f"EC2 instance `{resource_id}` terminated."
    except Exception as e:
        return f"Termination failed for {resource_id}: {e}"