"""
Module for ownership cog
"""

import discord
from discord import Embed, Colour
from discord.ext import commands
from discord_slash import cog_ext, SlashContext
from discord_slash.utils.manage_commands import create_choice, create_option

from unsigned_bot.config import GUILD_IDS
from unsigned_bot.constants import MAX_AMOUNT
from unsigned_bot.log import logger
from unsigned_bot.emojis import *
from unsigned_bot.urls import POOL_PM_URL
from unsigned_bot.fetch import get_current_owner_address
from unsigned_bot.parsing import (
    get_asset_name_from_idx,
    get_asset_id,
    unsig_exists
)
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

        if ctx.channel.name == "general":
            await ctx.send(content=f"I'm not allowed to post here.\n Please go to #bot channel.")
            return 

        asset_name = get_asset_name_from_idx(number)

        if not unsig_exists(number):
            await ctx.send(content=f"{asset_name} does not exist!\nPlease enter number between 0 and {MAX_AMOUNT-1}.")
        else:
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