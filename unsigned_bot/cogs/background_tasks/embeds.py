"""
Module for background tasks cog specific discord embeds
"""

from datetime import datetime
from discord import Embed, Colour

from unsigned_bot.emojis import *
from unsigned_bot.urls import *
from unsigned_bot.fetch import get_ipfs_url_from_file
from unsigned_bot.embedding import list_marketplace_base_urls


async def embed_sale(sale_data: dict) -> Embed:
    """Return discord embed for sale"""

    asset_name = sale_data.get("assetid")

    title = f"{EMOJI_CART} {asset_name} {EMOJI_CART}"
    description="minted by unsigned_algorithms"
    color = Colour.dark_blue()

    embed = Embed(title=title, description=description, color=color)

    price = sale_data.get("price")
    price = price/1000000
    embed.add_field(name=f"{EMOJI_MONEYBAG} Price", value=f"₳{price:,.0f}", inline=True)

    timestamp_ms = sale_data.get("date")
    date = datetime.utcfromtimestamp(timestamp_ms/1000).strftime("%Y-%m-%d %H:%M:%S UTC")
    embed.add_field(name=f"{EMOJI_CALENDAR} Sold on", value=date, inline=True)

    marketplace = sale_data.get("marketplace")
    embed.add_field(name=f"{EMOJI_PIN} Marketplace", value=f"`{marketplace.upper()}`", inline=False)

    image_url = await get_ipfs_url_from_file(asset_name)

    if image_url:
        embed.set_image(url=image_url)

    embed.set_footer(text=f"Data comes from \n{list_marketplace_base_urls()}")

    return embed