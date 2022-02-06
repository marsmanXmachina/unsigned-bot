"""
Module for checks during cog interaction
"""

from typing import Optional
from discord_slash import SlashContext

from unsigned_bot.constants import MAX_AMOUNT
from unsigned_bot.parsing import (
    unsig_exists,
    get_asset_name_from_idx
)


async def valid_channel(ctx: SlashContext, allowed: Optional[str] = "bot") -> bool:
    """Check if channel is allowed for interaction and send message to channel if not."""

    FORBIDDEN_CHANNELS = ["general"]

    channel_name = ctx.channel.name
    if channel_name.lower() in FORBIDDEN_CHANNELS:
        await ctx.send(content=f"I'm not allowed to post here.\nPlease go to #{allowed} channel.")
        return False
    return True

async def valid_unsig(ctx: SlashContext, number: str) -> bool:
    """Check number of unsig and send message to channel if it not exists"""

    if not unsig_exists(number):
        asset_name = get_asset_name_from_idx(number)
        await ctx.send(content=f"{asset_name} does not exist!\nPlease enter number between 0 and {MAX_AMOUNT-1}.")
        return False
    return True