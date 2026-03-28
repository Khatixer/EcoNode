import time
import os
from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.text import Text
from rich import box
from rich.rule import Rule

from core.graph import build_graph
from core.state import AgentState
from output.playbook import generate_playbook
from integrations.audit_db import get_all_logs, update_approval

load_dotenv()
console = Console()


def print_banner():
    console.print()
    console.print(Panel.fit(
        "[bold cyan]⚡ EcoNode[/bold cyan] [white]Autonomous Cloud FinOps Engine[/white]\n"
        "[dim]Multi-Agent Cost Optimization | Human-in-the-Loop | Audit Trail[/dim]",
        border_style="cyan",
        padding=(1, 4),
    ))
    console.print()


def print_agent_step(agent: str, message: str, status: str = "running"):
    icons = {"running": "🔄", "done": "✅", "warn": "⚠️", "block": "🔴"}
    color = {"running": "yellow", "done": "green", "warn": "yellow", "block": "red"}
    icon = icons.get(status, "🔄")
    c = color.get(status, "white")
    console.print(f"  {icon} [{c}]{agent}[/{c}]  {message}")


def print_resources_table(state: AgentState):
    table = Table(
        title="📊 Resource Analysis",
        box=box.ROUNDED,
        border_style="blue",
        show_lines=True,
    )
    table.add_column("Resource ID", style="cyan", no_wrap=True)
    table.add_column("Type", style="white")
    table.add_column("CPU%", justify="right")
    table.add_column("Class", justify="center")
    table.add_column("Risk", justify="center")
    table.add_column("Monthly Waste", justify="right", style="red")
    table.add_column("Net Savings", justify="right", style="green")
    table.add_column("Action")

    for r in state.get("anomalies", []):
        cls_color = {
            "ZOMBIE": "red", "UNDERUTILIZED": "yellow", "HEALTHY": "green"
        }.get(r["classification"], "white")

        risk_color = {
            "SAFE_TO_ACT": "green", "ESCALATE_ONLY": "yellow",
            "BLOCKED": "red", "HEALTHY_SKIP": "dim"
        }.get(r["risk_label"], "white")

        action = (
            "Terminate" if r["classification"] == "ZOMBIE"
            else "Rightsize" if r["classification"] == "UNDERUTILIZED"
            else "—"
        )

        table.add_row(
            r["resource_id"][:22],
            r["resource_type"],
            f"{r['cpu_avg']}%",
            f"[{cls_color}]{r['classification']}[/{cls_color}]",
            f"[{risk_color}]{r['risk_label']}[/{risk_color}]",
            f"${r['monthly_waste']:,.2f}",
            f"${r['net_savings']:,.2f}",
            action,
        )

    console.print()
    console.print(table)


def print_savings_summary(state: AgentState):
    total = state.get("total_monthly_savings", 0)
    roi = state.get("roi_multiplier", 0)
    manual = state.get("manual_finops_cost", 3400)

    console.print()
    console.print(Rule("[bold green]💰 Cost-Savings Playbook Summary[/bold green]"))

    grid = Table.grid(expand=True, padding=(0, 4))
    grid.add_column(justify="left")
    grid.add_column(justify="left")

    grid.add_row(
        "[bold]Monthly Savings Identified:[/bold]",
        f"[bold green]${total:,.2f}[/bold green]"
    )
    grid.add_row(
        "[bold]Annualized Savings:[/bold]",
        f"[bold green]${total * 12:,.2f}[/bold green]"
    )
    grid.add_row(
        "[bold]Manual FinOps Replaced:[/bold]",
        f"[yellow]${manual:,}/month (40hrs × $85/hr)[/yellow]"
    )
    grid.add_row(
        "[bold]EcoNode Runtime Cost:[/bold]",
        "[dim]$0.80/month[/dim]"
    )
    grid.add_row(
        "[bold]ROI Multiplier:[/bold]",
        f"[bold cyan]{roi:,.0f}x[/bold cyan]"
    )
    grid.add_row(
        "[bold]Audit Log ID:[/bold]",
        f"[dim]{state.get('audit_log_id', 'N/A')}[/dim]"
    )

    console.print(Panel(grid, border_style="green", padding=(1, 2)))


def print_audit_trail():
    logs = get_all_logs()
    if not logs:
        return

    table = Table(title="🗂️  Audit Trail", box=box.SIMPLE_HEAD, border_style="dim")
    table.add_column("ID", style="cyan")
    table.add_column("Timestamp")
    table.add_column("Resource")
    table.add_column("Action")
    table.add_column("Risk")
    table.add_column("Savings", justify="right")
    table.add_column("Status")
    table.add_column("Executed", justify="center")

    for row in logs:
        log_id, ts, res_id, res_type, action, risk_score, risk_label, savings, status, approved_by, executed, _ = row
        status_color = {"PENDING": "yellow", "APPROVED": "green", "DENIED": "red"}.get(status, "white")
        table.add_row(
            log_id,
            ts[:19],
            res_id[:18],
            action[:30],
            f"{risk_score:.2f}",
            f"${savings:,.2f}",
            f"[{status_color}]{status}[/{status_color}]",
            "✅" if executed else "⏳",
        )

    console.print()
    console.print(table)



def main():
    print_banner()

    console.print("[bold]Starting EcoNode pipeline...[/bold]")
    console.print()

    # Initial state
    initial_state: AgentState = {
        "anomalies": [],
        "actionable": [],
        "blocked": [],
        "total_monthly_savings": 0.0,
        "manual_finops_cost": 0.0,
        "econode_runtime_cost": 0.0,
        "roi_multiplier": 0.0,
        "current_step": "start",
        "approval_status": "PENDING",
        "action_executed": False,
        "audit_log_id": None,
        "messages": [],
        "playbook_path": None,
    }

    app = build_graph()
    final_state = None

    agent_names = {
        "auditor": "Auditor Agent     (Spend Intelligence)",
        "telemetry": "Telemetry Agent   (Resource Optimization)",
        "risk": "Risk Agent        (SLA Prevention)",
        "supervisor": "Supervisor Agent  (FinOps Brain)",
    }

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        transient=True,
        console=console,
    ) as progress:

        for output in app.stream(initial_state):
            for node_name, node_state in output.items():
                final_state = node_state
                label = agent_names.get(node_name, node_name)
                task = progress.add_task(f"  Running {label}...", total=None)
                time.sleep(0.8)  # visual pause for demo effect
                progress.remove_task(task)

                # Print messages from this agent
                msgs = node_state.get("messages", [])
                if msgs:
                    print_agent_step(label, msgs[-1], "done")

    console.print()
    console.print(Rule("[bold blue]Pipeline Complete[/bold blue]"))

    if final_state:
        print_resources_table(final_state)
        print_savings_summary(final_state)

        # Generate PDF playbook
        console.print()
        with console.status("[bold]Generating PDF Cost-Savings Playbook...[/bold]"):
            playbook_path = generate_playbook(final_state)
            time.sleep(1)

        console.print(f"  [green]✅ Playbook saved:[/green] [cyan]{playbook_path}[/cyan]")

        console.print()
        console.print(Panel(
            f"[bold yellow]⚡ Slack approval sent[/bold yellow]\n\n"
            f"EcoNode identified [bold green]${final_state.get('total_monthly_savings', 0):,.2f}/month[/bold green] "
            f"in savings.\n"
            f"[cyan]{len(final_state.get('actionable', []))}[/cyan] Slack message(s) sent — "
            f"one per resource.\n\n"
            f"Reply in Slack with:\n"
            f"  [green]econode approve <LOG_ID>[/green] — to execute\n"
            f"  [red]econode deny <LOG_ID>[/red] — to skip\n\n"
            f"[dim]Slack listener must be running to process replies.[/dim]",
            border_style="yellow",
            padding=(1, 3),
        ))

        # Show audit trail
        print_audit_trail()

    console.print()
    console.print(Rule())
    console.print("[bold green]EcoNode run complete.[/bold green]")
    console.print()


if __name__ == "__main__":
    main()