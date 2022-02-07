"""
Module for market cog specific discord embeds
"""

from random import sample
import discord
from discord import Embed, Colour
from typing import Optional

from unsigned_bot.utility.time_util import timestamp_to_datetime
from unsigned_bot.utility.price_util import get_average_price, get_min_prices
from unsigned_bot.constants import POLICY_ID
from unsigned_bot.emojis import *
from unsigned_bot.parsing import (
    get_asset_name_from_idx,
    get_idx_from_asset_name,
    get_asset_from_number,
    order_by_num_props, 
    get_unsig_url,
    get_url_from_marketplace_id
)
from unsigned_bot.embedding import add_num_props, add_minting_order


def embed_sales(assets: list, prices_type: str, period: Optional[str]) -> Embed:
    """Return discord embed for sales on marketplace"""

    period_str = f"last {period}" if period else "all-time"

    if prices_type == "highest":
        title = f"{EMOJI_MONEYWINGS} Highest sales {period_str} {EMOJI_MONEYWINGS}"
    else:
        title = f"{EMOJI_CART} Average sales {period_str} {EMOJI_CART}"

    description=f"**{len(assets)}** sold on marketplace"
    color = Colour.dark_blue()
    embed = Embed(title=title, description=description, color=color)

    ordered = order_by_num_props(assets)
    for idx in range(7):
        assets_props = ordered.get(idx, None)

        if assets_props:
            sales_str = ""
            num_sold_props = len(assets_props)

            if prices_type == "highest":
                sorted_by_price = sorted(assets_props, key=lambda x:x['price'], reverse=True)
                
                for j in range(3):
                    try:
                        max_priced = sorted_by_price[j]
                    except:
                        continue
                    else:
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

def embed_related(number: str, related: list[int], selected: list[int], sales: list, cols=3) -> Embed:
    """Return discord embed for related unsigs sold on marketplace"""

    asset_name = get_asset_name_from_idx(number)

    title = f"{EMOJI_MIRROW} like {asset_name} {EMOJI_MIRROW}"
    description="Related unsigs sold"
    color = Colour.dark_blue()
    embed = Embed(title=title, description=description, color=color)

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

            related_str += f"#{str(asset_number).zfill(5)} sold for **₳{price:,.0f}** on {dt.date()}\n"

    embed.add_field(name=f"Sales of similar unsigs", value=related_str, inline=False)

    if related:
        displayed_str = ""
        for i, num in enumerate(selected):
            displayed_str += f" #{str(num).zfill(5)} "

            if (i+1) % cols == 0:
                displayed_str += "\n"

        embed.add_field(name=f"{EMOJI_ARROW_DOWN} Unsigs displayed {EMOJI_ARROW_DOWN}", value=displayed_str, inline=False)

    return embed

def embed_matches(number: str, matches: list[int], best_matches: list[int], offers: list, entire_collection=False) -> Embed:
    """Return discord embed for matches on marketplace"""

    asset_name = get_asset_name_from_idx(number)

    title = f"{EMOJI_PUZZLE} {asset_name} matches {EMOJI_PUZZLE}"
    if entire_collection:
        description="Available matches in ENTIRE collection"
    else:
        description="Available matches on marketplace"
    color = Colour.dark_blue()
    embed = Embed(title=title, description=description, color=color)

    def link_match_to_marketplace(match, offers: list) -> str:
        offer = get_asset_from_number(match, offers)
        offer_id = offer.get("id")
        marketplace = offer.get("marketplace")
        marketplace_url = get_url_from_marketplace_id(offer_id, marketplace)
        return f" [#{str(match).zfill(5)}]({marketplace_url}) "

    SIDES = ["top", "left", "right", "bottom"]
    for side in SIDES:
        arrow = ARROWS.get(side)

        matches_side = matches.get(side, None)
        if matches_side:

            if entire_collection:
                shuffled = sample(matches_side, len(matches_side))
                matches_side = shuffled[:9]
                rest = shuffled[9:] if len(shuffled) > 9 else 0

            matches_str = ""
            for match in matches_side:
                if entire_collection:
                    unsigs_url = get_unsig_url(match)
                    matches_str += f" [#{str(match).zfill(5)}]({unsigs_url}) "
                else:
                    match_str = link_match_to_marketplace(match, offers)
                    matches_str += match_str
                    
            if entire_collection:
                matches_str += f"...and {len(rest)} more"
        else:
            matches_str = "` - `"
        
        embed.add_field(name=f"{arrow} {side.upper()} {arrow}", value=matches_str, inline=False)

    UNSIG_MATCHBOX_LINK = "https://www.fibons.io/unsigs/services/"
    matchbox_text = f"For deeper analysis checkout [unsig_matchbox]({UNSIG_MATCHBOX_LINK})"

    embed.add_field(name=f"{EMOJI_GLASS} Portfolio Analysis {EMOJI_GLASS}", value=matchbox_text, inline=False)
    
    best_matches_str=""
    for side in SIDES:
        best_match = best_matches.get(side, None)
        if best_match:
            if entire_collection:
                unsigs_url = get_unsig_url(best_match)
                best_match_str = f" [#{str(best_match).zfill(5)}]({unsigs_url}) "  
            else:
                best_match_str = link_match_to_marketplace(best_match, offers)
        else:
            best_match_str = "` - `"

        arrow = ARROWS.get(side)
        best_matches_str += f"{arrow} {best_match_str}\n" 

    embed.add_field(name="Matches displayed", value=best_matches_str)

    return embed

def embed_offers(assets_ordered: dict) -> Embed:
    """Return discord embed for offers on marketplace"""

    title = f"{EMOJI_BROOM} Unsigs Floor {EMOJI_BROOM}"
    description="Cheapest unsigs on marketplace\n(auctions excluded)"
    color = Colour.dark_blue()
    embed = Embed(title=title, description=description, color=color)

    for idx in range(7):
        assets = assets_ordered.get(idx, None)
        if assets:
            num_assets = len(assets)
            low_priced_assets = get_min_prices(assets)
            min_price = None

            offers_str = ""
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

async def embed_offer(seller: str, price: Optional[str], asset_name: str, unsig_data: dict, minting_data: tuple) -> Embed:
    """Return discord embed for unsig offer"""

    title = f"{EMOJI_SHOPPINGBAGS} {asset_name} for sale {EMOJI_SHOPPINGBAGS}"
    description="Are you interested in this beautiful unsig?"
    color=discord.Colour.dark_blue()
    embed = discord.Embed(title=title, description=description, color=color)

    embed.add_field(name=f"{EMOJI_PERSON} Seller", value=seller, inline=False)

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
    add_num_props(embed, unsig_data)

    embed.set_footer(text=f"\nAlways check policy id:\n{POLICY_ID}")

    return embed