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
    get_unsigs_data,
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
from unsigned_bot.constants import POLICY_ID, MAX_AMOUNT, TREASURY_ADDRESS
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

def add_num_props(embed, unsigs_data):
    total_props = unsigs_data.get("num_props")
    embed.add_field(name="Total properties", value=f"This unsig has **{total_props}** properties", inline=False)

def add_props(embed, unsigs_data):
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

async def embed_metadata(metadata):
    asset_name = metadata.get("title").replace("_", "")

    try:
        asset_id = get_asset_id(asset_name)
        tx_id = await get_minting_tx_id(asset_id)
    except:
        metadata_url = None
    else:
        metadata_url = f"{CARDANOSCAN_URL}/transaction/{tx_id}/?tab=metadata"

    title = f"{EMOJI_FILE}  metadata {asset_name}  {EMOJI_FILE}"
    description="Show metadata of your unsig"
    color=discord.Colour.dark_blue()

    embed = discord.Embed(title=title, description=description, color=color, url=metadata_url)

    for k, v in metadata.items():
        if isinstance(v, dict):
            value_str = pprint.pformat(v)
        else:   
            value_str = v
        
        if len(str(value_str)) >= 1024:
            value_str = f"Data too long to display!"
            if metadata_url:
                value_str += f"\nClick **[here]({metadata_url})** to see complete metadata."
        else:
            value_str = f"`{value_str}`"

        embed.add_field(name=f"**'{k}'**", value=f"{value_str}", inline=False)

    return embed

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
    

def embed_offers(assets_ordered: dict):
    title = f"{EMOJI_BROOM} Unsigs Floor {EMOJI_BROOM}"
    description="Cheapest unsigs on marketplace\n(auctions excluded)"
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
                number = asset_name.replace("unsig", "")
                marketplace_id = asset.get("id")
                marketplace = asset.get("marketplace")
                offers_str += f" [#{number.zfill(5)}]({get_url_from_marketplace_id(marketplace_id, marketplace)}) "
            
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
                    number = name.replace("unsig", "")
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

def embed_matches(number, matches, best_matches, offers):

    asset_name = get_asset_name_from_idx(number)

    title = f"{EMOJI_PUZZLE} {asset_name} matches {EMOJI_PUZZLE}"
    description="Available matches on marketplace"
    color=discord.Colour.dark_blue()

    embed = discord.Embed(title=title, description=description, color=color)

    SIDES = ["top", "left", "right", "bottom"]

    for side in SIDES:

        arrow = ARROWS.get(side)
        matches_str=""

        matches_side = matches.get(side, None)

        if matches_side:
            for match in matches_side:
                offer = get_asset_from_number(match, offers)
                offer_id = offer.get("id")
                marketplace = offer.get("marketplace")
                marketplace_url = get_url_from_marketplace_id(offer_id, marketplace)
                match_str=f" [#{str(match).zfill(5)}]({marketplace_url}) "
                matches_str += match_str
        else:
            matches_str="` - `"

        embed.add_field(name=f"{arrow} {side.upper()} {arrow}", value=matches_str, inline=False)

    UNSIG_MATCHBOX_LINK = "https://discord.gg/RR8rhNH2"
    matchbox_text = f"For deeper analysis checkout [unsig_matchbox]({UNSIG_MATCHBOX_LINK})"
    embed.add_field(name=f"{EMOJI_GLASS} Portfolio Analysis {EMOJI_GLASS}", value=matchbox_text, inline=False)
    
    best_matches_str=""

    for side in SIDES:
        best_match = best_matches.get(side, None)
        if best_match:
            offer = get_asset_from_number(best_match, offers)
            offer_id = offer.get("id")
            marketplace = offer.get("marketplace")
            marketplace_url = get_url_from_marketplace_id(offer_id, marketplace)
            best_match_str=f"[#{str(best_match).zfill(5)}]({marketplace_url})"
        else:
            best_match_str = "` - `"

        arrow = ARROWS.get(side)
        best_matches_str += f"{arrow} {best_match_str}\n" 

    embed.add_field(name="Matches displayed", value=best_matches_str)

    return embed
    
def embed_related(number, related, selected, sales, cols=3):
    asset_name = get_asset_name_from_idx(number)

    title = f"{EMOJI_MIRROW} like {asset_name} {EMOJI_MIRROW}"
    description="Related unsigs sold"
    color=discord.Colour.dark_blue()

    embed = discord.Embed(title=title, description=description, color=color)

    related_sales = [sale for sale in sales if get_idx_from_asset_name(sale.get("assetid")) in related]

    last_related_sales = related_sales[:10]
    
    if not related:
        related_str = "` - `"
    else:
        related_str = ""
        for i, sale in enumerate(last_related_sales):
            asset_name = sale.get("assetid")
            asset_number = get_idx_from_asset_name(asset_name)
            price = sale.get("price")
            price = price/1000000
            timestamp_ms = sale.get("date")
            dt = timestamp_to_datetime(timestamp_ms)

            sale_str = f"#{str(asset_number).zfill(5)} sold for **₳{price:,.0f}** on {dt.date()}\n"

            related_str += sale_str

    embed.add_field(name=f"Sales of similar unsigs", value=related_str, inline=False)

    if related:
        selected_str = ""

        for i, num in enumerate(selected):

            displayed_str = f" #{str(num).zfill(5)} "
            
            selected_str += displayed_str

            if (i+1) % cols == 0:
                selected_str += "\n"

        embed.add_field(name=f"{EMOJI_ARROW_DOWN} Unsigs displayed {EMOJI_ARROW_DOWN}", value=selected_str, inline=False)

    return embed

def embed_siblings(number, siblings, selected, offers, cols=2):
    asset_name = get_asset_name_from_idx(number)

    title = f"{EMOJI_DNA} siblings {asset_name} {EMOJI_DNA}"
    description="Siblings of your unsig"
    color=discord.Colour.dark_blue()

    embed = discord.Embed(title=title, description=description, color=color)

    if offers:
        offers_str = ""
        offers_numbers = get_numbers_from_assets(offers)
        siblings_offers = [num for num in siblings if num in offers_numbers]
        if siblings_offers:
            for num in siblings_offers:
                offer = get_asset_from_number(num, offers)
                price = offer.get("price")/1000000
                marketplace_id = offer.get("id")
                marketplace = offer.get("marketplace")
                siblings_str = link_asset_to_marketplace(num, marketplace_id, marketplace)
                offers_str += f"{siblings_str} for **₳{price:,.0f}**\n"
        else:
            offers_str = "` - `"
    else:
        offers_str = "` - `"

    embed.add_field(name="on marketplace", value=offers_str, inline=False)

    if siblings:
        collection_str = ""
        for num in siblings:
            collection_str += f"#{str(num).zfill(5)}\n"
    else:
        collection_str = "` - `"

    embed.add_field(name="in ENTIRE collection", value=collection_str, inline=False)

    if siblings:
        displayed_str = ""

        for i, num in enumerate(selected):
            displayed_str += f" #{str(num).zfill(5)} "

            if (i+1) % cols == 0:
                displayed_str += "\n"

        embed.add_field(name=f"{EMOJI_ARROW_DOWN} Unsigs displayed {EMOJI_ARROW_DOWN}", value=displayed_str, inline=False)

    return embed

def embed_pattern_combo(pattern_found: list, search_input: list, to_display: list, cols=3):
    num_found = len(pattern_found)

    subs_frequencies = load_json("data/json/subs_frequencies.json")
    search_formatted = dict(Counter(search_input))
   
    pattern_str = " + \n".join([f"{amount} x {pattern}" for pattern, amount in search_formatted.items()])
  
    title = f"{EMOJI_LINK} Pattern combo {EMOJI_LINK}"
    description=f"**{num_found}** unsigs with this pattern combo:\n`{pattern_str}`"
    color=discord.Colour.dark_blue()

    embed = discord.Embed(title=title, description=description, color=color)

    
    for sub, amount in search_formatted.items():
        frequency = subs_frequencies.get(sub).get(str(amount), 0)
        embed.add_field(name=f"{amount} x {sub}", value=f"**{frequency} / 31119** unsigs contain this subpattern", inline=False)

    if to_display:
        unsigs_str=link_assets_to_grid(to_display, cols)
        embed.add_field(name=f"{EMOJI_ARROW_DOWN} Random selection {EMOJI_ARROW_DOWN}", value=unsigs_str, inline=False)

    return embed

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

        #TODO: Add more certificate information

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


def embed_output_colors(number, color_frequencies):
    asset_name = get_asset_name_from_idx(number)
    
    num_colors = get_total_colors(color_frequencies)

    title = f"{EMOJI_PALETTE} colors {asset_name} {EMOJI_PALETTE} "
    description=f"Unsig has **{num_colors} / 64** output colors"
    color=discord.Colour.dark_blue()

    unsig_url = get_unsig_url(number)

    embed = discord.Embed(title=title, description=description, color=color, url=unsig_url)

    add_output_colors(embed, color_frequencies)

    return embed

def embed_color_ranking():
    title = f"{EMOJI_PALETTE} Color Rarities {EMOJI_PALETTE} "
    description=f"based on cumulative pixel amount in whole collection"
    color=discord.Colour.dark_blue()

    embed = discord.Embed(title=title, description=description, color=color)

    total_pixels = sum(PIXELS_COLORS.values())

    ordered_ranking = sorted(COLOR_RANKING.items(), key=lambda x:x[1], reverse=False)

    color_ranking_list = list()
    for i, (color, rank) in enumerate(ordered_ranking):
        color_hex = rgb_2_hex(color)
        color_link = link_hex_color(color_hex)
        pixels = PIXELS_COLORS.get(color)
        percentage = pixels / total_pixels
        color_ranking_list.append(f" `{rank}.`[{color_hex}]({color_link}), **{percentage:.2%}**\n")

    PARTS = 8
    splitted = np.array_split(color_ranking_list, PARTS)
    for i, part in enumerate(splitted):
        if i == 0:
            title = f"{EMOJI_ARROW_DOWN} Rarity Ranking {EMOJI_ARROW_DOWN}"
        else: 
            title = "..."
        
        part_str = "".join(part)

        embed.add_field(name=title, value=part_str, inline=False)

    return embed


# @slash.slash(
#     name="firework", 
#     description="A new era begins...", 
#     guild_ids=GUILD_IDS
# )
# async def firework(ctx: SlashContext):
#     title = f"{EMOJI_PARTY} Quantum of v2 {EMOJI_PARTY}"
#     description="A new era begins..."
#     color=discord.Colour.purple()

#     embed = discord.Embed(title=title, description=description, color=color)

#     embed.set_image(url="https://media.giphy.com/media/26tOZ42Mg6pbTUPHW/giphy.gif")

#     await ctx.send(embed=embed)

@slash.slash(
    name="verse", 
    description="One unsig to rule them all...", 
    guild_ids=GUILD_IDS,
)
async def verse(ctx: SlashContext):
    title = f"{EMOJI_CERT} Unsig verse {EMOJI_CERT}"
    description="..."
    color=discord.Colour.dark_blue()

    embed = discord.Embed(title=title, description=description, color=color) 

    verse = """Two distributions for the algorithm in numpy
        Three fundamental colours which set the tone
        Four numbers for the values to multiply
        Four rotations as the quarters of a circle have shown
        
        In the unsig land, 
        where all combined layers lie...
        One unsig to rule them all, 
        One unsig to find them
        One unsig to bring them all, 
        and in its darkness bind them
        """
    embed.add_field(name="One unsig to rule them all", value=f"{verse}", inline=False)

    image_url = await get_ipfs_url_from_file("unsig00000")
    embed.set_image(url=image_url)
    
    await ctx.send(embed=embed)


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
    "analysis": {
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
        },
        "pattern-combo": {
            "syntax": "/pattern-combo",
            "hint": "count unsigs with given pattern combo"
        },
        "forms": {
            "syntax": "/forms",
            "hint": "show unsigs with given form"            
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
    name="siblings", 
    description="show siblings of your unsig", 
    guild_ids=GUILD_IDS,
    options=[
        create_option(
            name="number",
            description="number of your unsig",
            required=True,
            option_type=3,
        )
    ]    
)
async def siblings(ctx: SlashContext, number: str):
        
    if ctx.channel.name == "general":
        await ctx.send(content=f"I'm not allowed to post here.\n Please go to #bot channel.")
        return

    asset_name = get_asset_name_from_idx(number)

    if not unsig_exists(number):
        await ctx.send(content=f"{asset_name} does not exist!\nPlease enter number between 0 and {MAX_AMOUNT}.")
        return
    else:

        collection_numbers = range(0,31119)

        similar_unsigs = get_similar_unsigs(number, collection_numbers, structural=False)

        siblings_numbers = list(set().union(*similar_unsigs.values()))

        selected_numbers = siblings_numbers[:]
        selected_numbers.insert(0, int(number))

        embed = embed_siblings(number, siblings_numbers, selected_numbers, bot.offers, cols=2)

        if bot.offers and siblings_numbers:
            add_disclaimer(embed, bot.offers_updated)

        if not siblings_numbers:
            await ctx.send(embed=embed)
            return

        try:
            image_path = f"img/grid_{''.join(map(str, selected_numbers))}.png"
            
            await gen_grid(selected_numbers, cols=2)

            image_file = discord.File(image_path, filename="siblings.png")
            if image_file:
                embed.set_image(url="attachment://siblings.png")
            delete_image_files(IMAGE_PATH)
        except:
            await ctx.send(content=f"I can't generate the siblings of your unsig.")
            return
        else:
            await ctx.send(file=image_file, embed=embed)


@slash.slash(
    name="like", 
    description="show related unsigs sold", 
    guild_ids=GUILD_IDS,
    options=[
        create_option(
            name="number",
            description="number of your unsig",
            required=True,
            option_type=3,
        )
    ]    
)
async def like(ctx: SlashContext, number: str):
        
    if ctx.channel.name == "general":
        await ctx.send(content=f"I'm not allowed to post here.\n Please go to #bot channel.")
        return

    asset_name = get_asset_name_from_idx(number)

    if not unsig_exists(number):
        await ctx.send(content=f"{asset_name} does not exist!\nPlease enter number between 0 and {MAX_AMOUNT}.")
        return
    else:
        if bot.sales:
            sales_numbers = get_numbers_from_assets(bot.sales)
            sales_by_date = sort_sales_by_date(bot.sales, descending=True)

            similar_unsigs = get_similar_unsigs(number, sales_numbers)

            related_numbers = list(set().union(*similar_unsigs.values()))

            LIMIT_DISPLAY = 8
            related_numbers = related_numbers[:LIMIT_DISPLAY]
            selected_numbers = related_numbers[:]
            selected_numbers.insert(0, int(number))

            embed = embed_related(number, related_numbers, selected_numbers, sales_by_date, cols=3)

            add_disclaimer(embed, bot.sales_updated)

            if not related_numbers:
                await ctx.send(embed=embed)
                return

            try:
                image_path = f"img/grid_{''.join(map(str, selected_numbers))}.png"
                
                await gen_grid(selected_numbers, cols=3)

                image_file = discord.File(image_path, filename="related.png")
                if image_file:
                    embed.set_image(url="attachment://related.png")
                delete_image_files(IMAGE_PATH)
            except:
                await ctx.send(content=f"I can't generate the related of your unsig.")
                return
            else:
                await ctx.send(file=image_file, embed=embed)

        else:
            await ctx.send(content=f"Currently no sales data available...")
            return

@slash.slash(
    name="matches", 
    description="show available matches on marketplace", 
    guild_ids=GUILD_IDS,
    options=[
        create_option(
            name="number",
            description="number of unsig you want to match",
            required=True,
            option_type=3,
        )
    ]    
)
async def matches(ctx: SlashContext, number: str):
        
    if ctx.channel.name == "general":
        await ctx.send(content=f"I'm not allowed to post here.\n Please go to #bot channel.")
        return

    asset_name = get_asset_name_from_idx(number)

    if not unsig_exists(number):
        await ctx.send(content=f"{asset_name} does not exist!\nPlease enter number between 0 and {MAX_AMOUNT}.")
        return
    else:
        if bot.offers:
            offers_numbers = get_numbers_from_assets(bot.offers)

            matches = match_unsig(number, offers_numbers)
            best_matches = choose_best_matches(number, matches)

            embed = embed_matches(number, matches, best_matches, bot.offers)

            add_disclaimer(embed, bot.offers_updated)

            try:
                image_path = f"img/matches_{int(number)}.png"
                
                await gen_grid_with_matches(best_matches)

                image_file = discord.File(image_path, filename="matches.png")
                if image_file:
                    embed.set_image(url="attachment://matches.png")
                delete_image_files(IMAGE_PATH)
            except:
                await ctx.send(content=f"I can't generate the matches of your unsig.")
                return
            else:
                await ctx.send(file=image_file, embed=embed)

        else:
            await ctx.send(content=f"Currently no marketplace data available...")
            return


@slash.slash(
    name="floor", 
    description="show cheapest unsigs on marketplace", 
    guild_ids=GUILD_IDS
)
async def floor(ctx: SlashContext):
        
    if ctx.channel.name != "bot":
        await ctx.send(content=f"I'm not allowed to post here.\n Please go to #bot channel.")
        return
    
    if bot.offers:
        filtered = filter_assets_by_type(bot.offers, "listing", "offer", "Buy")
        ordered_by_props = order_by_num_props(filtered)

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
                price_str = "???"
            else:
                price_str = f"₳{price:,.0f}"

        embed.add_field(name=f"{EMOJI_MONEYBAG} Price", value=price_str, inline=True)

        add_minting_order(embed, minting_data)

        add_num_props(embed, unsigs_data)

        image_url = await get_ipfs_url_from_file(asset_name)

        if image_url:
            embed.set_image(url=image_url)

        embed.set_footer(text=f"\nAlways check policy id:\n{POLICY_ID}")
 
        await ctx.send(embed=embed)

@slash.slash(
    name="cert", 
    description="show certificate data of your unsig", 
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
async def cert(ctx: SlashContext, number: str):
        
    if ctx.channel.name == "general":
        await ctx.send(content=f"I'm not allowed to post here.\n Please go to #bot channel.")
        return

    asset_name = get_asset_name_from_idx(number)

    if not unsig_exists(number):
        await ctx.send(content=f"{asset_name} does not exist!\nPlease enter number between 0 and {MAX_AMOUNT}.")
    else:
        number = str(int(number))

        certificates = load_json("data/json/certificates.json")
        num_certificates = len(certificates)

        data = get_certificate_data_by_number(number, certificates)

        try:
            embed = embed_certificate(number, data, num_certificates)
        except:
            await ctx.send(content=f"I can't embed certificate for your unsig.")
        else:
            await ctx.send(embed=embed)


@slash.slash(
    name="color-ranking", 
    description="show color ranking", 
    guild_ids=GUILD_IDS
)
async def color_ranking(ctx: SlashContext):
        
    if ctx.channel.name == "general":
        await ctx.send(content=f"I'm not allowed to post here.\n Please go to #bot channel.")
        return

    embed = embed_color_ranking()

    try:
        image_path = "img/color_freqs.jpg" 
        image_file = discord.File(image_path, filename="image.jpg")
        if image_file:
            embed.set_image(url="attachment://image.jpg")
    except:
        await ctx.send(content=f"I can't generate color ranking.")
        return
    else:
        await ctx.send(file=image_file, embed=embed)


@slash.slash(
    name="colors", 
    description="show output colors of given unsig", 
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
async def colors(ctx: SlashContext, number: str):
        
    if ctx.channel.name == "general":
        await ctx.send(content=f"I'm not allowed to post here.\n Please go to #bot channel.")
        return

    asset_name = get_asset_name_from_idx(number)

    if not unsig_exists(number):
        await ctx.send(content=f"{asset_name} does not exist!\nPlease enter number between 0 and {MAX_AMOUNT}.")
    else:

        number = str(int(number))

        color_frequencies = get_color_frequencies(number)

        embed = embed_output_colors(number, color_frequencies)

        embed.set_footer(text=f"\nDiscord Bot by Mar5man")

        try:
            image_path = await gen_color_histogram(number, color_frequencies)
            image_file = discord.File(image_path, filename="image.png")
            if image_file:
                embed.set_image(url="attachment://image.png")
            delete_image_files(IMAGE_PATH)
        except:
            await ctx.send(content=f"I can't generate color histogram of your unsig.")
            return
        else:
            await ctx.send(file=image_file, embed=embed)

@slash.slash(
    name="forms", 
    description="show unsigs with given form", 
    guild_ids=GUILD_IDS,
    options=[
        create_option(
            name="form",
            description="visible pattern of unsig",
            required=True,
            option_type=3,
            choices=[create_choice(name=name, value=name) for name in SUBPATTERN_NAMES]
        )
    ]
)
async def forms(ctx: SlashContext, form: str):
        
    if ctx.channel.name == "general":
        await ctx.send(content=f"I'm not allowed to post here.\n Please go to #bot channel.")
        return
    
    subs_advanced = load_json("data/json/subs_advanced.json")

    form_selected = subs_advanced.get(form)
    if not form_selected:
        if form == "basketball":
            clean_form = subs_advanced.get("bulb").get("diagonal")
        if form == "butterfly":
            clean_form = subs_advanced.get("window").get("bulb")
    else:
        clean_form = form_selected.get("clean")

    num_found = len(clean_form)

    emoji = FORMS_EMOJIS.get(form)
    p = inflect.engine()
    form_name = p.plural(form)
    if form == "rivers" or form == "veins":
        form_name = form

    title = f"{emoji} {form_name} {emoji}"
    description=f"**{num_found}** clean {form_name} in whole collection"
    color=discord.Colour.dark_blue()

    embed = discord.Embed(title=title, description=description, color=color)

    embed.set_footer(text=f"\nDiscord Bot by Mar5man")

    try:
        image_path = f"img/{form}.jpg" 
        image_file = discord.File(image_path, filename="image.jpg")
        if image_file:
            embed.set_image(url="attachment://image.jpg")
    except:
        await ctx.send(content=f"I can't display unsig forms.")
        return
    else:
        await ctx.send(file=image_file, embed=embed)  


@slash.slash(
    name="metadata", 
    description="show metadata of your unsig", 
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
        await ctx.send(content=f"I'm not allowed to post here.\n Please go to #bot channel.")
        return

    asset_name = get_asset_name_from_idx(number)

    if not unsig_exists(number):
        await ctx.send(content=f"{asset_name} does not exist!\nPlease enter number between 0 and {MAX_AMOUNT}.")
    else:

        number = str(int(number))

        metadata = get_metadata_from_asset_name(asset_name)

        if metadata:
            embed = await embed_metadata(metadata)
            embed.set_footer(text=f"\nData comes from {POOL_PM_URL}")

            await ctx.send(embed=embed)
            return
        else:
            await ctx.send(content=f"I can't find the metadata of your unsig!")

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

        unsigs_data = get_unsigs_data(number)

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
                image_path = f"img/animation_{number}.gif"
                
                await gen_animation(number, mode=animation, backwards=True)

                image_file = discord.File(image_path, filename="image.gif")
                if image_file:
                    embed.set_image(url="attachment://image.gif")
                delete_image_files(IMAGE_PATH, suffix="gif")
            except:
                print("Animation failed!")
                pass
            else:
                embed.set_footer(text=f"\nDiscord Bot by Mar5man")
                await ctx.send(file=image_file, embed=embed)
                return 

        image_url = await get_ipfs_url_from_file(asset_name)

        if image_url:
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
    name="pattern-combo", 
    description="count unsigs with given pattern combo", 
    guild_ids=GUILD_IDS,
    options=[
        create_option(
            name="first_pattern",
            description="1st subpattern",
            required=True,
            option_type=3,
            choices=[create_choice(name=name, value=name) for name in SUBPATTERN_NAMES]
        ),
        create_option(
            name="second_pattern",
            description="2nd subpattern",
            required=False,
            option_type=3,
            choices=[create_choice(name=name, value=name) for name in SUBPATTERN_NAMES]
        ),
        create_option(
            name="third_pattern",
            description="3rd subpattern",
            required=False,
            option_type=3,
            choices=[create_choice(name=name, value=name) for name in SUBPATTERN_NAMES]
        ),
    ]
)
async def pattern_combo(ctx: SlashContext, first_pattern: str, second_pattern: str = None, third_pattern: str = None):
        
    if ctx.channel.name == "general":
        await ctx.send(content=f"I'm not allowed to post here.\n Please go to #bot channel.")
        return

    pattern = [first_pattern, second_pattern, third_pattern]

    pattern_for_search = [p for p in pattern if p in SUBPATTERN_NAMES]

    subs_counted = load_json("data/json/subs_counted.json")

    pattern_found = filter_subs_by_names(subs_counted, pattern_for_search)

    LIMIT_DISPLAY = 9

    if len(pattern_found) <= LIMIT_DISPLAY:
        to_display = pattern_found
        cols = math.ceil(math.sqrt(len(to_display)))
    else:
        to_display = random.sample(pattern_found, LIMIT_DISPLAY)
        cols = math.ceil(math.sqrt(LIMIT_DISPLAY))


    embed = embed_pattern_combo(pattern_found, pattern_for_search, to_display, cols)
    embed.set_footer(text=f"\nDiscord Bot by Mar5man")

    if to_display:
        try:
            image_path = f"img/grid_{''.join(to_display)}.png"
            
            await gen_grid(to_display, cols)

            image_file = discord.File(image_path, filename="grid.png")
            if image_file:
                embed.set_image(url="attachment://grid.png")
            delete_image_files(IMAGE_PATH)
        except:
            await ctx.send(content=f"I can't display the selection of unsigs.")
            return
        else:
            await ctx.send(file=image_file, embed=embed)
    else:
        await ctx.send(embed=embed)


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
        
    if ctx.channel.name == "general":
        await ctx.send(content=f"I'm not allowed to post here.\n Please go to #bot channel.")
        return

    asset_name = get_asset_name_from_idx(number)

    if not unsig_exists(number):
        await ctx.send(content=f"{asset_name} does not exist!\nPlease enter number between 0 and {MAX_AMOUNT}.")
    else:

        number = str(int(number))

        unsig_data = get_unsigs_data(number)

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
            image_path = f"img/subpattern_{number}.png"
            
            await gen_subpattern(number)

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

        add_subs(embed, number)

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

        number = str(get_idx_from_asset_name(asset_name))
        unsig_url = get_unsig_url(number)

        unsigs_data = get_unsigs_data(number)
      
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

# bot.load_extension(f"unsigned_bot.cogs.cog")

# def main():
#     pass

if __name__ == "__main__":
    
    bot.run(TOKEN)

