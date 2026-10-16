from app.tools.payout.payout_history import (
    get_payout_history,
)
from app.tools.payout.upcoming_payouts import (
    get_upcoming_payouts,
)

from app.tools.transfer import transfer_to_supervisor

PAYOUT_TOOLS = [
    get_payout_history,
    get_upcoming_payouts,
    transfer_to_supervisor,
]
