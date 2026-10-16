from langchain_core.messages import SystemMessage
from app.core.llm import get_llm
from app.graph.state import WorkflowState


LOAN_AGENT_SYSTEM_PROMPT = """
You are the Loan Agent for an RWA investment platform.

Your responsibilities include:
- Answer questions about loans, borrowing, and collateral.
- You are currently under construction and do not have full capabilities.
- Be polite, professional, and concise.
- If the user asks about a topic outside your domain (e.g., staking, assets, payouts), you MUST call the transfer_to_supervisor tool immediately. Do NOT apologize. Do NOT say you cannot help. Just call the tool.
"""


async def loan_agent_node(
    state: WorkflowState,
) -> WorkflowState:

    from app.tools.transfer import transfer_to_supervisor

    llm = get_llm()
    llm_with_tools = llm.bind_tools([transfer_to_supervisor])

    messages = [
        SystemMessage(
            content=LOAN_AGENT_SYSTEM_PROMPT
        ),
        *state.get("messages", []),
    ]

    response = await llm_with_tools.ainvoke(messages)

    return {
        "messages": [response],
        "active_agent": "loan_agent",
        "status": "completed",
        "result": {
            "agent": "loan_agent",
            "message": "Loan agent reached successfully.",
        },
    }