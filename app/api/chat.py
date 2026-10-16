from uuid import uuid4

from fastapi import APIRouter, Depends
from langchain_core.messages import HumanMessage
from langgraph.types import Command

from app.auth.dependencies import require_roles
from app.auth.models import AuthContext
from app.config.settings import settings
from app.graph.graph import graph


router = APIRouter(
    prefix="/chat",
    tags=["Chat"],
)


def extract_response(messages) -> str:
    """
    Extract text from the latest AI message.
    """

    if not messages:
        return ""

    final_message = messages[-1]
    content = final_message.content

    if isinstance(content, str):
        return content

    if isinstance(content, list):

        text_parts = []

        for item in content:

            if (
                isinstance(item, dict)
                and item.get("type") == "text"
            ):
                text_parts.append(
                    item.get("text", "")
                )

        return "\n".join(text_parts)

    return str(content)


@router.post("")
async def chat(
    message: str,
    conversation_id: str,

    auth: AuthContext = Depends(require_roles(*(role.strip() for role in settings.auth_chat_roles.split(",")))),
):

    config = {
        "configurable": {
            "thread_id": conversation_id,

            # Request-scoped JWT
            "user_jwt": auth.token,
        }
    }

    # -----------------------------------------
    # Normal user message
    # -----------------------------------------

    result = await graph.ainvoke(
        {
            "request_id": str(uuid4()),
            "user_id": auth.user.user_id,
            "conversation_id": conversation_id,
            "status": "idle",

            "messages": [
                HumanMessage(
                    content=message
                )
            ],
        },
        config=config,
    )

    # -----------------------------------------
    # CHECK LANGGRAPH INTERRUPT
    # -----------------------------------------

    if "__interrupt__" in result:

        interrupt_data = result[
            "__interrupt__"
        ][0]

        interrupt_value = (
            interrupt_data.value
        )

        return {
            "conversation_id": conversation_id,
            "user_id": auth.user.user_id,

            "status": "waiting_for_confirmation",

            "response": interrupt_value.get(
                "message",
                "",
            ),

            "show_confirmation": True,

            "investment": interrupt_value.get(
                "investment"
            ),

            "actions": interrupt_value.get(
                "actions",
                ["confirm", "cancel"],
            ),
        }

    # -----------------------------------------
    # Normal response
    # -----------------------------------------

    messages = result.get(
        "messages",
        []
    )

    response_text = extract_response(
        messages
    )

    return {
        "conversation_id": conversation_id,
        "user_id": auth.user.user_id,

        "status": result.get(
            "status",
            "completed",
        ),

        "response": response_text,

        "show_confirmation": False,
    }


@router.post("/resume")
async def resume_chat(
    action: str,
    conversation_id: str,

    auth: AuthContext = Depends(require_roles(*(role.strip() for role in settings.auth_chat_roles.split(",")))),
):

    if action not in [
        "confirm",
        "cancel",
    ]:
        return {
            "conversation_id": conversation_id,
            "status": "failed",
            "response": (
                "Invalid confirmation action."
            ),
        }

    config = {
        "configurable": {
            "thread_id": conversation_id,

            # Request-scoped JWT
            "user_jwt": auth.token,
        }
    }

    # -----------------------------------------
    # RESUME INTERRUPTED GRAPH
    # -----------------------------------------

    result = await graph.ainvoke(
        Command(
            resume=action
        ),
        config=config,
    )

    # -----------------------------------------
    # Another interrupt?
    # -----------------------------------------

    if "__interrupt__" in result:

        interrupt_data = result[
            "__interrupt__"
        ][0]

        interrupt_value = (
            interrupt_data.value
        )

        return {
            "conversation_id": conversation_id,

            "status": (
                "waiting_for_confirmation"
            ),

            "response": interrupt_value.get(
                "message",
                "",
            ),

            "show_confirmation": True,

            "investment": interrupt_value.get(
                "investment"
            ),

            "actions": interrupt_value.get(
                "actions",
                ["confirm", "cancel"],
            ),
        }

    # -----------------------------------------
    # Graph completed
    # -----------------------------------------

    messages = result.get(
        "messages",
        []
    )

    response_text = extract_response(
        messages
    )

    return {
        "conversation_id": conversation_id,

        "user_id": auth.user.user_id,

        "status": result.get(
            "status",
            "completed",
        ),

        "response": response_text,

        "show_confirmation": False,
    }


# from fastapi import APIRouter, Depends
# from langchain_core.messages import HumanMessage

# from app.auth.dependencies import get_auth_context
# from app.auth.models import AuthContext
# from app.graph.graph import graph


# router = APIRouter(
#     prefix="/chat",
#     tags=["Chat"],
# )


# @router.post("")
# async def chat(
#     message: str,
#     conversation_id: str,

#     auth: AuthContext = Depends(
#         get_auth_context
#     ),
# ):

#     result = await graph.ainvoke(
#         {
#             "user_id": auth.user.user_id,
#             "conversation_id": conversation_id,
#             "status": "idle",
#             "messages": [
#                 HumanMessage(
#                     content=message
#                 )
#             ],
#         },
#         config={
#             "configurable": {
#                 "thread_id": conversation_id,

#                 # Request-scoped JWT.
#                 # Do NOT put this in WorkflowState.
#                 "user_jwt": auth.token,
#             }
#         },
#     )

#     messages = result.get("messages", [])

#     if not messages:
#         response_text = ""
#     else:
#         final_message = messages[-1]
#         content = final_message.content

#         if isinstance(content, str):
#             response_text = content

#         elif isinstance(content, list):
#             text_parts = []

#             for item in content:
#                 if (
#                     isinstance(item, dict)
#                     and item.get("type") == "text"
#                 ):
#                     text_parts.append(
#                         item.get("text", "")
#                     )

#             response_text = "\n".join(text_parts)

#         else:
#             response_text = str(content)

#     return {
#         "conversation_id": conversation_id,
#         "user_id": auth.user.user_id,
#         "response": response_text,
#     }
