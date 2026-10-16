from langchain_core.tools import tool

@tool
def transfer_to_supervisor() -> str:
    """
    Transfer the conversation to the supervisor.
    Call this tool when the user asks about a topic outside of your domain (e.g., if you are the staking agent and the user asks about loans).
    """
    return "Transferred to supervisor."
