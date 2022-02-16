"""
Module for fetching data
"""

import os
import json
from typing import Optional
import requests
from requests_html import HTMLSession, AsyncHTMLSession

from unsigned_bot.utility.files_util import load_json
from unsigned_bot.constants import POLICY_ID, ASSESSMENTS_POLICY_ID
from unsigned_bot.urls import CARDANOSCAN_URL, BLOCKFROST_IPFS_URL, BLOCKFROST_API_URL, POOL_PM_URL
from unsigned_bot import ROOT_DIR

from dotenv import load_dotenv
load_dotenv() 

BLOCKFROST_API_TOKEN = os.getenv("BLOCKFROST_API_TOKEN")
BLOCKFROST_API_HEADERS = {
    "project_id": BLOCKFROST_API_TOKEN
}
BLOCKFROST_API_URL = "https://cardano-mainnet.blockfrost.io/api/v0"


def get_request(url: str, headers: Optional[dict] = None, params: Optional[dict] = None):
    """Return response if request is successful and in JSON format"""
    try:
        response = requests.get(url, headers=headers, params=params).json()
    except:
        return
    else:
        return response


# === Blockfrost API calls ===
def get_asset_ids(policy_id: str) -> list:
    """Return list of asset ids for a given policy"""

    url = f"{BLOCKFROST_API_URL}/assets/policy/{policy_id}"
    params = {
        "page": 1,
        "order": "desc"
    }
    response = get_request(url, headers=BLOCKFROST_API_HEADERS, params=params)
    
    if response:
        return [asset.get("asset") for asset in response]

def get_asset_data(asset_id: str) -> dict:
    """Return data for asset with given asset id"""
    url = f"{BLOCKFROST_API_URL}/assets/{asset_id}"
    response = get_request(url, headers=BLOCKFROST_API_HEADERS)
    return response

def get_tx_data(tx_id: str) -> dict:
    "Return data for transaction with given id"
    url = f"{BLOCKFROST_API_URL}/txs/{tx_id}"
    response = get_request(url, headers=BLOCKFROST_API_HEADERS)
    return response

def get_block_data(block_id: str) -> dict:
    "Return data for block with given id"
    url = f"{BLOCKFROST_API_URL}/blocks/{block_id}"

    response = get_request(url, headers=BLOCKFROST_API_HEADERS)
    return response

def get_tx_timestamp(tx_id: str) -> int:
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

async def get_ipfs_url_from_file(asset_name: str) -> str:
    """Load ipfs from file for given unsig"""
    ipfs_urls = load_json(f"{ROOT_DIR}/data/json/ipfs_urls.json")
    return ipfs_urls.get(asset_name, None)

async def get_ipfs_url(asset_id: str, asset_name: str) -> str:
    """Get ipfs url from metadata of given unsig"""
    metadata = await get_metadata(asset_id)

    if metadata:
        ipfs_hash = get_ipfs_hash(metadata, asset_name)

        if ipfs_hash:
            ipfs_url = f"{BLOCKFROST_IPFS_URL}/{ipfs_hash}"
            return ipfs_url

async def get_metadata(asset_id: str) -> dict:
    """Get metadata of given unsig"""
    tx_id = await get_minting_tx_id(asset_id)

    if tx_id:
        metadata = await metadata_from_tx_id(tx_id)
        return metadata

# === END blockfrost API calls ==

async def get_minting_tx_id(asset_id: str) -> str:
    """Get id of minting transaction for given asset id by scraping HTML"""

    try:
        URL = f"{CARDANOSCAN_URL}/token/{asset_id}/?tab=minttransactions"
        asession = AsyncHTMLSession()
        r = await asession.get(URL)
    except:
        return
    else:
        try:
            tx_id = r.html.xpath("//*[@id='minttransactions']//a[starts-with(@href,'/transaction')]/text()")[0]
        except:
            return
        else:
            return tx_id

async def metadata_from_tx_id(tx_id: str) -> dict:
    """Get metadata for transaction with given id by scraping HTML"""

    try:
        URL=f"{CARDANOSCAN_URL}/transaction/{tx_id}/?tab=metadata"
        session = HTMLSession()
        r = session.get(URL)
    except:
        return
    else:
        metadata_str = r.html.xpath("//*[@class='metadata-value']/text()")[0]

        if metadata_str:
            metadata = json.loads(metadata_str)
            return metadata

def get_ipfs_hash(metadata: dict, asset_name: str) -> str:
    """Return extracted ipfs hash from metadata"""

    try:
        image_url = metadata.get(POLICY_ID).get(asset_name).get("image", None)
    except:
        return
    else:
        if image_url:   
            return image_url.rsplit("/")[-1]

def get_metadata_from_asset_name(asset_name: str) -> dict:
    """Get metadata for given asset"""
    url = f"{POOL_PM_URL}/asset/{POLICY_ID}.{asset_name}"
    response = get_request(url, headers=None)
    return response.get("metadata")

def get_unsig_data(idx: str) -> dict:
    """Load properties data from file for given unsig"""
    unsigs_data = load_json(f"{ROOT_DIR}/data/json/unsigs.json")
    return unsigs_data.get(idx, None)

def get_minting_number(asset_name: str) -> int:
    """Load minting order from file for given unsig"""
    minting_order = load_json(f"{ROOT_DIR}/data/json/minted.json")
    number = minting_order.index(asset_name) + 1
    return number

def get_minting_data(number: str) -> tuple:
    """Load minting data from file for given unsig"""

    unsigs_minted = load_json(f"{ROOT_DIR}/data/json/unsigs_minted.json")
    
    minting_data = unsigs_minted.get(number)
    minting_time = minting_data.get("time")
    minting_order = minting_data.get("order")

    return (int(minting_order), int(minting_time))

def get_current_owner_address(token_id: str) -> str:
    """Get current owner address for given token id by scraping HTML"""

    try:
        url = f"{CARDANOSCAN_URL}/token/{token_id}?tab=topholders"
        session = HTMLSession()

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

def get_wallet_balance(address: str) -> int:
    "Get current balance for wallet with given address"
    try:
        url = f"{POOL_PM_URL}/wallet/{address}"
        response = get_request(url, headers=None)

        lovelaces = response.get("lovelaces", 0)
        reward = response.get("reward", 0)
        withdrawal = response.get("withdrawal", 0)
    except:
        return
    else:
        return lovelaces + reward - withdrawal

def get_new_certificates(certificates: dict) -> dict:
    """Identify new certificates and fetch data for each certificate"""

    asset_ids = get_asset_ids(ASSESSMENTS_POLICY_ID)
    new_certs_ids = set(asset_ids).difference(set(certificates.keys()))

    new_certs = dict()
    for cert_id in list(new_certs_ids):
        cert_data = get_asset_data(cert_id)

        # add date to certificate data
        tx_id = cert_data.get('initial_mint_tx_hash')
        cert_data["date"] = get_tx_timestamp(tx_id)

        new_certs[cert_id] = cert_data

    return new_certs