import asyncio
from langchain_core.tools import tool
from langchain_core.runnables import RunnableConfig

@tool
async def my_tool(x: int, config: RunnableConfig) -> str:
    """A tool"""
    return f"x={x}, jwt={config.get('configurable', {}).get('user_jwt')}"

async def main():
    print("Schema:", my_tool.args_schema.schema())
    res = await my_tool.ainvoke({"x": 42}, config={"configurable": {"user_jwt": "secret"}})
    print("Result:", res)

if __name__ == "__main__":
    asyncio.run(main())
