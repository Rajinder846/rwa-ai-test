from app.tools.asset.get_asset_details import (
    get_asset_details,
)

from app.tools.asset.search_assets import (
    search_assets,
)

from app.tools.transfer import transfer_to_supervisor

ASSET_TOOLS = [
    get_asset_details,
    search_assets,
    transfer_to_supervisor,
]