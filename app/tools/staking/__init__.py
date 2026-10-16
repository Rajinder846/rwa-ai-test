from .get_staking_pools import get_staking_pools
from .get_user_stakes import get_user_stakes
from .get_staking_categories import get_staking_categories

from app.tools.transfer import transfer_to_supervisor

STAKING_TOOLS = [
    get_staking_pools,
    get_user_stakes,
    transfer_to_supervisor,
]
