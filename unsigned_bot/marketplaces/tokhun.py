"""
Module for fetching data from tokhun.io marketplace
"""

from typing import Optional
import requests
from ratelimit import limits

from unsigned_bot.log import logger
from unsigned_bot.parsing import add_num_props
from unsigned_bot.urls import TOKHUN_API_URL

MARKETPLACE = "tokhun"


async def get_data_from_marketplace(policy_id: str, sold: Optional[bool] = False) -> list:
    """Fetch assets data via pagination and return list of parsed assets"""

    if sold:
        url = f"{TOKHUN_API_URL}/sold"
    else:
        url = f"{TOKHUN_API_URL}/live"
    
    if policy_id:
        url += f"/{policy_id}"

    assets_all = list()

    params = {
        "page": 1
    }

    next_page = True
    while next_page:
        try:
            response = call_api(url, params).json()
        except:
            logger.warning(f"Fetching data from {MARKETPLACE.upper()} failed")
            return
        else:
            new_assets = response.get("data")
            if new_assets:
                assets_parsed = parse_data(new_assets, sold)
                assets_extended = add_num_props(assets_parsed)
                assets_all.extend(assets_extended)
            else:
                next_page = False
        
        params["page"] +=1

    logger.info(f"{len(assets_all)} assets found at {MARKETPLACE.upper()}")
    
    return assets_all

@limits(calls=10, period=60)
def call_api(url: str, params: dict) -> dict:
    """Request API with rate limit of 10 calls per minute"""

    response = requests.get(url, params=params)
    if response.status_code != 200:
        raise Exception('API response: {}'.format(response.status_code))
        
    return response

def parse_data(assets: list, sold=False) -> list:
    """
    Extract relevant data from assets.
    Has to be kept updated along with tokhun API.
    """

    parsed = list()

    for asset in assets:
        asset_parsed = dict()
        asset_parsed["assetid"] = asset.get("asset_name")
        asset_parsed["unit"] = asset.get("asset_id")
        price = asset.get("price_in_ada")*1000000 # convert price in ADA to lovelace
        asset_parsed["price"] = int(price)
        asset_parsed["id"] = asset.get("sale_id")
        asset_parsed['marketplace'] = MARKETPLACE
        asset_parsed["sold"] = True if asset.get("sale_status") == "Sold" else False
        
        if sold:
            asset_parsed["date"] = asset.get("sold_at_utc")*1000 # convert timestamp to ms
        else:
            asset_parsed["date"] = asset.get("sale_listed_at_utc")*1000 # convert timestamp to ms

            asset_parsed["type"] = asset.get("sale_type")
        
        # exclude bundles
        bundle = asset.get("bundle")
        if not bundle:
            parsed.append(asset_parsed)

    return parsed


