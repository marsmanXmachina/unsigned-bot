"""
Module for aggregating data of marketplaces
"""

from unsigned_bot.marketplaces.cnft import fetch_data_from_marketplace
from unsigned_bot.marketplaces.tokhun import get_data_from_marketplace
from unsigned_bot.constants import POLICY_ID
from unsigned_bot.urls import TOKHUN_API_URL, CNFT_API_URL


async def aggregate_data_from_marketplaces(sold=False):
    data = list()

    try:
        assets_cnft = await fetch_data_from_marketplace(CNFT_API_URL, "unsigned_algorithms", sold)
    except:
        print(f"Can not fetch data from cnft.io")
    else:
        if assets_cnft:
            data.extend(assets_cnft)

    try:
        assets_tokhun = await get_data_from_marketplace(TOKHUN_API_URL, POLICY_ID, sold)
    except:
        print(f"Can not fetch data from tokhun.io")
    else:
        if assets_tokhun:
            data.extend(assets_tokhun)

    return data



