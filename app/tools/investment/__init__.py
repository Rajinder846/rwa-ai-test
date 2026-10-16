from app.tools.investment.validate_investment import (
    validate_investment,
)
from app.tools.asset.get_asset_details import (
    get_asset_details,
)
from app.tools.asset.search_assets import (
    search_assets,
)
from app.tools.investment.trigger_investment import (
    trigger_investment_confirmation,
)

from app.tools.transfer import transfer_to_supervisor

INVESTMENT_TOOLS = [
    # validate_investment,
    get_asset_details,
    search_assets,
    trigger_investment_confirmation,
    transfer_to_supervisor,
]