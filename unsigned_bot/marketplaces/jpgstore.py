import requests

from unsigned_bot.utility.files_util import save_json
from unsigned_bot.utility.time_util import datetime_to_timestamp
from unsigned_bot.parsing import add_num_props
from unsigned_bot.urls import JPGSTORE_API_URL

MARKETPLACE = "jpgstore"


async def get_data_from_marketplace(policy_id: str, sold=False) -> list:
    
    request_type = "sales" if sold else "listings"
    url = f"{JPGSTORE_API_URL}/policy/{policy_id}/{request_type}"

    try:
        response = requests.get(url).json()
    except:
        print("Fetching data failed!")
        return
    else:
        if isinstance(response, list):
            assets_parsed = parse_data(response, sold)
            assets_extended = add_num_props(assets_parsed)
        
        print(f"{len(assets_extended)} assets found at {MARKETPLACE.upper()}!")
        return assets_extended

def parse_data(assets: list, sold: bool) -> list:
    parsed = list()

    for asset in assets:
        asset_parsed = dict()

        asset_parsed["assetid"] = asset.get("asset_display_name").replace("_", "")
        asset_parsed['price'] = asset.get("price_lovelace")
        asset_parsed["id"] = asset.get("asset")
        asset_parsed['marketplace'] = MARKETPLACE
        asset_parsed["sold"] = True if asset.get("is_confirmed") else False

        if sold:
            date = asset.get("purchased_at")
            asset_parsed["date"] = datetime_to_timestamp(date)
        else:
            asset_parsed["type"] = "listing"

        parsed.append(asset_parsed)

    return parsed
