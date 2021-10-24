import copy

import asyncio

import requests
import aiohttp


from utility.files_util import load_json

from parsing import get_idx_from_asset_name

from urls import CNFT_API_URL

MARKETPLACE = "cnft"


async def fetch_data_from_marketplace(policy_id: str, sold=False) -> list:
    
    payload = {
        "search": policy_id,
        "sort": "date",
        "order": "desc",
        "page": 1,
        "verified": "true",
        "count": 200
    }

    if sold:
        payload["sold"] = "true"

    try:
        responses = await fetch_all(CNFT_API_URL, payload)
    except:
        print("Fetching data failed!")
        return
    else:
        if responses:
            assets = get_data_from_responses(responses)
            if assets:

                assets_parsed = parse_data(assets, sold)

                assets_extended = add_num_props(assets_parsed)

                return assets_extended

async def fetch_all(url, payload: dict):
    payloads = get_payloads(url, payload)
    if payloads:
        async with aiohttp.ClientSession() as session:
            tasks = get_tasks_for_pagination(session, url, payloads)
            responses = await asyncio.gather(*tasks, return_exceptions=True)

            return responses

def get_payloads(url, payload: dict):
    payloads = list()

    items_found = get_items_found(url, payload)
    if items_found:
        items_per_page = payload.get("count")
        pages = (items_found // items_per_page) + 1

        for idx in range(pages):
            page = idx + 1
            new_payload = copy.deepcopy(payload)
            new_payload["page"] = page
            payloads.append(new_payload)
        
        return payloads

def get_items_found(url, payload: dict):
    response_data = post_request(url, payload)
    if response_data:
        items_found = response_data.get("found", None)
        return items_found

def post_request(url, payload: dict):
    try:
        response = requests.post(url, payload).json()
    except:
        return
    else:
        return response

def get_tasks_for_pagination(session, url, payloads: list):
    tasks = list()

    for payload in payloads:
        tasks.append(fetch(session, url, payload))

    return tasks 

async def fetch(session, url, payload: dict):
    async with session.post(url, json=payload) as response:
        try:
            resp = await response.json()
        except:
            return
        else:
            return resp

def get_data_from_responses(responses) -> list:
    num_assets_found = 0

    assets = list()

    for response in responses:
        if response:
            if not num_assets_found:
                num_assets_found = response.get("found", 0)

            assets_found = response.get("assets", None)
            if assets_found:
                assets.extend(assets_found)
    
    if num_assets_found > len(assets):
        print("not all assets requested")
        print(num_assets_found, len(assets))
        return
    
    print(f"{len(assets)} assets found at {MARKETPLACE.upper()}!")
    return assets

def parse_data(assets: list, sold=False) -> list:

    parsed = list()

    for asset in assets:
        asset_parsed = dict()

        name = asset.get("metadata").get("name")
        asset_parsed["assetid"] = name.replace("_", "")
        asset_parsed["unit"] = asset.get("unit")
        asset_parsed["price"] = asset.get("price")
        asset_parsed["sold"] = asset.get("sold")
        asset_parsed["id"] = asset.get("id")
        asset_parsed["marketplace"] = MARKETPLACE

        if sold:
            asset_parsed["date"] = asset.get("dateSold")
        else:
            asset_parsed["date"] = asset.get("dateListed")
            payment_session = asset.get("paymentSession")
            asset_parsed["reserved"] = True if payment_session else False

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