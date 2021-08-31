import os
import re
import json
import time
import pytz
from datetime import datetime
import asyncio

from operator import itemgetter

from files_util import load_json

import requests
from requests_html import HTMLSession, AsyncHTMLSession

import discord
from discord.ext import commands
from discord.ext.tasks import loop

from discord_slash import SlashCommand, SlashContext
from discord_slash.context import ComponentContext
from discord_slash.utils.manage_commands import create_choice, create_option

INVERVAL_LOOP=900

from dotenv import load_dotenv
load_dotenv() 

TOKEN = os.getenv('BOT_TOKEN')
POLICY_ID = os.getenv('POLICY_ID')
SALES_CHANNEL=os.getenv('SALES_CHANNEL')
GUILD_NAME = os.getenv('GUILD_NAME')
GUILD_ID = os.getenv('GUILD_ID')

GUILD_IDS=[int(GUILD_ID)]

CARDANOSCAN_URL = "https://cardanoscan.io"
BLOCKFROST_IPFS_URL = "https://ipfs.blockfrost.dev/ipfs"
POOL_PM_URL= "https://pool.pm"
CNFT_URL = "https://cnft.io"

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

    URL_TEMPLATE = f"https://api.cnft.io/api/sold?search={policy_id}&sort=date&order=desc&page=<page>&count=250"

    page = 1
    total_amount = None
    next_page = True
    while next_page:
        
        try:
            response = requests.get(URL_TEMPLATE.replace("<page>", str(page))).json()
        except:
            return
        else:

            if not total_amount:
                total_amount = response.get('found')

            assets = response.get('assets')
            
            if assets:
                sales.extend(assets)
            else:
                next_page = False

            print(f"{len(assets)} assets found on sales page {page}")
            page +=1

    if len(sales) < 0.95 * int(total_amount):
        return 

    return sales

def get_asset_id(asset_name) -> str:
    ASSET_IDS = load_json("json/asset_ids.json")
    return ASSET_IDS.get(asset_name, None)

def get_asset_name_from_idx(idx):
    number_str = str(idx).zfill(5)
    return f"unsig{number_str}"

def get_idx_from_asset_id(asset_id: str) -> int:
    regex_str = r"(?P<number>[0-9]+)"
    regex = re.compile(regex_str)
    match = re.search(regex, asset_id)
    number = match.group("number")
    if number:
        return int(number)

async def get_ipfs_url(asset_id, asset_name):
    metadata = await get_metadata(asset_id)
    ipfs_hash = get_ipfs_hash(metadata, asset_id, asset_name)
    if ipfs_hash:
        ipfs_url = f"{BLOCKFROST_IPFS_URL}/{ipfs_hash}"
        return ipfs_url

async def get_ipfs_url_from_file(asset_name):
    pass
    

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
        tx_id=r.html.xpath("//*[@id='minttransactions']//a[starts-with(@href,'/transaction')]/text()")[0]
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

def get_minting_data(idx):
    unsigs_data = load_json("json/unsigs.json")
    return unsigs_data.get(idx, None)

def get_minting_number(asset_name):
    minting_order = load_json("json/minted.json")
    number = minting_order.index(asset_name) + 1
    return number

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
    if int(number) <= MAX_AMOUNT and int(number) >= 0:
        return True
    else:
        return False

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




bot = commands.Bot(command_prefix='!', help_command=None)

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

def embed_minting_order(embed, minting_number):
    pass

def embed_sales(embed, sales):

    sales_value=""

    for sale in sales:
        asset_name = sale.get("assetid").replace("_", "")
        price = sale.get('price')/1000000
        timestamp_ms = sale.get('date')
        date = datetime.utcfromtimestamp(timestamp_ms/1000).date()

        row = f"sold on **{date}** for **₳{price:,.0f}**\n"
        sales_value += row

    embed.add_field(name=f"{EMOJI_SHOPPINGBAGS} Past sales", value=sales_value, inline=False)



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



@slash.slash(
    name="sell", 
    description="offer you unsig for sale", 
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
        await ctx.send(content=f"Please post you offer in the #{SELLING_CHANNEL} channel.")
        return
        
    asset_name = get_asset_name_from_idx(int(number))

    if not unsig_exists(number):
        await ctx.send(content=f"{asset_name} does not exist!\nPlease enter number between 0 and {MAX_AMOUNT}.")
    else:
        asset_id = get_asset_id(asset_name)

        minting_data = get_minting_data(str(int(number)))
        minting_number = get_minting_number(asset_name)

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

        embed.add_field(name="Minting order", value=f"{minting_number}/{MAX_AMOUNT+1} ", inline=False)

        total_props = minting_data.get("num_props")
        embed.add_field(name="Total properties", value=f"This unsig has **{total_props}** properties", inline=False)

        image_url = await get_ipfs_url(asset_id, asset_name)

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
        )
    ]
)
async def unsig(ctx: SlashContext, number: str):
        
    if ctx.channel.name == "general":
        await ctx.send(content=f"I'm not allowed to post here...")
        return
        
    asset_name = get_asset_name_from_idx(int(number))

    if not unsig_exists(number):
        await ctx.send(content=f"{asset_name} does not exist!\nPlease enter number between 0 and {MAX_AMOUNT}.")
    else:
        asset_id = get_asset_id(asset_name)

        minting_data = get_minting_data(str(int(number)))
        minting_number = get_minting_number(asset_name)

        title = f"{asset_name}"
        description="minted by unsigned_algorithms"
        color=discord.Colour.dark_blue()

        embed = discord.Embed(title=title, description=description, color=color)

        embed.add_field(name=f"{EMOJI_NUMBERS} Minting order", value=f"{minting_number}/{MAX_AMOUNT+1} ", inline=False)

        if bot.sales:
            past_sales = filter_sales_by_asset(bot.sales, asset_name)
            sales_by_date = sort_sales_by_date(past_sales, descending=True)

            if past_sales:
                embed_sales(embed, sales_by_date)

        total_props = minting_data.get("num_props")
        embed.add_field(name="Total properties", value=f"Your unsig has **{total_props}** properties", inline=False)

        properties = minting_data.get("properties")

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

        image_url = await get_ipfs_url(asset_id, asset_name)

        if image_url:
            embed.set_image(url=image_url)

        embed.set_footer(text=f"\nAlways check policy id:\n{POLICY_ID}")
 
        await ctx.send(embed=embed)

@slash.slash(
    name="owner", 
    description="shows wallet of unsig with given number", 
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
        await ctx.send(content=f"I'm not allowed to post here...d")
        return 

    asset_name = get_asset_name_from_idx(int(number))

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
        channel = discord.utils.get(bot.guild.channels, name=SALES_CHANNEL)
    except:
        print(f"Can't find the {SALES_CHANNEL} channel")
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

            image_url = await get_ipfs_url(asset_id, asset_name)

            if image_url:
                embed.set_image(url=image_url)

            embed.set_footer(text=f"Data comes from {CNFT_URL}")
            await channel.send(embed=embed)


@loop(seconds=INVERVAL_LOOP)
async def fetch_data():
    
    sales_data = await get_sales_data(POLICY_ID)
    if sales_data:
        bot.sales = sales_data
        bot.last_update = datetime.now()

        latest_sales = filter_by_time_interval(sales_data, INVERVAL_LOOP*1000)

        if latest_sales:
            await asyncio.sleep(2)
            await post_sales(latest_sales)
 
    print("Updated:", datetime.now()) 


bot.run(TOKEN)