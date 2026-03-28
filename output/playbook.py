import os
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
)
from core.state import AgentState


def generate_playbook(state: AgentState) -> str:
    """Generates a PDF Cost-Savings Playbook. Returns the file path."""
    os.makedirs("output/reports", exist_ok=True)
    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    path = f"output/reports/econode_playbook_{ts}.pdf"

    doc = SimpleDocTemplate(path, pagesize=A4,
                            leftMargin=2*cm, rightMargin=2*cm,
                            topMargin=2*cm, bottomMargin=2*cm)
    styles = getSampleStyleSheet()

    # Custom styles
    title_style = ParagraphStyle("Title", parent=styles["Title"],
                                 fontSize=22, textColor=colors.HexColor("#1a1a2e"),
                                 spaceAfter=6)
    heading_style = ParagraphStyle("Heading", parent=styles["Heading2"],
                                   fontSize=13, textColor=colors.HexColor("#16213e"),
                                   spaceBefore=14, spaceAfter=6)
    body_style = ParagraphStyle("Body", parent=styles["Normal"],
                                fontSize=10, leading=16)
    green_style = ParagraphStyle("Green", parent=body_style,
                                 textColor=colors.HexColor("#2d6a4f"), fontSize=12)
    red_style = ParagraphStyle("Red", parent=body_style,
                               textColor=colors.HexColor("#c1121f"), fontSize=11)

    story = []

    # Header
    story.append(Paragraph("⚡ EcoNode Cost-Savings Playbook", title_style))
    story.append(Paragraph(
        f"Generated: {datetime.utcnow().strftime('%B %d, %Y at %H:%M UTC')} &nbsp;|&nbsp; "
        f"Audit Trail Active &nbsp;|&nbsp; Human Approval Required",
        body_style
    ))
    story.append(HRFlowable(width="100%", thickness=2, color=colors.HexColor("#457b9d")))
    story.append(Spacer(1, 0.4*cm))

    # Executive Summary
    story.append(Paragraph("Executive Summary", heading_style))
    total = state.get("total_monthly_savings", 0)
    roi = state.get("roi_multiplier", 0)
    manual = state.get("manual_finops_cost", 3400)
    actionable_count = len(state.get("actionable", []))
    blocked_count = len(state.get("blocked", []))

    summary_data = [
        ["Metric", "Value"],
        ["Total Monthly Savings Identified", f"${total:,.2f}"],
        ["Annualized Savings", f"${total * 12:,.2f}"],
        ["Actionable Resources", str(actionable_count)],
        ["Blocked (SLA Protected)", str(blocked_count)],
        ["Manual FinOps Cost (replaced)", f"${manual:,}/month"],
        ["EcoNode Runtime Cost", "$0.80/month"],
        ["ROI Multiplier", f"{roi:,.0f}x"],
    ]

    summary_table = Table(summary_data, colWidths=[10*cm, 6*cm])
    summary_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1a1a2e")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.HexColor("#f8f9fa"), colors.white]),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#dee2e6")),
        ("PADDING", (0, 0), (-1, -1), 8),
        ("FONTNAME", (0, 1), (0, -1), "Helvetica-Bold"),
    ]))
    story.append(summary_table)
    story.append(Spacer(1, 0.5*cm))

    # Savings Math
    story.append(Paragraph("The Math — How Savings Are Calculated", heading_style))
    story.append(Paragraph(
        "<b>Formula 1 — Zombie Instance Savings:</b><br/>"
        "Monthly Waste = Hourly Rate × 24hrs × 30days<br/>"
        "Rightsizing Alt = Next-tier hourly rate × 24 × 30<br/>"
        "Net Savings = Monthly Waste − Rightsizing Alternative",
        body_style
    ))
    story.append(Spacer(1, 0.2*cm))
    story.append(Paragraph(
        "<b>Formula 2 — SLA Risk Score:</b><br/>"
        "Risk = (Production Tag Weight × 0.6) + (Deploy Recency × 0.3) + (Network Traffic × 0.1)<br/>"
        "BLOCKED if Risk &gt; 0.7 | ESCALATE if 0.3–0.7 | SAFE_TO_ACT if &lt; 0.3",
        body_style
    ))
    story.append(Spacer(1, 0.2*cm))
    story.append(Paragraph(
        f"<b>Formula 3 — EcoNode ROI:</b><br/>"
        f"Manual FinOps = 40hrs × $85/hr = $3,400/month<br/>"
        f"EcoNode Runtime = $0.80/month<br/>"
        f"ROI = ($3,400 + ${total:,.2f}) ÷ $0.80 = <b>{roi:,.0f}x</b>",
        green_style
    ))
    story.append(Spacer(1, 0.5*cm))

    # Actionable Resources
    if state.get("actionable"):
        story.append(Paragraph("✅ Actionable Resources (Awaiting Approval)", heading_style))
        headers = ["Resource ID", "Type", "CPU%", "Risk", "Monthly Waste", "Net Savings", "Action"]
        rows = [headers]
        for r in state["actionable"]:
            action = "Terminate" if r["classification"] == "ZOMBIE" else "Rightsize"
            rows.append([
                r["resource_id"][:20],
                r["resource_type"],
                f"{r['cpu_avg']}%",
                f"{r['risk_score']} ({r['risk_label']})",
                f"${r['monthly_waste']:,.2f}",
                f"${r['net_savings']:,.2f}",
                action,
            ])

        t = Table(rows, colWidths=[4.5*cm, 2.5*cm, 1.5*cm, 3.5*cm, 2.5*cm, 2.5*cm, 2*cm])
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2d6a4f")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.HexColor("#d8f3dc"), colors.white]),
            ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#b7e4c7")),
            ("PADDING", (0, 0), (-1, -1), 6),
        ]))
        story.append(t)
        story.append(Spacer(1, 0.5*cm))

    # Blocked Resources
    if state.get("blocked"):
        story.append(Paragraph("🔴 Blocked Resources (SLA Protected)", heading_style))
        story.append(Paragraph(
            "These resources were identified as wasteful but are protected by SLA risk scoring. "
            "No automated action will be taken. Manual review recommended.",
            red_style
        ))
        story.append(Spacer(1, 0.2*cm))
        b_headers = ["Resource ID", "Type", "Risk Score", "Risk Label", "Monthly Waste"]
        b_rows = [b_headers]
        for r in state["blocked"]:
            b_rows.append([
                r["resource_id"][:20],
                r["resource_type"],
                str(r["risk_score"]),
                r["risk_label"],
                f"${r['monthly_waste']:,.2f}",
            ])
        bt = Table(b_rows, colWidths=[5*cm, 3*cm, 2.5*cm, 3.5*cm, 3*cm])
        bt.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#c1121f")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.HexColor("#ffe8e8"), colors.white]),
            ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#ffb3b3")),
            ("PADDING", (0, 0), (-1, -1), 6),
        ]))
        story.append(bt)

    story.append(Spacer(1, 0.8*cm))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#adb5bd")))
    story.append(Paragraph(
        "EcoNode Autonomous FinOps Engine | All actions require human approval | "
        f"Audit Log ID: {state.get('audit_log_id', 'N/A')}",
        ParagraphStyle("Footer", parent=body_style, fontSize=8,
                       textColor=colors.HexColor("#6c757d"))
    ))

    doc.build(story)
    return path