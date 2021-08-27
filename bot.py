import os
import re
import json

from files_util import load_json

import requests
from requests_html import HTMLSession, AsyncHTMLSession

import discord
from discord.ext import commands
from discord.ext.tasks import loop

from discord_slash import SlashCommand, SlashContext
from discord_slash.context import ComponentContext
from discord_slash.utils.manage_commands import create_choice, create_option



from dotenv import load_dotenv
load_dotenv() 

TOKEN = os.getenv('BOT_TOKEN')
POLICY_ID = os.getenv('POLICY_ID')
GUILD_NAME = os.getenv('GUILD_NAME')
GUILD_ID = os.getenv('GUILD_ID')

GUILD_IDS=[int(GUILD_ID)]

CARDANOSCAN_URL = "https://cardanoscan.io"
BLOCKFROST_IPFS_URL = "https://ipfs.blockfrost.dev/ipfs"
POOL_PM_URL= "https://pool.pm"

MAX_AMOUNT = 31119

EMOJI_FRAME="\U0001F5BC"
EMOJI_RAINBOW = "\U0001F308"
EMOJI_BARCHART = "\U0001F4CA"
EMOJI_CIRCLE_ARROWS = "\U0001F504"
EMOJI_GEAR = "\u2699"

DISCORD_COLOR_CODES = {
    "blue": "ini",
    "red": "diff",
    "green": "bash"  
}

def get_asset_id(asset_name) -> str:
    ASSET_IDS = load_json("json/asset_ids.json")
    return ASSET_IDS.get(asset_name, None)

def get_asset_name_from_idx(idx):
    number_str = str(idx).zfill(5)
    return f"unsig{number_str}"

async def get_ipfs_url(asset_id, asset_name):
    metadata = await get_metadata(asset_id)
    ipfs_hash = get_ipfs_hash(metadata, asset_id, asset_name)
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

    session = HTMLSession()

    try:
        r = session.get(URL)
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


def get_current_owner_address(token_id: str) -> str:
    url = f"{CARDANOSCAN_URL}/token/{token_id}?tab=topholders"

    session = HTMLSession()

    try:
        r = session.get(url)
    except:
        address = None
    else:
        address_str = r.html.xpath("//*[@id='topholders']//a[contains(@href,'address')]/text()")[0]
        address_id = r.html.xpath("//*[@id='topholders']//a[contains(@href,'address')]/@href")[0]
        address_id = address_id.rsplit("/")[-1]
        address = {
            "id": address_id,
            "name": address_str
        }
    finally:
        return address

def unsig_exists(number: str) -> bool:
    if int(number) <= MAX_AMOUNT and int(number) >= 1:
        return True
    else:
        return False

bot = commands.Bot(command_prefix='!', help_command=None)

slash = SlashCommand(bot, sync_commands=True)

@bot.event
async def on_ready():
    print("guilds", bot.guilds)

    bot.guild = discord.utils.find(lambda g: g.name == GUILD_NAME, bot.guilds)

    if bot.guild:
        print(
            f'{bot.user} is connected to the following guild:\n'
            f'{bot.guild.name}(id: {bot.guild.id})'
        )

    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name='unsigned_algorithms'))

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

    asset_name = get_asset_name_from_idx(int(number))

    if not unsig_exists(number):
        await ctx.send(content=f"{asset_name} does not exist!\nPlease enter number between 1 and {MAX_AMOUNT}.")
    else:
        asset_id = get_asset_id(asset_name)

        minting_data = get_minting_data(str(int(number)))

        title = f"{asset_name}"
        description="minted by unsigned_algorithms"
        color=discord.Colour.dark_blue()

        embed = discord.Embed(title=title, description=description, color=color)

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

        print(image_url)
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
    asset_name = get_asset_name_from_idx(int(number))

    if not unsig_exists(number):
        await ctx.send(content=f"{asset_name} does not exist!\nPlease enter number between 1 and {MAX_AMOUNT}.")
    else:
        asset_id = get_asset_id(asset_name)

        owner_address_data = get_current_owner_address(asset_id)
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

bot.run(TOKEN)