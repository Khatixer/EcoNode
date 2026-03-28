from langgraph.graph import StateGraph, END
from core.state import AgentState
from agents.auditor import auditor_agent
from agents.telemetry import telemetry_agent
from agents.risk import risk_agent
from agents.supervisor import supervisor_agent


def build_graph() -> StateGraph:
    workflow = StateGraph(AgentState)

    # Register all 4 agent nodes
    workflow.add_node("auditor", auditor_agent)
    workflow.add_node("telemetry", telemetry_agent)
    workflow.add_node("risk", risk_agent)
    workflow.add_node("supervisor", supervisor_agent)

    # Define the pipeline sequence
    workflow.set_entry_point("auditor")
    workflow.add_edge("auditor", "telemetry")
    workflow.add_edge("telemetry", "risk")
    workflow.add_edge("risk", "supervisor")
    workflow.add_edge("supervisor", END)

    return workflow.compile()