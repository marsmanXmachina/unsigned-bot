"""
Module for parsing and filtering data
"""

import re
import time
from datetime import datetime
from operator import itemgetter
from collections import defaultdict

from unsigned_bot.utility.files_util import load_json
from unsigned_bot.constants import MAX_AMOUNT
from unsigned_bot.urls import UNSIGS_URL, CNFT_URL, TOKHUN_URL, JPGSTORE_URL
from unsigned_bot import ROOT_DIR


def get_asset_id(asset_name: str) -> str:
    asset_ids = load_json(f"{ROOT_DIR}/json/asset_ids.json")
    return asset_ids.get(asset_name, None)

def get_asset_name_from_idx(idx: str) -> str:
    try:
        index = int(idx)
    except:
        return f"unsig{idx}"
    else:
        number_str = str(index).zfill(5)
        return f"unsig{number_str}"

def get_idx_from_asset_name(asset_name: str) -> int:
    regex_str = r"(?P<number>[0-9]+)"
    regex = re.compile(regex_str)
    match = re.search(regex, asset_name)
    number = match.group("number")
    if number:
        return int(number)

def get_numbers_from_assets(assets: list) -> list:
    return [get_idx_from_asset_name(asset.get("assetid")) for asset in assets]

def get_asset_name_from_minting_order(idx:str) -> str:
    minting_order = load_json(f"{ROOT_DIR}/json/minted.json")
    try:
        idx = int(idx)
        asset_name = minting_order[idx-1]
    except:
        return
    else:
        return asset_name

def get_numbers_from_string(string):
    return re.findall(r"\d+", string)

def get_asset_from_number(number, assets: list) -> dict:
    for asset in assets:
        asset_number = asset.get("assetid").replace("unsig", "")

        if int(asset_number) == int(number):
            return asset

def order_by_num_props(assets: list) -> dict:
    ordered = defaultdict(list)

    for asset in assets:
        num_props = asset.get("num_props")
        ordered[num_props].append(asset)

    return ordered

def get_certificate_data_by_number(number, certificates: dict) -> dict:
    for _, data in certificates.items():
        metadata = data.get("onchain_metadata")

        if metadata:
            unsig_number = metadata.get("Unsig number")
            if unsig_number == f"#{str(number).zfill(5)}":
                return data   
    else:
        return None

def filter_by_time_interval(assets: list, interval_ms) -> list:
    timestamp_now = round(time.time() * 1000)
    
    filtered = list()
    for asset in assets:
        timestamp = asset.get("date")
        if timestamp >= (timestamp_now - interval_ms):
            filtered.append(asset)

    return filtered

def filter_certs_by_time_interval(assets: dict, interval_ms) -> dict:
    return {k: v for k,v in assets.items() if v.get("date") >= ((round(time.time() * 1000) - interval_ms))}

def filter_sales_by_asset(sales, asset_name):
    return [sale for sale in sales if sale.get("assetid").replace("_","") == asset_name]

def sort_sales_by_date(sales, descending=False):
    return sorted(sales, key=itemgetter('date'), reverse=descending)

def filter_new_sales(past_sales, new_sales):
    return [sale for sale in new_sales if sale not in past_sales]

def filter_assets_by_type(assets: list, *types) -> list:
    return [asset for asset in assets if asset.get("type") in types]

def get_unsig_url(number: str):
    return f"{UNSIGS_URL}/details/{str(number).zfill(5)}"

def get_url_from_marketplace_id(marketplace_id: str, marketplace="cnft") -> str:
    if marketplace == "cnft":
        return f"{CNFT_URL}/token/{marketplace_id}"
    if marketplace == "tokhun":
        return f"{TOKHUN_URL}/marketplace/{marketplace_id}"
    if marketplace == "jpgstore":
        return f"{JPGSTORE_URL}/asset/{marketplace_id}"

def link_asset_to_marketplace(number: str, marketplace_id: str, marketplace: str) -> str:
    url = get_url_from_marketplace_id(marketplace_id, marketplace)
    return f" [#{str(number).zfill(5)}]({url}) "

def link_assets_to_grid(numbers, cols):
    assets_str = ""

    for i, number in enumerate(numbers):
        link = get_unsig_url(str(number))
        assets_str += f" [#{str(number).zfill(5)}]({link}) "

        if (i+1) % cols == 0:
            assets_str += f"\n"

    return assets_str

def unsig_exists(number: str) -> bool:
    try:
        if int(number) <= MAX_AMOUNT and int(number) >= 0:
            return True
        else:
            return False
    except:
        return False

def parse_sale(sale_data: dict) -> tuple:
    marketplace_name = sale_data.get("assetid")

    num_props = sale_data.get("num_props")

    price = sale_data.get("price", None)
    if price:
        price = price/1000000

    timestamp_ms = sale_data.get("date")
    if timestamp_ms:
        date = datetime.utcfromtimestamp(timestamp_ms/1000).strftime("%Y-%m-%d %H:%M:%S UTC")
    else:
        date = None
    
    return (marketplace_name, num_props, price, date)

def add_num_props(assets: list) -> list:
    unsigs = load_json(f"{ROOT_DIR}/json/unsigs.json")

    for asset in assets:
        asset_name = asset.get("assetid")
        idx = get_idx_from_asset_name(asset_name)

        unsigs_data = unsigs.get(str(idx))
        asset["num_props"] = unsigs_data.get("num_props")
    
    return assets
