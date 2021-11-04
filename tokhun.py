import os
import asyncio

import requests
from ratelimit import limits

from utility.files_util import load_json, save_json

from parsing import get_idx_from_asset_name

from urls import TOKHUN_API_URL

from dotenv import load_dotenv
load_dotenv() 

POLICY_ID = os.getenv('POLICY_ID')

MARKETPLACE = "tokhun"


async def get_data_from_marketplace(base_url, policy_id: str, sold=False) -> list:
    if sold:
        url = f"{base_url}/sold"
    else:
        url = f"{base_url}/live"
    
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
            print("Fetching data failed!")
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

    print(f"{len(assets_all)} assets found at {MARKETPLACE.upper()}!")
    return assets_all

@limits(calls=10, period=60)
def call_api(url, params):
    response = requests.get(url, params=params)

    if response.status_code != 200:
        raise Exception('API response: {}'.format(response.status_code))
    return response

def parse_data(assets, sold=False):
    parsed = list()

    for asset in assets:
        asset_parsed = dict()
        asset_parsed["assetid"] = asset.get("asset_name")
        asset_parsed["unit"] = asset.get("asset_id")
        price = asset.get("price_in_ada")*1000000 # convert price to lovelace
        asset_parsed["price"] = int(price)
        asset_parsed["sold"] = True if asset.get("sale_status") == "Sold" else False
        asset_parsed["id"] = asset.get("sale_id")
        asset_parsed['marketplace'] = MARKETPLACE

        if sold:
            asset_parsed["date"] = asset.get("sold_at_utc")*1000 # convert timestamp to ms
        else:
            asset_parsed["date"] = asset.get("sale_listed_at_utc")*1000 # convert timestamp to ms
        
        parsed.append(asset_parsed)

    return parsed

def add_num_props(assets: list) -> list:
    unsigs = load_json("json/unsigs.json")

    for asset in assets:
        asset_name = asset.get("assetid")
        idx = get_idx_from_asset_name(asset_name)

        unsigs_data = unsigs.get(str(idx))
        asset["num_props"] = unsigs_data.get("num_props")
    
    return assets
