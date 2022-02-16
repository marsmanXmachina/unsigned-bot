"""
Module for data cog specific discord embeds
"""

import pprint
from collections import Counter
import discord
from discord import Embed, Colour

from unsigned_bot import ROOT_DIR
from unsigned_bot.utility.files_util import load_json
from unsigned_bot.utility.time_util import timestamp_to_datetime
from unsigned_bot.constants import MAX_AMOUNT
from unsigned_bot.emojis import *
from unsigned_bot.urls import *
from unsigned_bot.colors import (
    COLOR_RANKING,
    get_top_colors,
    rgb_2_hex,
    link_hex_color,
    calc_color_rarity
)
from unsigned_bot.deconstruct import (
    get_prop_layers,
    get_subpattern,
    get_subpattern_names,
    filter_subs_by_names
)
from unsigned_bot.fetch import get_minting_tx_id
from unsigned_bot.parsing import (
    get_asset_id,
    get_idx_from_asset_name,
    get_unsig_url,
    filter_sales_by_asset,
    sort_sales_by_date
)
from unsigned_bot.embedding import add_props, add_num_props, add_minting_order


def embed_basic_info(number: str, asset_name: str, unsigs_data: dict, minting_data: tuple, sales: list) -> Embed:
    """Return discord embed for unsig info"""

    unsig_url = get_unsig_url(number)

    title = f"{asset_name}"
    description="minted by unsigned_algorithms"
    color=discord.Colour.dark_blue()
    embed = discord.Embed(title=title, description=description, color=color, url=unsig_url)

    add_minting_order(embed, minting_data)

    if sales:
        past_sales = filter_sales_by_asset(sales, asset_name)
        sales_by_date = sort_sales_by_date(past_sales, descending=True)

        if past_sales:
            add_sales(embed, sales_by_date)

    add_num_props(embed, unsigs_data)
    add_props(embed, unsigs_data)

    return embed
    
async def embed_metadata(metadata: dict) -> Embed:
    """Return discord embed with metadata of unsig"""
    
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

def embed_certificate(number: str, data: dict, num_certificates: int, feed=False) -> Embed:
    """Return discord embed for certificates"""

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
        color = Colour.dark_blue()
        embed = Embed(title=title, description=description, color=color, url=certificate_link)
    else:
        title = f"{EMOJI_CROSS} No cert found for unsig{number.zfill(5)} {EMOJI_CROSS}"
        description=f"**{num_certificates}** certificates already minted\n"
        color = Colour.dark_blue()
        embed = Embed(title=title, description=description, color=color)
    
    if data:
        mint_date = metadata.get("Unsig mint date")
        embed.add_field(name=f"{EMOJI_PICK} Minted on", value=f"`{mint_date}`", inline=True)

        assessment_date = metadata.get("Assessment date")
        embed.add_field(name=f"{EMOJI_CHECK} Certified on", value=f"`{assessment_date}`", inline=True)

        embed.set_image(url=image_link)

    embed.add_field(name=f"{EMOJI_CART} Order your unsig certificate {EMOJI_CART}", value=f"{EMOJI_ARROW_RIGHT} visit [CNFT_ART's discord]({DISCORD_CNFT_ART})", inline=False)

    return embed

def add_subpattern(embed: Embed, unsig_data: dict):
    """Add subpattern to discord embed"""
    
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

    pattern_for_search = list(subpattern_names.values())
    pattern_found = filter_subs_by_names(pattern_for_search)
    num_pattern = len(pattern_found)
    pattern_formatted = dict(Counter(pattern_for_search))

    pattern_combo_str = " + \n".join([f" {amount} x {pattern}" for pattern, amount in pattern_formatted.items()])

    if layers:
        frequency_str = f"\n=> **{num_pattern} / {MAX_AMOUNT}** unsigs with this pattern combo"
    else:
        frequency_str = ""

    embed.add_field(name = f"{EMOJI_LINK} Pattern combo {EMOJI_LINK}", value=f"`{pattern_combo_str}`\n{frequency_str}", inline=False)

    return embed

def add_output_colors(embed: Embed, color_frequencies: dict, num_colors: int = 10):
    """Add output colors to discord embed"""

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

def add_sales(embed: Embed, sales: list):
    """Add sales to discord embed"""

    sales_value = ""
    for sale in sales:
        price = sale.get('price')/1000000
        timestamp_ms = sale.get('date')
        date = timestamp_to_datetime(timestamp_ms).date()

        sales_value += f"sold on **{date}** for **₳{price:,.0f}**\n"

    embed.add_field(name=f"{EMOJI_SHOPPINGBAGS} Past sales", value=sales_value, inline=False)