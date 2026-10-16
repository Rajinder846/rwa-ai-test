from decimal import Decimal
from math import ceil

from langchain_core.tools import tool


@tool
def validate_investment(
    token_amount: int,
    token_price_sar: Decimal,
    minimum_investment: Decimal,
    available_tokens: int,
) -> dict:
    """
    Validate an investment using SAR only.
    """

    if token_amount <= 0:

        return {
            "valid": False,
            "message": (
                "The token amount must be "
                "greater than zero."
            ),
        }

    if token_amount > available_tokens:

        return {
            "valid": False,
            "message": (
                f"Only {available_tokens} tokens "
                f"are currently available. "
                f"You requested {token_amount} tokens."
            ),
        }

    total_amount = (
        Decimal(token_amount)
        * Decimal(token_price_sar)
    )

    # Minimum investment is an AMOUNT in SAR.
    if total_amount < Decimal(
        minimum_investment
    ):

        minimum_tokens = ceil(
            Decimal(minimum_investment)
            / Decimal(token_price_sar)
        )

        return {
            "valid": False,

            "total_amount": (
                total_amount
            ),

            "minimum_tokens": (
                minimum_tokens
            ),

            "currency": "SAR",

            "message": (
                f"The minimum investment is "
                f"{minimum_investment} SAR. "
                f"At {token_price_sar} SAR "
                f"per token, you need to "
                f"invest at least "
                f"{minimum_tokens} tokens."
            ),
        }

    return {
        "valid": True,

        "total_amount": (
            total_amount
        ),

        "currency": "SAR",

        "minimum_tokens": None,

        "message": None,
    }