from langchain_core.tools import tool

@tool
def trigger_investment_confirmation() -> str:
    """
    Call this tool ONLY when you have identified the exact single Asset ID 
    and the user has specified a valid investment amount. 
    You MUST call this tool to proceed with the investment; do not just reply textually.
    This tool triggers the investment confirmation process in the UI.
    Do NOT call this tool if you need to ask the user a clarifying question.
    """
    return "Investment confirmation triggered."
