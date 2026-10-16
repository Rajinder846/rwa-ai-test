from langchain_core.messages import SystemMessage
from app.core.llm import get_llm
from app.graph.state import WorkflowState


PORTFOLIO_AGENT_SYSTEM_PROMPT = """
You are the Portfolio Agent for an RWA investment platform.

Your responsibilities include:
- Answer questions about the investor's past investments based on the conversation history.
- You currently do not have access to an external database, so you must rely entirely on the conversation history provided to you.
- If the user asks about an investment they made that is not in the recent conversation history, let them know you don't have access to that external database information yet.
- Be polite, professional, and concise.
- If the user asks about a topic outside your domain (e.g., loans, staking, assets), you MUST call the transfer_to_supervisor tool immediately. Do NOT apologize. Do NOT say you cannot help. Just call the tool.
"""


async def portfolio_agent_node(
    state: WorkflowState,
) -> WorkflowState:

    from app.tools.transfer import transfer_to_supervisor

    llm = get_llm()
    llm_with_tools = llm.bind_tools([transfer_to_supervisor])

    messages = [
        SystemMessage(
            content=PORTFOLIO_AGENT_SYSTEM_PROMPT
        ),
        *state.get("messages", []),
    ]
    print("LLM #2 call")
    response = await llm_with_tools.ainvoke(messages)

    return {
        "messages": [response],
        "active_agent": "portfolio_agent",
        "status": "completed",
        "result": {
            "agent": "portfolio_agent",
            "message": "Portfolio agent reached successfully.",
        },
    }