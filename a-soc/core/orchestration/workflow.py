from typing import TypedDict, Annotated, Sequence, Union, List
from langgraph.graph import StateGraph, END
import operator
from ..base.message import ASOCMessage
from ...agents.telemetry.telemetry_agent import TelemetryAgent
from ...agents.detection.detection_agent import DetectionAgent
from ...agents.supervisor.supervisor_agent import SupervisorAgent
from ...agents.forensics.forensics_agent import ForensicsAgent
from ...agents.response.response_agent import ResponseAgent

class AgentState(TypedDict):
    # The state of our SOC workflow
    messages: Annotated[Sequence[ASOCMessage], operator.add]
    incident_id: str
    risk_score: float
    next_step: str
    is_authorized: bool

async def telemetry_node(state: AgentState):
    agent = TelemetryAgent()
    # In a real loop, this would be an entry point. Here we mock finding an event.
    return {"next_step": "detection"}

async def detection_node(state: AgentState):
    agent = DetectionAgent()
    latest_msg = state["messages"][-1] if state["messages"] else None
    # Processing...
    return {"risk_score": 0.85, "next_step": "supervisor"}

async def supervisor_node(state: AgentState):
    agent = SupervisorAgent()
    # Decision logic based on risk_score
    if state["risk_score"] > 0.8:
        return {"next_step": "forensics", "is_authorized": True}
    return {"next_step": "end"}

async def forensics_node(state: AgentState):
    agent = ForensicsAgent()
    # Detailed analysis...
    return {"next_step": "response"}

async def response_node(state: AgentState):
    agent = ResponseAgent()
    # Remediation...
    return {"next_step": "end"}

def create_asoc_graph():
    workflow = StateGraph(AgentState)

    # Add Nodes
    workflow.add_node("telemetry", telemetry_node)
    workflow.add_node("detection", detection_node)
    workflow.add_node("supervisor", supervisor_node)
    workflow.add_node("forensics", forensics_node)
    workflow.add_node("response", response_node)

    # Define Edges
    workflow.set_entry_point("telemetry")
    workflow.add_edge("telemetry", "detection")
    workflow.add_edge("detection", "supervisor")
    
    workflow.add_conditional_edges(
        "supervisor",
        lambda x: x["next_step"],
        {
            "forensics": "forensics",
            "end": END
        }
    )
    
    workflow.add_edge("forensics", "response")
    workflow.add_edge("response", END)

    return workflow.compile()
