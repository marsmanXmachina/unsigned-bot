"""
Module for ownership cog specific discord embeds
"""

from discord import Embed, Colour
from unsigned_bot.urls import POOL_PM_URL


def embed_owners_wallet(address, asset_name) -> Embed:
    """Return discord embed of wallet owner"""

    title = f"{asset_name} is owned by"
    description = f"`{address}`"
    color = Colour.blurple()

    embed = Embed(title=title, description=description, color=color)

    name = "This address belongs to wallet..."
    value = f"{POOL_PM_URL}/{address}/0e14267a"
    embed.add_field(name=name, value=value, inline=False)

    embed.set_footer(text=f"Data comes from {POOL_PM_URL}")

    return embed