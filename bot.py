import os
import math
import re
import json
import time
import pytz
from datetime import datetime
import asyncio

from operator import itemgetter
from collections import defaultdict

from files_util import load_json, save_json

import aiohttp

import requests
from requests_html import HTMLSession, AsyncHTMLSession

import discord
from discord.ext import commands
from discord.ext.tasks import loop

from discord_slash import SlashCommand, SlashContext
from discord_slash.context import ComponentContext
from discord_slash.utils.manage_commands import create_choice, create_option

from draw import gen_evolution, gen_grid, delete_image_files

from fetch import fetch_data_from_marketplace

INVERVAL_LOOP=900

from dotenv import load_dotenv
load_dotenv() 

FILE_DIR = os.path.dirname(os.path.abspath(__file__))
IMAGE_PATH = f"{FILE_DIR}/img"

TOKEN = os.getenv('BOT_TOKEN')
POLICY_ID = os.getenv('POLICY_ID')
SALES_CHANNEL=os.getenv('SALES_CHANNEL')
SALES_CHANNEL_ID = int(os.getenv('SALES_CHANNEL_ID'))
GUILD_NAME = os.getenv('GUILD_NAME')
GUILD_ID = os.getenv('GUILD_ID')

GUILD_IDS=[int(GUILD_ID)]

DISCORD_API_URL = "https://discord/api/v9"

CARDANOSCAN_URL = "https://cardanoscan.io"
BLOCKFROST_IPFS_URL = "https://ipfs.blockfrost.dev/ipfs"
POOL_PM_URL= "https://pool.pm"
CNFT_URL = "https://cnft.io"
CNFT_API_URL = "https://api.cnft.io/market/listings"

UNSIGS_URL = "https://www.unsigs.com"

MARKETPLACES = {
    "CNFT.IO": "https://cnft.io/marketplace.php?s=0e14267a8020229adc0184dd25fa3174c3f7d6caadcb4425c70e7c04",
    "Tokhun.io": "https://tokhun.io/marketplace?verifiedPolicyId=yes&project%5B%5D=347&minPrice=&maxPrice=&sortBy=Newest+First&page=1"
}

DISCORD_ESCROWS = {
    "Flowers for Lovelace": "https://discord.gg/P2Dssm9at2",
    "CNFT": "https://discord.gg/jpxXxMr8Dg",
    "CardanoNFT": "https://discord.gg/mWDTRdDMVk",
    "The Hoskinsons": "https://discord.gg/UvFyfsMgfP"
}

MAX_AMOUNT = 31118

EMOJI_FRAME="\U0001F5BC"
EMOJI_RAINBOW = "\U0001F308"
EMOJI_BARCHART = "\U0001F4CA"
EMOJI_CIRCLE_ARROWS = "\U0001F504"
EMOJI_GEAR = "\u2699"
EMOJI_CART = "\U0001F6D2"
EMOJI_MONEYBACK = "\U0001F4B0"
EMOJI_CALENDAR = "\U0001F4C5"
EMOJI_SHOPPINGBAGS = "\U0001F6CD"
EMOJI_PERSON = "\U0001F464"
EMOJI_NUMBERS = "\U0001F522"
EMOJI_PALETTE = "\U0001F3A8"
EMOJI_ARROW_DOWN = "\u2B07"
EMOJI_ARROW_RIGHT = "\u27A1"
EMOJI_PARTY = "\U0001F389"
EMOJI_WARNING = "\u26A0"
EMOJI_ROBOT = "\U0001F916"
EMOJI_BROOM = "\U0001F9F9"
EMOJI_MONEYWINGS = "\U0001F4B8"

DISCORD_COLOR_CODES = {
    "blue": "ini",
    "red": "diff",
    "green": "bash"  
}

INVERVALS_IN_DAYS = {
    "day": 1,
    "week": 7,
    "month": 30,
}

async def get_sales_data(policy_id) -> list:
    """Get data of sold pioneers from cnft.io marketplace"""

    sales = list()

    url = "https://api.cnft.io/market/listings"

    payload = {
        "search": policy_id,
        "sort": "date",
        "order": "desc",
        "page": 1,
        "verified": "true",
        "sold": "true",
        "count": 200
    }

    total_amount = None
    next_page = True
    while next_page:
        
        try:
            response = requests.post(url, payload).json()
        except:
            return sales
        else:

            if isinstance(response, dict):
                if not total_amount:
                    total_amount = response.get('found')

                assets = response.get('assets')
            else:
                return sales
            
            if assets:
                sales.extend(assets)
            else:
                next_page = False

            print(f"{len(assets)} assets found on sales page {payload['page']}")
            payload["page"] += 1

    return sales
    

def extract_sales_data(assets_data):
    sales_data = list()

    for asset in assets_data:
        sales_data.append({
            "assetid": asset.get("metadata").get("name"),
            "date": asset.get("dateSold"),
            "unit": asset.get("unit"),
            "price": asset.get("price")
        })
    
    return sales_data

def get_asset_id(asset_name) -> str:
    asset_ids = load_json("json/asset_ids.json")
    return asset_ids.get(asset_name, None)

def get_asset_name_from_idx(idx: str):
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

def get_asset_name_from_minting_order(idx:str):
    minting_order = load_json("json/minted.json")
    try:
        idx = int(idx)
        asset_name = minting_order[idx-1]
    except:
        return
    else:
        return asset_name

async def get_ipfs_url(asset_id, asset_name):
    metadata = await get_metadata(asset_id)
    if metadata:
        ipfs_hash = get_ipfs_hash(metadata, asset_id, asset_name)
        if ipfs_hash:
            ipfs_url = f"{BLOCKFROST_IPFS_URL}/{ipfs_hash}"
            return ipfs_url

async def get_ipfs_url_from_file(asset_name):
    ipfs_urls = load_json("json/ipfs_urls.json")
    return ipfs_urls.get(asset_name, None)
    
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

def get_ipfs_hash(metadata, asset_id, asset_name):
    try:
        image_url = metadata.get(POLICY_ID).get(asset_name).get("image", None)
    except:
        return
    else:
        if image_url:   
            return image_url.rsplit("/")[-1]

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


def unsig_exists(number: str) -> bool:
    try:
        if int(number) <= MAX_AMOUNT and int(number) >= 0:
            return True
        else:
            return False
    except:
        return False

def get_interval_from_period(period):

    INVERVALS_IN_DAYS = {
        "day": 1,
        "week": 7,
        "month": 30
    }

    interval = INVERVALS_IN_DAYS.get(period)
    if interval:
        return interval * 24 * 3600 * 1000
    else:
        return 0

def filter_by_time_interval(assets: list, interval_ms) -> list:
    timestamp_now = round(time.time() * 1000)
    
    filtered = list()
    for asset in assets:
        timestamp = asset.get("date")
        if timestamp >= (timestamp_now - interval_ms):
            filtered.append(asset)

    return filtered

def timestamp_to_datetime(timestamp_ms):
    dt = datetime.utcfromtimestamp(timestamp_ms/1000)
    return dt

def filter_sales_by_asset(sales, asset_name):
    return [sale for sale in sales if sale.get("assetid").replace("_","") == asset_name]

def sort_sales_by_date(sales, descending=False):
    return sorted(sales, key=itemgetter('date'), reverse=descending)

def filter_new_sales(past_sales, new_sales):
    return [sale for sale in new_sales if sale not in past_sales]

def filter_available_assets(assets):
    return [asset for asset in assets if not asset.get("reserved")]

def get_unsig_url(number: str):
    return f"{UNSIGS_URL}/details/{number.zfill(5)}"

def get_numbers_from_string(string):
    return re.findall(r"\d+", string)

def order_by_num_props(assets: list) -> dict:
    ordered = defaultdict(list)

    for asset in assets:
        num_props = asset.get("num_props")
        ordered[num_props].append(asset)

    return ordered

def get_min_prices(assets: list) -> list:
    min_price = min([asset.get("price") for asset in assets])
    return [asset for asset in assets if asset.get("price") == min_price]

def get_average_price(assets: list) -> float:
    num_assets = len(assets) 
    return sum_prices(assets)/num_assets if num_assets else 0  

def sum_prices(assets: list) -> float:
    return sum([asset.get("price") for asset in assets])

def get_url_from_marketplace_id(marketplace_id: str) -> str:
    return f"https://cnft.io/token.php?id={marketplace_id}"



bot = commands.Bot(command_prefix='!', help_command=None)
bot.sales = load_json("json/sales.json")
bot.sales_updated = None
bot.offers = None
bot.offers_updated = None

slash = SlashCommand(bot, sync_commands=True)

@bot.event
async def on_ready():
    if not fetch_data.is_running():
        fetch_data.start()
    

    print("guilds", bot.guilds)

    bot.guild = discord.utils.find(lambda g: g.name == GUILD_NAME, bot.guilds)

    if bot.guild:
        print(
            f'{bot.user} is connected to the following guild:\n'
            f'{bot.guild.name}(id: {bot.guild.id})'
        )

    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name='unsigned_algorithms'))

def embed_minting_order(embed, minting_data):
    minting_order, minting_time = minting_data
    dt = timestamp_to_datetime(minting_time)

    embed.add_field(name=f"{EMOJI_NUMBERS} Minting order", value=f"`{minting_order}/{MAX_AMOUNT+1}` ({dt.date()})", inline=False)

def add_sales(embed, sales):

    sales_value=""

    for sale in sales:
        price = sale.get('price')/1000000
        timestamp_ms = sale.get('date')
        date = timestamp_to_datetime(timestamp_ms).date()

        row = f"sold on **{date}** for **₳{price:,.0f}**\n"
        sales_value += row

    embed.add_field(name=f"{EMOJI_SHOPPINGBAGS} Past sales", value=sales_value, inline=False)

def embed_num_props(embed, unsigs_data):
    total_props = unsigs_data.get("num_props")
    embed.add_field(name="Total properties", value=f"This unsig has **{total_props}** properties", inline=False)

def embed_props(embed, unsigs_data):
    properties = unsigs_data.get("properties")

    colors = properties.get("colors")
    multipliers = properties.get("multipliers")
    distributions = properties.get("distributions")
    rotations = properties.get("rotations")
    
    colors_str = ", ".join([c for c in colors])
    embed.add_field(name=f"{EMOJI_RAINBOW} Colors {EMOJI_RAINBOW}", value=f"`{colors_str}`", inline=False)

    multipliers_str = ", ".join([str(m) for m in multipliers])
    embed.add_field(name=f"{EMOJI_GEAR} Multipliers {EMOJI_GEAR}", value=f"`{multipliers_str}`", inline=False)

    distributions_str = ", ".join([d for d in distributions])
    embed.add_field(name=f"{EMOJI_BARCHART} Distributions {EMOJI_BARCHART}", value=f"`{distributions_str}`", inline=False)

    rotations_str = ", ".join([str(r) for r in rotations])
    embed.add_field(name=f"{EMOJI_CIRCLE_ARROWS} Rotations {EMOJI_CIRCLE_ARROWS}", value=f"`{rotations_str}`", inline=False)


def embed_subpattern(embed, number:str):
    try:
        unsigs_subpattern = load_json("json/subpattern.json")
    except:
        print("Can not open subpatterns.")
    else:
        subpattern = unsigs_subpattern.get(number, None)
        if subpattern:
            subpattern_str = ""
            for i, pattern in enumerate(reversed(subpattern)):
                if not pattern:
                    row = f"{i+1}. ` - `\n"
                else:
                    unsig_url = get_unsig_url(str(pattern))
                    pattern = str(pattern).zfill(5)
                    row = f"{i+1}. [#{pattern}]({unsig_url})\n"

                
                subpattern_str += row
            
            embed.add_field(name=f"{EMOJI_ARROW_DOWN} Top to Bottom {EMOJI_ARROW_DOWN}", value=subpattern_str, inline=False)

def add_disclaimer(embed, last_update):
    last_update = last_update.strftime("%Y-%m-%d %H:%M:%S UTC")
    embed.set_footer(text=f"The server has no affiliation with the marketplace nor listed prices.\n\nData comes from https://cnft.io\nLast update: {last_update}")

def add_data_source(embed, last_update):
    last_update = last_update.strftime("%Y-%m-%d %H:%M:%S UTC")
    embed.set_footer(text=f"Data comes from https://cnft.io\nLast update: {last_update}")

def add_policy(embed):
    embed.add_field(name = f"\u26A0 Watch out for fake items and always check the policy id \u26A0", value=f"`{POLICY_ID}`", inline=False)

def embed_marketplaces():
    title = f"{EMOJI_SHOPPINGBAGS} Where to buy? {EMOJI_SHOPPINGBAGS}"
    description="Places to buy your first unsig..."
    color=discord.Colour.dark_blue()

    embed = discord.Embed(title=title, description=description, color=color)

    marketplaces_str = ""
    for marketplace, marketplace_url in MARKETPLACES.items():
        marketplace_str = f"{EMOJI_ARROW_RIGHT} [{marketplace}]({marketplace_url})\n"
        marketplaces_str += marketplace_str

    embed.add_field(name=f"Marketplaces", value=marketplaces_str, inline=False)

    escrows_str = ""
    for escrow, escrow_url in DISCORD_ESCROWS.items():
        escrow_str = f"{EMOJI_ARROW_RIGHT} [{escrow}]({escrow_url})\n"
        escrows_str += escrow_str

    embed.add_field(name=f"Escrows on discord server", value=escrows_str, inline=False)

    embed.set_footer(text=f"The server has no affiliation with the marketplace nor listed prices.\n\nAlways check policy id:\n{POLICY_ID}")

    return embed

def embed_policy():
    title = f"{EMOJI_WARNING} Unsigs Policy ID {EMOJI_WARNING}"
    description="The official one and only..."
    color=discord.Colour.orange()

    embed = discord.Embed(title=title, description=description, color=color)
    embed.add_field(name=f"Always check the policy ID", value=f"`{POLICY_ID}`", inline=False)

    return embed


def embed_offers(assets_ordered: dict):
    title = f"{EMOJI_BROOM} Unsigs Floor {EMOJI_BROOM}"
    description="Cheapest unsigs on marketplace"
    color=discord.Colour.dark_blue()

    embed = discord.Embed(title=title, description=description, color=color)

    for idx in range(7):

        assets = assets_ordered.get(idx, None)
        
        if assets:
            num_assets = len(assets)
            offers_str=""
            low_priced_assets = get_min_prices(assets)

            min_price = None
            for asset in low_priced_assets:
                min_price = asset.get("price")/1000000
                asset_name = asset.get("assetid")
                number = asset_name.replace("unsig_", "")
                marketplace_id = asset.get("id")
                offers_str += f" [#{number.zfill(5)}]({get_url_from_marketplace_id(marketplace_id)}) "
            
            offers_str += f"for **₳{min_price:,.0f}** (out of {num_assets})\n"
        else:
            offers_str = "` - `"
            num_assets = 0
        
        embed.add_field(name=f"**{idx} props**", value=offers_str, inline=False)

    return embed

def embed_sales(assets, prices_type, period):

    num_assets = len(assets)

    ordered = order_by_num_props(assets)
    if not period:
        period_str = "all-time"
    else:
        period_str = f"last {period}"

    if prices_type == "highest":
        title = f"{EMOJI_MONEYWINGS} Highest sales {period_str} {EMOJI_MONEYWINGS}"
    else:
        title = f"{EMOJI_CART} Average sales {period_str} {EMOJI_CART}"
        
    description=f"**{num_assets}** sold on marketplace"
    color=discord.Colour.dark_blue()

    embed = discord.Embed(title=title, description=description, color=color)


    for idx in range(7):
        assets_props = ordered.get(idx, None)

        if assets_props:
            sales_str = ""
            num_sold_props = len(assets_props)

            if prices_type == "highest":
                sorted_by_price = sorted(assets_props, key=lambda x:x['price'], reverse=True)
                
                for j in range(3):
                    max_priced = sorted_by_price[j]
                    price = max_priced.get("price")/1000000
                    name = max_priced.get("assetid")
                    number = name.replace("unsig_", "")
                    timestamp_ms = max_priced.get("date")
                    dt = timestamp_to_datetime(timestamp_ms)

                    sales_str += f"[#{number}]({get_unsig_url(number)}) sold for **₳{price:,.0f}** on {dt.date()}\n"
            else:
                average_price = get_average_price(assets_props)/1000000
                sales_str = f"**{num_sold_props}** sold for **\u2300 ₳{average_price:,.0f}**"

        else:
            sales_str = "` - `"

        embed.add_field(name=f"**{idx} props**", value=sales_str, inline=False)

    return embed


# @slash.slash(
#     name="fund", 
#     description="message to raise funds", 
#     guild_ids=GUILD_IDS
# )
# async def fund(ctx: SlashContext):
        
#     title = f"\U0001F378 Unsigned, not stirred \U0001F378"
#     description="My name is 007. unsig007. What's next? You decide..."
#     color=discord.Colour.dark_blue()

#     embed = discord.Embed(title=title, description=description, color=color)

#     embed.add_field(name="Vote for the next task with emoji number", value="You can vote for multiple tasks", inline=False)
#     embed.add_field(name="Task \u0031", value="Feed twitter with unsigs", inline=False)
#     embed.add_field(name="Task \u0032", value="Alert if #unsig for sale", inline=False)
#     embed.add_field(name="Task \u0033", value="Notification if potential buyer for own unsig", inline=False)
#     embed.add_field(name="Task \u0034", value="Data feed from marketplace, e.g. floor prices", inline=False)

#     embed.set_footer(text=f"\nDon't forget to put some ₳ in my pockets!")
    
#     await ctx.send(embed=embed)

# @slash.slash(
#     name="firework", 
#     description="A new era begins...", 
#     guild_ids=GUILD_IDS
# )
# async def firework(ctx: SlashContext):
#     title = f"{EMOJI_PARTY} Quantum of Alonzo {EMOJI_PARTY}"
#     description="A new era begins..."
#     color=discord.Colour.purple()

#     embed = discord.Embed(title=title, description=description, color=color)

#     embed.set_image(url="https://media.giphy.com/media/26tOZ42Mg6pbTUPHW/giphy.gif")

#     await ctx.send(embed=embed)


@slash.slash(
    name="faq", 
    description="Everything you should know about unsigs", 
    guild_ids=GUILD_IDS,
    options=[
        create_option(
            name="topics",
            description="Choose topic",
            required=True,
            option_type=3,
            choices=[
                create_choice(
                    name="Where to buy?",
                    value="buy_unsig"
                ),
                create_choice(
                    name="Policy ID",
                    value="policy_id"
                )
            ]
        )
    ]
)
async def faq(ctx: SlashContext, topics: str):
    if not topics:
        await ctx.send(content=f"Please choose a topic...")
        return
    else:
        if topics == "buy_unsig":
            embed = embed_marketplaces()

        if topics == "policy_id":
            embed = embed_policy()
        
        await ctx.send(embed=embed)

@slash.slash(
    name="help", 
    description="Get overview of my commands", 
    guild_ids=GUILD_IDS,
)
async def help(ctx: SlashContext):
    title = f"{EMOJI_ROBOT} My commands {EMOJI_ROBOT}"
    description="How can I help you?"
    color=discord.Colour.dark_blue()

    embed = discord.Embed(title=title, description=description, color=color) 

    embed.add_field(name="/faq", value="show important information", inline=False)
    embed.add_field(name="/unsig + `integer`", value="show unsig with given number", inline=False)
    embed.add_field(name="/minted + `integer`", value="show unsig with given minting order", inline=False)
    embed.add_field(name="/evo + `integer`", value="show composition of your unsig", inline=False)
    embed.add_field(name="/invo + `integer`", value="show ingredients of your unsig", inline=False)
    embed.add_field(name="/owner + `integer`", value="show wallet of given unsig", inline=False)
    embed.add_field(name="/sell + `integer` + `price`", value="offer your unsig for sale", inline=False)
    embed.add_field(name="/show + `numbers`", value="show your unsig collection", inline=False)
    embed.add_field(name="/floor", value="show cheapest unsigs on marketplace", inline=False)
    embed.add_field(name="/sales", value="show data of sold unsigs on marketplace", inline=False)
    
    await ctx.send(embed=embed)



@slash.slash(
    name="sales", 
    description="show data of sold unsigs on marketplace", 
    guild_ids=GUILD_IDS,
    options=[
        create_option(
            name="prices",
            description="type of price data",
            required=False,
            option_type=3,
            choices=[
                create_choice(
                    name="average prices",
                    value="average"
                ),
                create_choice(
                    name="top sales",
                    value="highest"
                )
            ]
        ),
        create_option(
            name="period",
            description="period of sales",
            required=False,
            option_type=3,
            choices=[
                create_choice(
                    name="last day",
                    value="day"
                ),
                create_choice(
                    name="last week",
                    value="week"
                ),
                create_choice(
                    name="last month",
                    value="month"
                )
            ]
        )
    ]
)
async def sales(ctx: SlashContext, prices=None, period=None):
        
    if ctx.channel.name == "general":
        await ctx.send(content=f"I'm not allowed to post here.\n Please go to #bot channel.")
        return

    if bot.sales:

        if period:
            interval_ms = get_interval_from_period(period)
            if not interval_ms:
                await ctx.send(content=f"Please enter a valid time period!")
                return
            else:
                filtered= filter_by_time_interval(bot.sales, interval_ms)
        else: 
            filtered = bot.sales

        embed = embed_sales(filtered, prices, period)

        add_data_source(embed, bot.sales_updated)

        await ctx.send(embed=embed)
    else:
        await ctx.send(content=f"Currently no sales data available...")
        return
       

@slash.slash(
    name="floor", 
    description="show cheapest unsigs on marketplace", 
    guild_ids=GUILD_IDS
)
async def floor(ctx: SlashContext):
        
    if ctx.channel.name == "general":
        await ctx.send(content=f"I'm not allowed to post here.\n Please go to #bot channel.")
        return
    
    if bot.offers:
        for_sale = filter_available_assets(bot.offers)
        ordered_by_props = order_by_num_props(for_sale)

        embed = embed_offers(ordered_by_props)

        add_policy(embed)

        add_disclaimer(embed, bot.offers_updated)

        await ctx.send(embed=embed)
    else:
        await ctx.send(content=f"Currently no marketplace data available...")
        return


@slash.slash(
    name="sell", 
    description="offer your unsig for sale", 
    guild_ids=GUILD_IDS,
    options=[
        create_option(
            name="number",
            description="number unsig you want to sell",
            required=True,
            option_type=3,
        ),
        create_option(
            name="price",
            description="price you want to sell",
            required=True,
            option_type=3,
        )
    ]
)
async def sell(ctx: SlashContext, number: str, price: str):
    SELLING_CHANNEL = "selling"
    if ctx.channel.name != SELLING_CHANNEL:
        await ctx.send(content=f"Please post your offer in the #{SELLING_CHANNEL} channel.")
        return
        
    asset_name = get_asset_name_from_idx(number)

    if not unsig_exists(number):
        await ctx.send(content=f"{asset_name} does not exist!\nPlease enter number between 0 and {MAX_AMOUNT}.")
    else:
        asset_id = get_asset_id(asset_name)

        number = str(int(number))

        unsigs_data = get_unsigs_data(number)

        minting_data = get_minting_data(number)

        title = f"{EMOJI_SHOPPINGBAGS} {asset_name} for sale {EMOJI_SHOPPINGBAGS}"
        description="Are you interested in this beautiful unsig?"
        color=discord.Colour.dark_blue()

        embed = discord.Embed(title=title, description=description, color=color)

        embed.add_field(name=f"{EMOJI_PERSON} Seller", value=ctx.author.name, inline=False)

        if not price:
            price_str = "???"
        else:
            try:
                price = float(price)
            except:
                await ctx.send(content=f"Please enter price for sale!")
                return
            else:
                price_str = f"₳{price:,.0f}"

        embed.add_field(name=f"{EMOJI_MONEYBACK} Price", value=price_str, inline=True)

        embed_minting_order(embed, minting_data)

        embed_num_props(embed, unsigs_data)

        image_url = await get_ipfs_url_from_file(asset_name)
        if image_url:
            embed.set_image(url=image_url)

        embed.set_footer(text=f"\nAlways check policy id:\n{POLICY_ID}")
 
        await ctx.send(embed=embed)

@slash.slash(
    name="unsig", 
    description="show unsig with given number", 
    guild_ids=GUILD_IDS,
    options=[
        create_option(
            name="number",
            description="Number of your unsig",
            required=True,
            option_type=3,
        ),
    ]
)
async def unsig(ctx: SlashContext, number: str):
        
    if ctx.channel.name == "general":
        await ctx.send(content=f"I'm not allowed to post here.\n Please go to #bot channel.")
        return


    asset_name = get_asset_name_from_idx(number)

    if not unsig_exists(number):
        await ctx.send(content=f"{asset_name} does not exist!\nPlease enter number between 0 and {MAX_AMOUNT}.")
    else:
        asset_id = get_asset_id(asset_name)

        number = str(int(number))

        unsigs_data = get_unsigs_data(number)

        minting_data = get_minting_data(number)

        unsig_url = get_unsig_url(number)

        title = f"{asset_name}"
        description="minted by unsigned_algorithms"
        color=discord.Colour.dark_blue()

        embed = discord.Embed(title=title, description=description, color=color, url=unsig_url)

        embed_minting_order(embed, minting_data)
       
        if bot.sales:
            past_sales = filter_sales_by_asset(bot.sales, asset_name)
            sales_by_date = sort_sales_by_date(past_sales, descending=True)

            if past_sales:
                add_sales(embed, sales_by_date)

        embed_num_props(embed, unsigs_data)

        embed_props(embed, unsigs_data)

        image_url = await get_ipfs_url_from_file(asset_name)

        if image_url:
            embed.set_image(url=image_url)


        embed.set_footer(text=f"\nAlways check policy id:\n{POLICY_ID}")
 
        await ctx.send(embed=embed)

@slash.slash(
    name="show", 
    description="show collection of your unsigs", 
    guild_ids=GUILD_IDS,
    options=[
        create_option(
            name="numbers",
            description="Numbers of your unsigs",
            required=True,
            option_type=3,
        ),
        create_option(
            name="columns",
            description="no. of unsigs side by side",
            required=False,
            option_type=3,
        ),
    ]
)
async def show(ctx: SlashContext, numbers: str, columns: str = None):
        
    if ctx.channel.name == "general":
        await ctx.send(content=f"I'm not allowed to post here.\n Please go to #bot channel.")
        return

    unsig_numbers = get_numbers_from_string(numbers)
    
    if not unsig_numbers:
        await ctx.send(content=f"Please enter numbers for your unsigs")
        return

    numbers_cleaned = list()
    for number in unsig_numbers:
        try:
            number = str(int(number))
        except:
            await ctx.send(content=f"unsig{number} does not exist!\nPlease enter number between 0 and {MAX_AMOUNT}.")
            return
        else:
            numbers_cleaned.append(number)
    
    if not columns:
        columns = math.ceil(math.sqrt(len(numbers_cleaned)))
    else:
        try:
            columns = int(columns)
        except:
            await ctx.send(content=f"Please enter the number of unsigs displayed sidy by side")
            return

    
    title = f"{EMOJI_FRAME} Your collection {EMOJI_FRAME}"
    description="Look at this beautiful collection of unsigs..."
    color=discord.Colour.dark_blue()

    embed = discord.Embed(title=title, description=description, color=color)

    collection_str=" "
    unsigs_links = [f"[#{num.zfill(5)}]({get_unsig_url(num)})" for num in numbers_cleaned]

    for i, link in enumerate(unsigs_links):
        collection_str += f" {link}"
        if (i+1) % columns == 0:
            collection_str += f"\n"

    embed.add_field(name=f"{EMOJI_ARROW_DOWN} Top to Bottom {EMOJI_ARROW_DOWN}", value=collection_str, inline=False)

    try:
        image_path = f"img/grid_{''.join(numbers_cleaned)}.png"
        
        await gen_grid(numbers_cleaned, columns)

        image_file = discord.File(image_path, filename="grid.png")
        if image_file:
            embed.set_image(url="attachment://grid.png")
        delete_image_files(IMAGE_PATH)
    except:
        await ctx.send(content=f"I can't generate the collection of your unsig.")
        return
    else:
        await ctx.send(file=image_file, embed=embed)

    

@slash.slash(
    name="invo", 
    description="show ingredients of unsig with given number", 
    guild_ids=GUILD_IDS,
    options=[
        create_option(
            name="number",
            description="Number of your unsig",
            required=True,
            option_type=3,
        )
    ]
)
async def invo(ctx: SlashContext, number: str):
        
    if ctx.channel.name == "general":
        await ctx.send(content=f"I'm not allowed to post here.\n Please go to #bot channel.")
        return

    asset_name = get_asset_name_from_idx(number)

    if not unsig_exists(number):
        await ctx.send(content=f"{asset_name} does not exist!\nPlease enter number between 0 and {MAX_AMOUNT}.")
    else:

        number = str(int(number))

        title = f"{EMOJI_PALETTE} {asset_name} {EMOJI_PALETTE}"
        description="Explore the ingredients of your unsig..."
        color=discord.Colour.dark_blue()

        embed = discord.Embed(title=title, description=description, color=color)

        try:
            image_path = f"img/evolution_{number}.png"
            
            await gen_evolution(number, show_single_layers=True)

            image_file = discord.File(image_path, filename="image.png")
            if image_file:
                embed.set_image(url="attachment://image.png")
            delete_image_files(IMAGE_PATH)
        except:
            await ctx.send(content=f"I can't generate the ingredients of your unsig.")
            return
        else:
            await ctx.send(file=image_file, embed=embed)

@slash.slash(
    name="evo", 
    description="show composition of unsig with given number", 
    guild_ids=GUILD_IDS,
    options=[
        create_option(
            name="number",
            description="Number of your unsig",
            required=True,
            option_type=3,
        ),
        create_option(
            name="extended",
            description="show ingredient layers",
            required=False,
            option_type=3,
            choices=[
                create_choice(
                    name="show ingredients",
                    value="extended"
                )
            ]
        )
    ]
)
async def evo(ctx: SlashContext, number: str, extended=False):
        
    if ctx.channel.name == "general":
        await ctx.send(content=f"I'm not allowed to post here.\n Please go to #bot channel.")
        return

    asset_name = get_asset_name_from_idx(number)

    if not unsig_exists(number):
        await ctx.send(content=f"{asset_name} does not exist!\nPlease enter number between 0 and {MAX_AMOUNT}.")
    else:

        number = str(int(number))

        title = f"{EMOJI_PALETTE} {asset_name} {EMOJI_PALETTE}"
        description="Explore the composition of your unsig..."
        color=discord.Colour.dark_blue()

        embed = discord.Embed(title=title, description=description, color=color)

        embed_subpattern(embed, number)

        try:
            image_path = f"img/evolution_{number}.png"
            
            if extended == "extended":
                extended = True
            else:
                extended = False

            await gen_evolution(number, show_single_layers=False, extended=extended)

            image_file = discord.File(image_path, filename="image.png")
            if image_file:
                embed.set_image(url="attachment://image.png")
            delete_image_files(IMAGE_PATH)
        except:
             await ctx.send(content=f"I can't generate the composition of your unsig.")
             return
        else:
            await ctx.send(file=image_file, embed=embed)

@slash.slash(
    name="minted", 
    description="show unsig with given minting order", 
    guild_ids=GUILD_IDS,
    options=[
        create_option(
            name="index",
            description="position of minting order",
            required=True,
            option_type=3,
        )
    ]
)
async def minted(ctx: SlashContext, index: str):
        
    if ctx.channel.name == "general":
        await ctx.send(content=f"I'm not allowed to post here.\n Please go to #bot channel.")
        return
        
    asset_name = get_asset_name_from_minting_order(index)

    if not asset_name:
        await ctx.send(content=f"Unsig with minting order {index} does not exist!\nPlease enter number between 1 and {MAX_AMOUNT+1}.")
    else:
        asset_id = get_asset_id(asset_name)

        number = str(get_idx_from_asset_name(asset_name))
        unsig_url = get_unsig_url(number)

        unsigs_data = get_unsigs_data(number)
      
        minting_data = get_minting_data(number)

        title = f"{asset_name}"
        description="minted by unsigned_algorithms"
        color=discord.Colour.dark_blue()

        embed = discord.Embed(title=title, description=description, color=color, url=unsig_url)

        embed_minting_order(embed, minting_data)
       
        if bot.sales:
            past_sales = filter_sales_by_asset(bot.sales, asset_name)
            sales_by_date = sort_sales_by_date(past_sales, descending=True)

            if past_sales:
                add_sales(embed, sales_by_date)

        embed_num_props(embed, unsigs_data)

        embed_props(embed, unsigs_data)

        image_url = await get_ipfs_url_from_file(asset_name)

        if image_url:
            embed.set_image(url=image_url)


        embed.set_footer(text=f"\nAlways check policy id:\n{POLICY_ID}")
 
        await ctx.send(embed=embed)

@slash.slash(
    name="owner", 
    description="show wallet of unsig with given number", 
    guild_ids=GUILD_IDS,
    options=[
        create_option(
            name="number",
            description="Number of your unsig",
            required=True,
            option_type=3,
        )
    ]
)
async def owner(ctx: SlashContext, number: str):

    if ctx.channel.name == "general":
        await ctx.send(content=f"I'm not allowed to post here.\n Please go to #bot channel.")
        return 

    asset_name = get_asset_name_from_idx(number)

    if not unsig_exists(number):
        await ctx.send(content=f"{asset_name} does not exist!\nPlease enter number between 0 and {MAX_AMOUNT}.")
    else:
        asset_id = get_asset_id(asset_name)

        owner_address_data = get_current_owner_address(asset_id)
        if owner_address_data:
            address = owner_address_data.get("name")

            title = f"{asset_name} is owned by"
            description = f"`{address}`"
            color = discord.Colour.blurple()

            embed = discord.Embed(title=title, description=description, color=color)

            name = "This address belongs to wallet..."
            value = f"{POOL_PM_URL}/{address}/0e14267a"
            embed.add_field(name=name, value=value, inline=False)

            embed.set_footer(text=f"Data comes from {POOL_PM_URL}")

            await ctx.send(embed=embed)
        else:
            await ctx.send(content=f"Sorry...I can't get the data for `{asset_name}` at the moment!")

async def post_sales(sales):
    try:
        channel = bot.get_channel(SALES_CHANNEL_ID)
    except:
        print(f"Can't find the sales feed channel")
    else:
        for sale_data in sales:
            marketplace_name = sale_data.get("assetid")
            asset_name = marketplace_name.replace("_", "")
            asset_id = get_asset_id(asset_name)

            price = sale_data.get("price")
            price = price/1000000
            timestamp_ms = sale_data.get("date")
            date = datetime.utcfromtimestamp(timestamp_ms/1000).strftime("%Y-%m-%d %H:%M:%S UTC")

            title = f"{EMOJI_CART} {asset_name} {EMOJI_CART}"
            description="minted by unsigned_algorithms"
            color=discord.Colour.dark_blue()

            embed = discord.Embed(title=title, description=description, color=color)

            embed.add_field(name=f"{EMOJI_MONEYBACK} Price", value=f"₳{price:,.0f}", inline=True)
            embed.add_field(name=f"{EMOJI_CALENDAR} Sold on", value=date, inline=True)

            image_url = await get_ipfs_url_from_file(asset_name)

            if image_url:
                embed.set_image(url=image_url)

            embed.set_footer(text=f"Data comes from {CNFT_URL}")
            
            message = await channel.send(embed=embed)
            await message.publish()


async def get_last_messages(channel):
    last_messages = list()

    async for message in channel.history(limit=15):
        now = datetime.utcnow()
        time_diff = now - message.created_at
        time_diff_seconds = time_diff.total_seconds()
        
        if time_diff_seconds <= INVERVAL_LOOP:
            last_messages.append(message)
    
    return last_messages

async def publish_last_messages():
    channel = bot.get_channel(SALES_CHANNEL_ID)

    last_messages = await get_last_messages(channel)
    if last_messages:
        for message in last_messages:
            await message.publish()


@loop(seconds=INVERVAL_LOOP)
async def fetch_data():

    sales_data = await fetch_data_from_marketplace(CNFT_API_URL, POLICY_ID, sold=True)
    if sales_data:
        new_sales = filter_new_sales(bot.sales, sales_data)
        bot.sales_updated = datetime.utcnow()
        print("sales updated", bot.sales_updated)

        if new_sales:
            bot.sales.extend(new_sales)
            save_json("json/sales.json", bot.sales)
    
            new_sales = filter_by_time_interval(new_sales, INVERVAL_LOOP * 1000 * 4)

            await asyncio.sleep(2)
            await post_sales(new_sales)
    
    offers_data = await fetch_data_from_marketplace(CNFT_API_URL, POLICY_ID, sold=False)
    if offers_data:
        bot.offers = offers_data
        bot.offers_updated = datetime.utcnow()
 
    print("Updated:", datetime.now()) 


bot.run(TOKEN)