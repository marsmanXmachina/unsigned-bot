import os
import pprint
import math
import random
import numpy as np
from datetime import datetime
import asyncio
from collections import Counter
import inflect

import discord
from discord.ext import commands
from discord.ext.tasks import loop
from discord_slash import SlashCommand, SlashContext
from discord_slash.utils.manage_commands import create_choice, create_option

from unsigned_bot.utility.files_util import load_json, save_json
from unsigned_bot.utility.time_util import timestamp_to_datetime, get_interval_from_period
from unsigned_bot.utility.price_util import get_min_prices, get_average_price

from unsigned_bot.fetch import (
    get_new_certificates,
    get_ipfs_url_from_file,
    get_current_owner_address,
    get_unsig_data,
    get_minting_data,
    get_metadata_from_asset_name,
    get_minting_tx_id,
    get_wallet_balance
)
from unsigned_bot.parsing import (
    get_asset_id,
    get_asset_name_from_idx,
    get_asset_name_from_minting_order,
    get_asset_from_number,
    get_idx_from_asset_name,
    get_numbers_from_assets,
    get_numbers_from_string,
    order_by_num_props,
    get_unsig_url,
    get_url_from_marketplace_id,
    link_asset_to_marketplace,
    link_assets_to_grid,
    get_certificate_data_by_number,
    filter_certs_by_time_interval,
    filter_by_time_interval,
    filter_sales_by_asset,
    filter_new_sales,
    filter_assets_by_type,
    sort_sales_by_date,
    unsig_exists
)
from unsigned_bot.aggregate import aggregate_data_from_marketplaces
from unsigned_bot.matching import match_unsig, choose_best_matches, get_similar_unsigs
from unsigned_bot.deconstruct import (
    SUBPATTERN_NAMES, 
    get_prop_layers,
    get_subpattern,
    get_subpattern_names,
    filter_subs_by_names
)
from unsigned_bot.draw import (
    gen_evolution,
    gen_subpattern,
    gen_grid,
    gen_grid_with_matches,
    gen_animation,
    gen_color_histogram,
    delete_image_files
)
from unsigned_bot.colors import (
    COLOR_RANKING, PIXELS_COLORS, 
    get_color_frequencies,
    get_total_colors,
    get_top_colors,
    rgb_2_hex,
    link_hex_color,
    calc_color_rarity
)
from unsigned_bot.twitter import tweet_sales, create_twitter_api
from unsigned_bot.constants import POLICY_ID, MAX_AMOUNT
from unsigned_bot.emojis import *
from unsigned_bot.urls import *
from unsigned_bot import ROOT_DIR

from dotenv import load_dotenv
load_dotenv() 


FILE_DIR = os.path.dirname(os.path.abspath(__file__))
IMAGE_PATH = f"{FILE_DIR}/img"

TOKEN = os.getenv('BOT_TOKEN')
INVERVAL_LOOP=900

# GUILD_NAME = "unsigned_algorithms"
# GUILD_ID = 843043397526093885
# SALES_CHANNEL_ID = 860188673239416862

#Test config
GUILD_NAME = "UnsignedBots"
GUILD_ID = 880769226422501436
SALES_CHANNEL_ID = 881188219092357180

GUILD_IDS = [GUILD_ID]


bot = commands.Bot(command_prefix='!', help_command=None)
bot.sales = load_json("data/json/sales.json")
bot.sales_updated = None
bot.offers = None
bot.offers_updated = None
bot.certs = load_json("data/json/certificates.json")
bot.certs_updated = None
bot.twitter_api = create_twitter_api()


slash = SlashCommand(bot, sync_commands=True, sync_on_cog_reload=True)

@bot.event
async def on_ready():
    if not fetch_data.is_running():
        fetch_data.start()
    
    print("bot guilds", bot.guilds)

    bot.guild = discord.utils.find(lambda g: g.name == GUILD_NAME, bot.guilds)

    if bot.guild:
        print(
            f'{bot.user} is connected to the following guild:\n'
            f'{bot.guild.name}(id: {bot.guild.id})'
        )

    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name='unsigned_algorithms'))


def add_minting_order(embed, minting_data):
    """Add minting order to discord embed"""
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

def add_num_props(embed, unsig_data):
    total_props = unsig_data.get("num_props")
    embed.add_field(name="Total properties", value=f"This unsig has **{total_props}** properties", inline=False)

def add_props(embed, unsig_data):
    """Add properties to discord embed"""

    properties = unsig_data.get("properties")
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


def add_subs(embed, number:str):
    try:
        unsigs_subpattern = load_json("data/json/subpattern.json")
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
    embed.set_footer(text=f"The server has no affiliation with the marketplace nor listed prices.\n\nData comes from \n - {CNFT_URL}\n - {TOKHUN_URL}\nLast update: {last_update}")

def add_data_source(embed, last_update):
    last_update = last_update.strftime("%Y-%m-%d %H:%M:%S UTC")
    embed.set_footer(text=f"Data comes from\n - {CNFT_URL}\n - {TOKHUN_URL}\nLast update: {last_update}")

def add_policy(embed):
    embed.add_field(name = f"{EMOJI_WARNING} Watch out for fake items and always check the policy id {EMOJI_WARNING}", value=f"`{POLICY_ID}`", inline=False)

def add_last_update(embed, last_update):
    last_update = last_update.strftime("%Y-%m-%d %H:%M:%S UTC")
    embed.set_footer(text=f"\nLast update: {last_update}")

def add_subpattern(embed, unsig_data):
    
    layers = get_prop_layers(unsig_data)
    subpattern = get_subpattern(layers)
    subpattern_names = get_subpattern_names(subpattern)

    COLORS = ["Red", "Green", "Blue"]
    subpattern_str = ""

    for color in reversed(COLORS):
        name = subpattern_names.get(color, None)
        if name:
            subpattern_str += f" - {color.lower()} {name}\n"

    embed.add_field(name = f"{EMOJI_DNA} Subpattern {EMOJI_DNA}", value=f"`{subpattern_str}`", inline=False)


    subs_counted = load_json("data/json/subs_counted.json")
    pattern_for_search = list(subpattern_names.values())

    pattern_found = filter_subs_by_names(subs_counted, pattern_for_search)
    num_pattern = len(pattern_found)

    pattern_formatted = dict(Counter(pattern_for_search))

    pattern_combo_str = " + \n".join([f" {amount} x {pattern}" for pattern, amount in pattern_formatted.items()])

    if layers:
        frequency_str = f"\n=> **{num_pattern} / 31119** unsigs with this pattern combo"
    else:
        frequency_str = ""

    embed.add_field(name = f"{EMOJI_LINK} Pattern combo {EMOJI_LINK}", value=f"`{pattern_combo_str}`\n{frequency_str}", inline=False)
    


def embed_certificate(number, data: dict, num_certificates: int, feed=False):

    if data:
        metadata = data.get("onchain_metadata")
        policy_id = data.get("policy_id")
        certificate_name = metadata.get("name")

        certificate_number = get_idx_from_asset_name(certificate_name)
        
        certificate_link = f"{POOL_PM_URL}/{policy_id}.UNS{str(certificate_number).zfill(5)}x{number.zfill(5)}"

        ipfs_hash = metadata.get("image").rsplit("/",1)[-1]
        image_link = f"{BLOCKFROST_IPFS_URL}/{ipfs_hash}"


        title = f"{EMOJI_CERT} Cert for unsig{number.zfill(5)} {EMOJI_CERT}"
        if feed:
            description=f"minted by CNFT_ART\n"
        else:
            description=f"**{num_certificates}** certificates already minted\n"
        color=discord.Colour.dark_blue()
    
        embed = discord.Embed(title=title, description=description, color=color, url=certificate_link)
    else:
        title = f"{EMOJI_CROSS} No cert found for unsig{number.zfill(5)} {EMOJI_CROSS}"
        description=f"**{num_certificates}** certificates already minted\n"
        color=discord.Colour.dark_blue()
        embed = discord.Embed(title=title, description=description, color=color)
    
    if data:
        mint_date = metadata.get("Unsig mint date")
        embed.add_field(name=f"{EMOJI_PICK} Minted on", value=f"`{mint_date}`", inline=True)

        assessment_date = metadata.get("Assessment date")
        embed.add_field(name=f"{EMOJI_CHECK} Certified on", value=f"`{assessment_date}`", inline=True)

        embed.set_image(url=image_link)

    embed.add_field(name=f"{EMOJI_CART} Order your unsig certificate {EMOJI_CART}", value=f"{EMOJI_ARROW_RIGHT} visit [CNFT_ART's discord]({DISCORD_CNFT_ART})", inline=False)

    if not feed:
        add_last_update(embed, bot.certs_updated)

    return embed
    
def add_output_colors(embed, color_frequencies, num_colors=10):

    top_colors = get_top_colors(color_frequencies, num_ranks=num_colors)

    top_colors_str = ""
    for i, (color, percentage) in enumerate(top_colors.items()):
        color_rank = COLOR_RANKING.get(color)
        color_hex = rgb_2_hex(color)
        color_link = link_hex_color(color_hex)
        top_colors_str += f" {i+1}. [{color_hex}]({color_link}) to **{percentage:.2%}** `[{color_rank}]`\n"
    
    color_rarity = calc_color_rarity(color_frequencies)

    top_colors_str += f" => weighted color rank: **{color_rarity:.2f}**\n"

    embed.add_field(name=f"{EMOJI_ARROW_DOWN} Top Colors [rarity rank] {EMOJI_ARROW_DOWN}", value=top_colors_str, inline=False)





BOT_COMMANDS = {
    "general": {
        "description": "commands for general information",
        "faq": {
            "syntax": "/faq",
            "hint": "show important information"
        },
    },
    "data": {
        "description": "commands to get info about your unsig",
        "unsig": {
            "syntax": "/unsig + `integer`",
            "hint": "show info for unsig with given number"
        },
        "metadata": {
            "syntax": "/metadata + `integer`",
            "hint": "show data of unsig with given number"
        },
        "minted": {
            "syntax": "/minted + `integer`",
            "hint": "show unsig with given minting order"
        },
        "cert": {
            "syntax": "/cert + `integer`",
            "hint": "show cert of unsig with given number"
        }
    },
    "geometry": {
        "description": "commands for geometrical analysis",
        "pattern-combo": {
            "syntax": "/pattern-combo",
            "hint": "count unsigs with given pattern combo"
        },
        "forms": {
            "syntax": "/forms",
            "hint": "show unsigs with given form"            
        }
    },
    "structure": {
        "description": "commands to deconstruct your unsig",
        "evo": {
            "syntax": "/evo + `integer`",
            "hint": "show composition of your unsig"
        },
        "invo": {
            "syntax": "/invo + `integer`",
            "hint": "show ingredients of your unsig"
        },
        "subs": {
            "syntax": "/subs + `integer`",
            "hint": "show subpattern of your unsig"
        }
    },
    "colors": {
        "description": "commands for color analysis",
        "colors": {
            "syntax": "/colors + `integer`",
            "hint": "show output colors of your unsig"
        },
        "color-ranking": {
            "syntax": "/color-ranking",
            "hint": "show color ranking"
        }
    },
    "ownership": {
        "description": "commands for ownership of unsigs",
        "owner": {
            "syntax": "/owner + `integer`",
            "hint": "show wallet of given unsig"
        }
    },
    "market": {
        "description": "commands for offers and sales",
        "sell": {
            "syntax": "/sell + `integer` + `price`",
            "hint": "offer your unsig for sale"
        },
        "floor": {
            "syntax": "/floor",
            "hint": "show cheapest unsigs on marketplace"
        },
        "sales": {
            "syntax": "/sales",
            "hint": "show sold unsigs on marketplace"
        },
        "like": {
            "syntax": "/like + `integer`",
            "hint": "show related unsigs sold"
        },
        "matches": {
            "syntax": "/matches + `integer`",
            "hint": "show available matches on marketplace"
        }
    },
    "collection": {
        "description": "commands for your unsig collection",
        "show": {
            "syntax": "/show + `numbers`",
            "hint": "show your unsig collection"
        },
        "siblings": {
            "syntax": "/siblings + `integer`",
            "hint": "show siblings of your unsig"
        }
    }
}

@slash.slash(
    name="help", 
    description="Get overview of my commands", 
    guild_ids=GUILD_IDS,
    options=[
        create_option(
            name="category",
            description="Choose category",
            required=False,
            option_type=3,
            choices=[
                create_choice(
                    name=f"{command.capitalize()}",
                    value=command
                ) for command, _ in BOT_COMMANDS.items()
            ]
        )
    ]
)
async def help(ctx: SlashContext, category=None):
    if not category:
        title = f"{EMOJI_ROBOT} My commands {EMOJI_ROBOT}"
        description="How can I help you?"
    else:
        emoji = COMMAND_CATEGORIES.get(category)
        title = f"{emoji} {category.capitalize()} commands {emoji}"
        description = BOT_COMMANDS.get(category).get("description")

    color=discord.Colour.dark_blue()        
    embed = discord.Embed(title=title, description=description, color=color) 

    for command_group, commands in BOT_COMMANDS.items():
        if not category:
            emoji = COMMAND_CATEGORIES.get(command_group)
            description = commands.get("description")

            embed.add_field(name=f"\n{emoji} {command_group.capitalize()}", value=description, inline=False)
        else:
            if category == command_group:
                for command, values in commands.items():
                    if command == "description":
                        continue

                    syntax = values.get("syntax")
                    hint = values.get("hint")

                    embed.add_field(name=syntax, value=hint, inline=False)
    
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
        create_option(
            name="animation",
            description="show animated unsig",
            required=False,
            option_type=3,
            choices=[
                create_choice(
                    name="fading",
                    value="fade"
                ),
                create_choice(
                    name="blending",
                    value="blend"
                )
            ]
        )
    ]
)
async def unsig(ctx: SlashContext, number: str, animation=False):
        
    if ctx.channel.name == "general":
        await ctx.send(content=f"I'm not allowed to post here.\n Please go to #bot channel.")
        return

    asset_name = get_asset_name_from_idx(number)

    if not unsig_exists(number):
        await ctx.send(content=f"{asset_name} does not exist!\nPlease enter number between 0 and {MAX_AMOUNT}.")
    else:
        number = str(int(number))

        unsigs_data = get_unsig_data(number)
        minting_data = get_minting_data(number)

        unsig_url = get_unsig_url(number)

        title = f"{asset_name}"
        description="minted by unsigned_algorithms"
        color=discord.Colour.dark_blue()

        embed = discord.Embed(title=title, description=description, color=color, url=unsig_url)

        add_minting_order(embed, minting_data)
       
        if bot.sales:
            past_sales = filter_sales_by_asset(bot.sales, asset_name)
            sales_by_date = sort_sales_by_date(past_sales, descending=True)

            if past_sales:
                add_sales(embed, sales_by_date)

        add_num_props(embed, unsigs_data)
        add_props(embed, unsigs_data)

        color_frequencies = get_color_frequencies(number)
        add_output_colors(embed, color_frequencies, num_colors=6)
        add_subpattern(embed, unsigs_data)

        num_props = unsigs_data.get("num_props")
        if animation and num_props > 1:
            try:
                image_path = await gen_animation(number, mode=animation, backwards=True)

                image_file = discord.File(image_path, filename="image.gif")
                if image_file:
                    embed.set_image(url="attachment://image.gif")

                delete_image_files(IMAGE_PATH, suffix="gif")
            except:
                print("Animation failed!")
            else:
                embed.set_footer(text=f"\nDiscord Bot by Mar5man")

                await ctx.send(file=image_file, embed=embed)
                return 

        image_url = await get_ipfs_url_from_file(asset_name)

        try:
            embed.set_image(url=image_url)
        except:
            pass

        embed.set_footer(text=f"\nDiscord Bot by Mar5man")

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

    LIMIT_DISPLAY = 20
    if len(numbers_cleaned) > LIMIT_DISPLAY:
        numbers_cleaned = numbers_cleaned[:LIMIT_DISPLAY]
    
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
    name="subs", 
    description="show subpattern of unsig with given number", 
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
async def subs(ctx: SlashContext, number: str):
    """show subpattern of your unsig"""

    if ctx.channel.name == "general":
        await ctx.send(content=f"I'm not allowed to post here.\n Please go to #bot channel.")
        return

    asset_name = get_asset_name_from_idx(number)

    if not unsig_exists(number):
        await ctx.send(content=f"{asset_name} does not exist!\nPlease enter number between 0 and {MAX_AMOUNT}.")
    else:
        number = str(int(number))

        unsig_data = get_unsig_data(number)

        layers = get_prop_layers(unsig_data)
        subpattern = get_subpattern(layers)
        subpattern_names = get_subpattern_names(subpattern)

        title = f"{EMOJI_PALETTE} {asset_name} {EMOJI_PALETTE}"
        description="Explore the subpattern of your unsig..."
        color=discord.Colour.dark_blue()

        embed = discord.Embed(title=title, description=description, color=color)

        if len(layers) > 1:
            name_idx = 1
            names_str = f"{name_idx}. #{number.zfill(5)}\n"
        else:
            names_str = ""
            name_idx = 0

        COLORS = ["Red", "Green", "Blue"]
        for color in reversed(COLORS):
            name = subpattern_names.get(color, None)
            if not name:
                continue

            name_idx += 1
            names_str += f"{name_idx}. `{color.lower()} {name}`\n"

        embed.add_field(name=f"{EMOJI_ARROW_DOWN} Top to Bottom {EMOJI_ARROW_DOWN}", value=names_str, inline=False)

        try:
            image_path = await gen_subpattern(number)

            image_file = discord.File(image_path, filename="image.png")
            if image_file:
                embed.set_image(url="attachment://image.png")

            delete_image_files(IMAGE_PATH)
        except:
            await ctx.send(content=f"I can't generate the subpattern of your unsig.")
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
    """show ingredients of your unsig"""  

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
            image_path = await gen_evolution(number, show_single_layers=True)

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
    """show composition of your unsig"""  

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

        add_subs(embed, number)

        try:
            extended = True if extended == "extended" else False

            image_path = await gen_evolution(number, show_single_layers=False, extended=extended)

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
    """show unsig with given minting order"""  

    if ctx.channel.name == "general":
        await ctx.send(content=f"I'm not allowed to post here.\n Please go to #bot channel.")
        return
        
    asset_name = get_asset_name_from_minting_order(index)

    if not asset_name:
        await ctx.send(content=f"Unsig with minting order {index} does not exist!\nPlease enter number between 1 and {MAX_AMOUNT+1}.")
    else:
        number = str(get_idx_from_asset_name(asset_name))
        unsig_url = get_unsig_url(number)

        unsigs_data = get_unsig_data(number)
        minting_data = get_minting_data(number)

        title = f"{asset_name}"
        description="minted by unsigned_algorithms"
        color=discord.Colour.dark_blue()

        embed = discord.Embed(title=title, description=description, color=color, url=unsig_url)

        add_minting_order(embed, minting_data)
       
        if bot.sales:
            past_sales = filter_sales_by_asset(bot.sales, asset_name)
            sales_by_date = sort_sales_by_date(past_sales, descending=True)

            if past_sales:
                add_sales(embed, sales_by_date)

        add_num_props(embed, unsigs_data)
        add_props(embed, unsigs_data)

        image_url = await get_ipfs_url_from_file(asset_name)
        if image_url:
            embed.set_image(url=image_url)

        embed.set_footer(text=f"\nDiscord Bot by Mar5man")
 
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
    """show wallet of unsig with given number"""

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
            asset_name = sale_data.get("assetid")

            price = sale_data.get("price")
            price = price/1000000
            timestamp_ms = sale_data.get("date")
            date = datetime.utcfromtimestamp(timestamp_ms/1000).strftime("%Y-%m-%d %H:%M:%S UTC")

            marketplace = sale_data.get("marketplace")

            title = f"{EMOJI_CART} {asset_name} {EMOJI_CART}"
            description="minted by unsigned_algorithms"
            color=discord.Colour.dark_blue()

            embed = discord.Embed(title=title, description=description, color=color)

            embed.add_field(name=f"{EMOJI_MONEYBAG} Price", value=f"₳{price:,.0f}", inline=True)
            embed.add_field(name=f"{EMOJI_CALENDAR} Sold on", value=date, inline=True)
            embed.add_field(name=f"{EMOJI_PIN} Marketplace", value=f"`{marketplace.upper()}`", inline=False)

            image_url = await get_ipfs_url_from_file(asset_name)

            if image_url:
                embed.set_image(url=image_url)

            embed.set_footer(text=f"Data comes from \n - {CNFT_URL}\n - {TOKHUN_URL}")
            
            message = await channel.send(embed=embed)
            await message.publish()

async def post_certs(new_certs: dict, num_certificates):
    try:
        channel = bot.get_channel(SALES_CHANNEL_ID)
    except:
        print(f"Can't find the sales feed channel")
    else:
        for cert_id, cert_data in new_certs.items():
            metadata = cert_data.get("onchain_metadata")
            asset_name = metadata.get("Unsig number")
            unsig_number = asset_name.replace("#", "")

            embed = embed_certificate(str(int(unsig_number)), cert_data, num_certificates, feed=True)
            message = await channel.send(embed=embed)
            try:
                await message.publish()
            except:
                print("Can not publish cert!")


@loop(seconds=INVERVAL_LOOP)
async def fetch_data():
    """Background tasks for fetching and posting data"""

    # === fetch and post new sales data ===
    try:
        sales_data = await aggregate_data_from_marketplaces(sold=True)
    except:
        print("Parsing sales data failed!")
    else:
        if sales_data:
            new_sales = filter_new_sales(bot.sales, sales_data)
            bot.sales_updated = datetime.utcnow()
            print("sales updated", bot.sales_updated)

            if new_sales:
                bot.sales.extend(new_sales)
                save_json("data/json/sales.json", bot.sales)
        
                new_sales = filter_by_time_interval(new_sales, INVERVAL_LOOP * 1000)

                if bot.guild.name == "unsigned_algorithms":
                    await asyncio.sleep(2)
                    await post_sales(new_sales)

                    if not bot.twitter_api:
                        bot.twitter_api = create_twitter_api()

                    try:
                        await tweet_sales(bot.twitter_api, new_sales)
                    except:
                        print("Tweeting sales FAILED!")
    
    # === fetch offers data ===
    try:
        offers_data = await aggregate_data_from_marketplaces(sold=False)
    except:
        print("Parsing listing data failed!")
    else:
        if offers_data:
            bot.offers = offers_data
            bot.offers_updated = datetime.utcnow()

    # === fetch and post new certificates ===
    try:
        certificates = load_json("data/json/certificates.json")

        new_certificates = get_new_certificates(certificates)
        print(len(new_certificates), "new certificates found")
        
        if new_certificates:
            bot.certs.update(new_certificates)
            save_json("data/json/certificates.json", bot.certs)

            if bot.guild.name == "unsigned_algorithms":
                num_certificates = len(bot.certs.keys())

                new_certificates = filter_certs_by_time_interval(new_certificates, INVERVAL_LOOP * 1000)
                
                await asyncio.sleep(2)
                await post_certs(new_certificates, num_certificates)
            
        bot.certs_updated = datetime.utcnow()
    except:
        print("Update certificates failed!")

    print("Updated:", datetime.now()) 


# == load cogs ==
for folder in os.listdir("unsigned_bot/cogs"):
    if os.path.exists(os.path.join("unsigned_bot/cogs", folder, "cog.py")):
        bot.load_extension(f"unsigned_bot.cogs.{folder}.cog")


def main():
    bot.run(TOKEN)


if __name__ == "__main__":
    
    bot.run(TOKEN)