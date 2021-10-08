import os


import os
import copy

import asyncio

import requests
import aiohttp

from files_util import load_json, save_json

from dotenv import load_dotenv
load_dotenv() 

BLOCKFROST_API_TOKEN = os.getenv("BLOCKFROST_API_TOKEN")
BLOCKFROST_API_HEADERS = {
    "project_id": BLOCKFROST_API_TOKEN
}

BLOCKFROST_API_URL = "https://cardano-mainnet.blockfrost.io/api/v0"

ASSESSMENTS_POLICY_ID = os.getenv('ASSESSMENTS_POLICY_ID')



def post_request(url, payload):
    try:
        response = requests.post(url, payload).json()
    except:
        return
    else:
        return response

def get_items_found(url, payload):
    response_data = post_request(url, payload)
    if response_data:
        items_found = response_data.get("found", None)
        return items_found


def get_payloads(url, payload):
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

def get_tasks_for_pagination(session, url, payloads):
    tasks = list()

    for payload in payloads:
        tasks.append(fetch(session, url, payload))

    return tasks       

async def fetch(session, url, payload):
    async with session.post(url, json=payload) as response:
        try:
            resp = await response.json()
        except:
            return
        else:
            return resp

async def fetch_all(url, payload):
    payloads = get_payloads(url, payload)
    if payloads:
        async with aiohttp.ClientSession() as session:
            tasks = get_tasks_for_pagination(session, url, payloads)
            responses = await asyncio.gather(*tasks, return_exceptions=True)

            return responses

async def fetch_data_from_marketplace(url, policy_id, sold=False):
    
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
            assets = get_data_from_reponses(responses)
            if assets:
                assets_parsed = parse_data(assets, sold)

                assets_extended = add_num_props(assets_parsed)

                return assets_extended


def get_data_from_reponses(responses):
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

def parse_data(assets, sold=False):
    parsed = list()

    for asset in assets:
        asset_parsed = dict()
        asset_parsed["assetid"] = asset.get("metadata").get("name")
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
        idx = str(int(asset_name.replace("unsig_","")))

        unsigs_data = unsigs.get(idx)
        asset["num_props"] = unsigs_data.get("num_props")
    
    return assets

def call_api(url, headers=None, params=None):
    try:
        response = requests.get(url, headers=headers, params=params).json()
    except:
        return
    else:
        return response

def get_asset_ids(policy_id: str) -> list:
    url = f"{BLOCKFROST_API_URL}/assets/policy/{policy_id}"

    params = {
        "page": 1,
        "order": "desc"
    }

    response = call_api(url, headers=BLOCKFROST_API_HEADERS, params=params)
    if response:
       return [asset.get("asset") for asset in response]

def get_asset_data(asset_id):
    url = f"{BLOCKFROST_API_URL}/assets/{asset_id}"

    response = call_api(url, headers=BLOCKFROST_API_HEADERS)
    if response:
        return response

def update_certificates(certificates: dict, new_certs: dict):
    if new_certs:
        certificates.update(new_certs)
        save_json("json/certificates.json", certificates)

def get_new_certificates(certificates: dict) -> dict:
    asset_ids = get_asset_ids(ASSESSMENTS_POLICY_ID)

    new_certs_ids = set(asset_ids).difference(set(certificates.keys()))

    new_certs = dict()
    for cert_id in list(new_certs_ids):
        cert_data = get_asset_data(cert_id)
        new_certs[cert_id] = cert_data

    return new_certs


