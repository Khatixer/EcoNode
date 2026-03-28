# ⚡ EcoNode — Autonomous Cloud FinOps Engine

> A 4-agent AI system that finds AWS waste, scores SLA risk, and executes 
> approved optimizations — with full human approval workflows and audit trail.

---

## What It Does

EcoNode runs a multi-agent pipeline that:
1. **Audits** AWS Cost Explorer and CloudWatch for idle/anomalous resources
2. **Classifies** each resource as ZOMBIE, UNDERUTILIZED, or HEALTHY
3. **Scores** SLA risk using a 3-factor weighted formula before any action
4. **Sends** individual Slack notifications per resource requiring approval
5. **Executes** terminations only after explicit human approval
6. **Logs** every action to a persistent audit trail

---

## The Math

**Formula 1 — Zombie Savings:**
```
Monthly Waste = Hourly Rate × 24hrs × 30days
Net Savings   = Monthly Waste − Rightsizing Alternative
```

**Formula 2 — SLA Risk Score:**
```
Risk = (Production Tag × 0.6) + (Deploy Recency × 0.3) + (Network Traffic × 0.1)
> 0.7  → BLOCKED
> 0.3  → ESCALATE_ONLY  
≤ 0.3  → SAFE_TO_ACT
```

**Formula 3 — EcoNode ROI:**
```
ROI = (Manual FinOps Cost + Savings) ÷ EcoNode Runtime
    = ($3,400 + savings) ÷ $0.80
    = 4,000x+
```

---

## Architecture
```
EventBridge (9am daily)
        ↓
   Lambda Function
        ↓
┌─────────────────────────────────────┐
│         LangGraph Pipeline          │
│                                     │
│  Agent 1: Auditor                   │
│  → AWS Cost Explorer + CloudWatch   │
│         ↓                           │
│  Agent 2: Telemetry                 │
│  → CPU classification + savings     │
│         ↓                           │
│  Agent 3: Risk                      │
│  → SLA risk scoring + blocking      │
│         ↓                           │
│  Agent 4: Supervisor                │
│  → PDF playbook + Slack + Audit DB  │
└─────────────────────────────────────┘
        ↓
   Slack Notification
        ↓
   Human types: econode approve <ID>
        ↓
   Flask Listener receives reply
        ↓
   EC2 instance terminated
        ↓
   Audit trail updated
```

---

## Tech Stack

| Layer | Tool |
|---|---|
| Agent Framework | LangGraph |
| LLM | Claude (Anthropic) |
| AWS Data | Boto3 — Cost Explorer, CloudWatch, EC2 |
| Human Approval | Slack Webhooks + Flask listener |
| Scheduling | AWS EventBridge + Lambda |
| Audit Trail | SQLite |
| PDF Reports | ReportLab |
| Terminal UI | Rich |

---

## Setup Instructions

### 1. Clone and install
```bash
git clone https://github.com/YOURUSERNAME/econode.git
cd econode
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Environment variables

Create a `.env` file in the root:
```env
# Anthropic
ANTHROPIC_API_KEY=your_key_here

# AWS
AWS_ACCESS_KEY_ID=your_key_here
AWS_SECRET_ACCESS_KEY=your_secret_here
AWS_REGION=us-east-1

# Slack
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/...
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL=#your-channel

# Flags
USE_MOCK=True    # Set False for real AWS data
DRY_RUN=True     # Set False for real terminations
```

### 3. Run locally
```bash
# Terminal 1 — start Slack listener
python slack_listener.py

# Terminal 2 — start ngrok
ngrok http 3000

# Terminal 3 — run pipeline
python main.py
```

### 4. Approve from Slack
```
econode approve <LOG_ID>   # terminate the resource
econode deny <LOG_ID>      # skip, log as denied
econode status             # show recent audit log
```

### 5. Deploy to AWS Lambda
```bash
python package_lambda.py
# Upload econode_lambda.zip to S3
# Deploy to Lambda function
# Add EventBridge trigger: cron(0 9 * * ? *)
```

---

## Project Structure
```
econode/
├── agents/
│   ├── auditor.py        # Agent 1: Spend intelligence
│   ├── telemetry.py      # Agent 2: Resource classification
│   ├── risk.py           # Agent 3: SLA risk scoring
│   └── supervisor.py     # Agent 4: FinOps brain
├── core/
│   ├── state.py          # Shared AgentState TypedDict
│   ├── graph.py          # LangGraph pipeline
│   └── math_engine.py    # All savings formulas
├── integrations/
│   ├── aws_client.py     # Boto3 wrapper
│   ├── slack_bot.py      # Outbound Slack notifications
│   ├── slack_listener.py # Inbound approval handler
│   └── audit_db.py       # SQLite audit trail
├── output/
│   └── playbook.py       # PDF report generator
├── main.py               # Terminal UI entry point
├── lambda_handler.py     # AWS Lambda entry point
├── package_lambda.py     # Lambda packaging script
└── requirements.txt
```

---

## Impact Model

| Metric | Monthly | Annual |
|---|---|---|
| Cloud waste eliminated | $2,700 | $32,400 |
| Engineer time recovered | $3,398 | $40,776 |
| SLA incident prevention | $1,867 | $22,400 |
| **Total value** | **$7,965** | **$95,576** |
| EcoNode cost | $0.80 | $9.60 |
| **ROI** | **9,956x** | **9,956x** |

---
