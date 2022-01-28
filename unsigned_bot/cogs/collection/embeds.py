"""
Module for collection cog specific discord embeds
"""
from discord import Embed, Colour


from unsigned_bot.emojis import *

from unsigned_bot.parsing import (
    get_asset_name_from_idx,
    get_numbers_from_assets,
    get_asset_from_number,
    link_asset_to_marketplace
)


def embed_siblings(number: str, siblings: list, selected: list, offers: list, cols=2) -> Embed:
    """Return discord embed for siblings on marketplace and in whole collection"""

    asset_name = get_asset_name_from_idx(number)

    title = f"{EMOJI_DNA} siblings {asset_name} {EMOJI_DNA}"
    description="Siblings of your unsig"
    color=Colour.dark_blue()

    embed = Embed(title=title, description=description, color=color)

    if offers:
        offers_numbers = get_numbers_from_assets(offers)
        siblings_offers = [num for num in siblings if num in offers_numbers]

        offers_str = ""
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