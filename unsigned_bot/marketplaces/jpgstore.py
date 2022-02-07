import requests

from unsigned_bot.utility.time_util import datetime_to_timestamp
from unsigned_bot.log import logger
from unsigned_bot.parsing import add_num_props
from unsigned_bot.urls import JPGSTORE_API_URL

MARKETPLACE = "jpgstore"


async def get_data_from_marketplace(policy_id: str, sold=False) -> list:
    
    request_type = "sales" if sold else "listings"
    url = f"{JPGSTORE_API_URL}/policy/{policy_id}/{request_type}"

    try:
        response = requests.get(url).json()
    except:
        logger.warning(f"Fetching data from {MARKETPLACE.upper()} failed")
        return
    else:
        if isinstance(response, list):
            assets_parsed = parse_data(response, sold)
            assets_extended = add_num_props(assets_parsed)
        
        logger.info(f"{len(assets_extended)} assets found at {MARKETPLACE.upper()}")
        
        return assets_extended

def parse_data(assets: list, sold: bool) -> list:
    parsed = list()

    for asset in assets:
        asset_parsed = dict()

        asset_parsed["assetid"] = asset.get("asset_display_name").replace("_", "")
        asset_parsed['price'] = asset.get("price_lovelace")
        asset_parsed["id"] = asset.get("asset")
        asset_parsed['marketplace'] = MARKETPLACE
        
        if sold:
            date = asset.get("confirmed_at")
            if not date:
                continue
            asset_parsed["date"] = datetime_to_timestamp(date)
            asset_parsed["sold"] = True
        else:
            asset_parsed["type"] = "listing"
            asset_parsed["sold"] = False

        parsed.append(asset_parsed)

    return parsed