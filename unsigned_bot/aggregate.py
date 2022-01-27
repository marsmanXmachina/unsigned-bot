"""
Module for aggregating data of marketplaces
"""

from unsigned_bot.marketplaces.cnft import fetch_data_from_marketplace
from unsigned_bot.marketplaces.tokhun import get_data_from_marketplace
import unsigned_bot.marketplaces.jpgstore as jpgstore
from unsigned_bot.constants import POLICY_ID


async def aggregate_data_from_marketplaces(sold=False):
    data = list()

    try:
        assets_cnft = await fetch_data_from_marketplace("unsigned_algorithms", sold)
    except:
        print(f"Can not fetch data from cnft.io")
    else:
        if assets_cnft:
            data.extend(assets_cnft)

    try:
        assets_tokhun = await get_data_from_marketplace(POLICY_ID, sold)
    except:
        print(f"Can not fetch data from tokhun.io")
    else:
        if assets_tokhun:
            data.extend(assets_tokhun)
    
    try:
        assets_jpg = await jpgstore.get_data_from_marketplace(POLICY_ID, sold)
    except:
        print(f"Can not fetch data from jpg.store")
    else:
        if assets_jpg:
            data.extend(assets_jpg)

    return data


