import os

import json
import copy

from pprint import pprint

import asyncio

import requests
from requests_html import HTMLSession, AsyncHTMLSession

import aiohttp

from utility.files_util import load_json

from parsing import get_idx_from_asset_name

from urls import POOL_PM_URL

from dotenv import load_dotenv
load_dotenv() 

POLICY_ID = os.getenv('POLICY_ID')

BLOCKFROST_API_TOKEN = os.getenv("BLOCKFROST_API_TOKEN")
BLOCKFROST_API_HEADERS = {
    "project_id": BLOCKFROST_API_TOKEN
}

BLOCKFROST_API_URL = "https://cardano-mainnet.blockfrost.io/api/v0"

ASSESSMENTS_POLICY_ID = os.getenv('ASSESSMENTS_POLICY_ID')

from urls import CARDANOSCAN_URL, BLOCKFROST_IPFS_URL


def post_request(url, payload: dict):
    try:
        response = requests.post(url, payload).json()
    except:
        return
    else:
        return response

def get_items_found(url, payload: dict):
    response_data = post_request(url, payload)
    if response_data:
        items_found = response_data.get("found", None)
        return items_found


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

async def fetch_all(url, payload: dict):
    payloads = get_payloads(url, payload)
    if payloads:
        async with aiohttp.ClientSession() as session:
            tasks = get_tasks_for_pagination(session, url, payloads)
            responses = await asyncio.gather(*tasks, return_exceptions=True)

            return responses

async def fetch_data_from_marketplace(url, policy_id: str, sold=False) -> list:
    
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
        responses = await fetch_all(url, payload)
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
    
    print(f"{len(assets)} assets found!")
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

def get_request(url, headers=None, params=None):
    try:
        response = requests.get(url, headers=headers, params=params).json()
    except:
        return
    else:
        return response

# Blockfrost API Calls
def get_asset_ids(policy_id: str) -> list:
    url = f"{BLOCKFROST_API_URL}/assets/policy/{policy_id}"

    params = {
        "page": 1,
        "order": "desc"
    }

    response = get_request(url, headers=BLOCKFROST_API_HEADERS, params=params)
    if response:
       return [asset.get("asset") for asset in response]

def get_asset_data(asset_id: str) -> dict:
    url = f"{BLOCKFROST_API_URL}/assets/{asset_id}"

    response = get_request(url, headers=BLOCKFROST_API_HEADERS)
    if response:
        return response

def get_tx_data(tx_id):
    url = f"{BLOCKFROST_API_URL}/txs/{tx_id}"

    response = get_request(url, headers=BLOCKFROST_API_HEADERS)
    if response:
        return response

def get_block_data(block_id):
    url = f"{BLOCKFROST_API_URL}/blocks/{block_id}"

    response = get_request(url, headers=BLOCKFROST_API_HEADERS)
    if response:
        return response

def get_tx_timestamp(tx_id):
    """Return timestamp of tx [in ms]"""
    try:
        tx_data = get_tx_data(tx_id)
        block_id = tx_data.get("block")
        block_data = get_block_data(block_id)
        timestamp = block_data.get("time")
    except:
        return 0
    else:
        return timestamp * 1000


async def get_ipfs_url_from_file(asset_name):
    ipfs_urls = load_json("json/ipfs_urls.json")
    return ipfs_urls.get(asset_name, None)


async def get_ipfs_url(asset_id, asset_name):
    metadata = await get_metadata(asset_id)
    if metadata:
        ipfs_hash = get_ipfs_hash(metadata, asset_name)
        if ipfs_hash:
            ipfs_url = f"{BLOCKFROST_IPFS_URL}/{ipfs_hash}"
            return ipfs_url

async def get_metadata(asset_id):
    tx_id = await get_minting_tx_id(asset_id)

    if tx_id:
        metadata = await metadata_from_tx_id(tx_id)

        return metadata

async def get_minting_tx_id(asset_id):
    URL=f"{CARDANOSCAN_URL}/token/{asset_id}/?tab=minttransactions"

    asession = AsyncHTMLSession()

    try:
        r = await asession.get(URL)
    except:
        return
    else:
        try:
            tx_id=r.html.xpath("//*[@id='minttransactions']//a[starts-with(@href,'/transaction')]/text()")[0]
        except:
            return
        else:
            return tx_id

async def metadata_from_tx_id(tx_id):
    URL=f"{CARDANOSCAN_URL}/transaction/{tx_id}/?tab=metadata"

    session = HTMLSession()

    try:
        r = session.get(URL)
    except:
        return
    else:
        metadata_str=r.html.xpath("//*[@class='metadata-value']/text()")[0]
        if metadata_str:
            metadata = json.loads(metadata_str)
            return metadata

def get_ipfs_hash(metadata, asset_name):
    try:
        image_url = metadata.get(POLICY_ID).get(asset_name).get("image", None)
    except:
        return
    else:
        if image_url:   
            return image_url.rsplit("/")[-1]



def get_metadata_from_asset_name(asset_name):
    url = f"{POOL_PM_URL}/asset/{POLICY_ID}.{asset_name}"
    response = get_request(url, headers=None)
    return response.get("metadata")

def get_unsigs_data(idx:str):
    unsigs_data = load_json("json/unsigs.json")
    return unsigs_data.get(idx, None)

def get_minting_number(asset_name):
    minting_order = load_json("json/minted.json")
    number = minting_order.index(asset_name) + 1
    return number

def get_minting_data(number: str):
    unsigs_minted = load_json("json/unsigs_minted.json")
    
    minting_data = unsigs_minted.get(number)

    minting_time = minting_data.get("time")
    minting_order = minting_data.get("order")

    return (int(minting_order), int(minting_time))

def get_current_owner_address(token_id: str) -> str:
    url = f"{CARDANOSCAN_URL}/token/{token_id}?tab=topholders"

    session = HTMLSession()

    try:
        r = session.get(url)
    except:
        address = None
    else:
        try:
            address_str = r.html.xpath("//*[@id='topholders']//a[contains(@href,'address')]/text()")[0]
            address_id = r.html.xpath("//*[@id='topholders']//a[contains(@href,'address')]/@href")[0]
            address_id = address_id.rsplit("/")[-1]
        except:
            address = None
        else:
            address = {
                "id": address_id,
                "name": address_str
            }
    finally:
        return address

def get_wallet_balance(address):
    url = f"{POOL_PM_URL}/wallet/{address}"
    response = get_request(url, headers=None)
    if response:
        lovelaces = response.get("lovelaces", 0)
        reward = response.get("reward", 0)

        return lovelaces + reward

def get_new_certificates(certificates: dict) -> dict:
    asset_ids = get_asset_ids(ASSESSMENTS_POLICY_ID)

    new_certs_ids = set(asset_ids).difference(set(certificates.keys()))

    new_certs = dict()
    for cert_id in list(new_certs_ids):
        cert_data = get_asset_data(cert_id)
        tx_id = cert_data.get('initial_mint_tx_hash')
        cert_data["date"] = get_tx_timestamp(tx_id)
        new_certs[cert_id] = cert_data

    return new_certs

