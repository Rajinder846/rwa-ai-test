from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

from app.agents.supervisor import supervisor_node
from app.graph.nodes.execute_investment_node import execute_investment_node
from app.graph.nodes.investment_node import investment_workflow
from app.graph.router import route_after_investment, route_after_supervisor
from app.graph.state import WorkflowState
from app.workflows import asset_workflow, clarification_node, loan_workflow, payout_workflow, portfolio_workflow, reasoning_agent, response_formatter, staking_workflow


def build_graph():
    builder = StateGraph(WorkflowState)
    for name, node in {"supervisor": supervisor_node, "asset_workflow": asset_workflow, "investment_workflow": investment_workflow, "portfolio_workflow": portfolio_workflow, "payout_workflow": payout_workflow, "loan_workflow": loan_workflow, "staking_workflow": staking_workflow, "reasoning_agent": reasoning_agent, "clarification": clarification_node, "execute_investment": execute_investment_node, "response_formatter": response_formatter}.items():
        builder.add_node(name, node)
    builder.add_edge(START, "supervisor")
    builder.add_conditional_edges("supervisor", route_after_supervisor, {name: name for name in ("asset_workflow", "investment_workflow", "portfolio_workflow", "payout_workflow", "loan_workflow", "staking_workflow", "reasoning_agent", "clarification")})
    builder.add_conditional_edges("investment_workflow", route_after_investment, {"execute_investment": "execute_investment", "response_formatter": "response_formatter"})
    for name in ("asset_workflow", "portfolio_workflow", "payout_workflow", "loan_workflow", "staking_workflow", "reasoning_agent", "clarification", "execute_investment"):
        builder.add_edge(name, "response_formatter")
    builder.add_edge("response_formatter", END)
    return builder.compile(checkpointer=MemorySaver())


graph = build_graph()
