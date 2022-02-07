"""
Module for ownership cog
"""

import discord
from discord import Embed, Colour
from discord.ext import commands
from discord_slash import cog_ext, SlashContext
from discord_slash.utils.manage_commands import create_choice, create_option

from unsigned_bot.config import GUILD_IDS
from unsigned_bot.log import logger
from unsigned_bot.emojis import *
from unsigned_bot.fetch import get_current_owner_address
from unsigned_bot.parsing import (
    get_asset_name_from_idx,
    get_asset_id
)
from unsigned_bot.cogs.checks import valid_channel, valid_unsig
from .embeds import embed_owners_wallet


class OwnershipCog(commands.Cog, name = "Ownership"):
    """commands for checking ownership"""

    COG_EMOJI = EMOJI_KEY

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @cog_ext.cog_slash(
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
    async def _owner(self, ctx: SlashContext, number: str):
        """show wallet of unsig with given number"""

        if not await valid_channel(ctx):
            return

        if not await valid_unsig(ctx, number):
            return

        asset_name = get_asset_name_from_idx(number)
        asset_id = get_asset_id(asset_name)

        owner_address_data = get_current_owner_address(asset_id)
        if owner_address_data:
            address = owner_address_data.get("name")

            embed = embed_owners_wallet(address, asset_name)

            await ctx.send(embed=embed)
        else:
            await ctx.send(content=f"Sorry...I can't get the data for `{asset_name}` at the moment!")


def setup(bot: commands.Bot):
    bot.add_cog(OwnershipCog(bot))
    logger.debug(f"{OwnershipCog.__name__} loaded")