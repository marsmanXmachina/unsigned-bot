import os
import asyncio

from cnft import fetch_data_from_marketplace
from tokhun import get_data_from_marketplace
from urls import TOKHUN_API_URL, CNFT_API_URL

from utility.files_util import load_json, save_json
from utility.time_util import timestamp_to_datetime

from dotenv import load_dotenv
load_dotenv() 

POLICY_ID = os.getenv('POLICY_ID')


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


if __name__ == '__main__':
    total_assets = asyncio.run(aggregate_data_from_marketplaces(sold=True))

    save_json("json/total_sales.json", total_assets)


