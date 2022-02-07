"""
Module for aggregating data of marketplaces
"""
from typing import Optional

from unsigned_bot.log import logger
import unsigned_bot.marketplaces.cnft as cnft
import unsigned_bot.marketplaces.tokhun as tokhun
import unsigned_bot.marketplaces.jpgstore as jpgstore
from unsigned_bot.constants import POLICY_ID


async def aggregate_data_from_marketplaces(sold: Optional[bool] = False) -> list:
    """Fetch assets data from available marketplaces"""

    data = list()

    # === cnft.io ==
    try:
        assets_cnft = await cnft.fetch_data_from_marketplace("unsigned_algorithms", sold)
    except:
        logger.warning("Can not fetch data from cnft.io")
    else:
        if assets_cnft:
            data.extend(assets_cnft)

    # === Tokhun.io ===
    try:
        assets_tokhun = await tokhun.get_data_from_marketplace(POLICY_ID, sold)
    except:
        logger.warning(f"Can not fetch data from tokhun.io")
    else:
        if assets_tokhun:
            data.extend(assets_tokhun)
    
    # === jpg.store ===
    try:
        assets_jpg = await jpgstore.get_data_from_marketplace(POLICY_ID, sold)
    except:
        logger.warning(f"Can not fetch data from jpg.store")
    else:
        if assets_jpg:
            data.extend(assets_jpg)

    return data