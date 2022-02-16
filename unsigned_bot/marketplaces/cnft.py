"""
Module for fetching data from cnft.io marketplace
"""

from typing import Optional, List, Dict
import copy
import asyncio
import aiohttp
from aiohttp import ClientSession, ClientResponse

from unsigned_bot.utility.time_util import datetime_to_timestamp
from unsigned_bot.log import logger
from unsigned_bot.parsing import add_num_props
from unsigned_bot.urls import CNFT_API_URL

MARKETPLACE = "cnft"


async def fetch_data_from_marketplace(project_name: str, sold: Optional[bool] = False) -> list:
    """Fetch assets data via pagination and return list of parsed assets"""
    
    url = CNFT_API_URL

    payload = {
        "project": project_name,
        "page": 1,
        "verified": True,
        "sold": sold
    }

    if sold:
        payload["types"] = [] 
    else:
        payload["types"] = [
            "auction",
            "listing",
            "offer"
        ]
    
    BURST_SIZE = 25
    
    assets_total = list()

    fetching = True
    num_requests = 1
    while fetching:
        pages = range((num_requests-1) * BURST_SIZE, num_requests*BURST_SIZE)
        payloads = get_payloads(pages, payload)

        try:
            responses = await fetch_all(url, payloads)
        except:
            logger.warning(f"Fetching data from {MARKETPLACE.upper()} failed")
            return
        else:
            if responses:
                assets = get_data_from_responses(responses)
                if assets:
                    assets_parsed = parse_data(assets, sold)
                    assets_extended = add_num_props(assets_parsed)
                    assets_total.extend(assets_extended)
                else:
                    fetching = False

        num_requests += 1
    
    logger.info(f"{len(assets_total)} assets found at {MARKETPLACE.upper()}")

    return assets_total

async def fetch_all(url: str, payloads: List[dict]) -> list:
    """Make concurrent requests to url with given payloads and return responses"""

    async with aiohttp.ClientSession() as session:
        tasks = get_tasks_for_pagination(session, url, payloads)
        responses = await asyncio.gather(*tasks, return_exceptions=True)

        return responses

def get_payloads(pages: List[int], payload: dict) -> list:
    """Duplicate payload for given pages and return payloads"""

    payloads = list()

    for idx in pages:
        page = idx + 1
        new_payload = copy.deepcopy(payload)
        new_payload["page"] = page
        payloads.append(new_payload)
    
    return payloads

def get_tasks_for_pagination(session: ClientSession, url: str, payloads: List[dict]) -> list:
    """Add fetching tasks for session and return tasks"""

    tasks = list()
    for payload in payloads:
        tasks.append(fetch(session, url, payload))

    return tasks     

async def fetch(session: ClientSession, url: str, payload: dict) -> ClientResponse:
    """Return response from requests inside given session"""

    async with session.post(url, json=payload) as response:
        try:
            resp = await response.json()
        except:
            return
        else:
            return resp

def get_data_from_responses(responses: List[dict]) -> list:
    """Parse list of responses and return extracted assets"""

    assets = list()

    for response in responses:
        if response:
            assets_found = response.get("results")
            if assets_found:
                assets.extend(assets_found)
    
    return assets

def parse_data(assets: List[dict], sold: bool = False) -> list:
    """
    Extract relevant data from assets.
    Has to be kept updated along with cnft API.
    """

    parsed = list()

    for asset in assets:
        asset_parsed = dict()

        # sometimes key is 'assets' instead of 'asset'
        asset_data = asset.get("asset")
        if not asset_data:
            asset_data = asset.get("assets")[0]

        asset_parsed["assetid"] = asset_data.get("assetId")
        asset_parsed["price"] = asset.get("price")
        asset_parsed["id"] = asset.get("_id")
        asset_parsed["marketplace"] = MARKETPLACE

        if sold:
            datetime_str = asset.get("soldAt")
            asset_parsed["sold"] = True
        else:
            datetime_str = asset.get("createdAt")
            asset_parsed["sold"] = False
            asset_parsed["type"] = asset.get("type") #set type only for offers

        if not datetime_str:
            datetime_str = asset.get("updatedAt")

        # only add asset if date exists
        if datetime_str:
            asset_parsed["date"] = datetime_to_timestamp(datetime_str)
            parsed.append(asset_parsed)
    
    return parsed