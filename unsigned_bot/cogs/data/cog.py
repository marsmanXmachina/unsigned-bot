"""
Module for unsig data cog
"""

import discord
from discord.ext import commands
from discord_slash import cog_ext, SlashContext
from discord_slash.utils.manage_commands import create_choice, create_option

from unsigned_bot import ROOT_DIR
from unsigned_bot.utility.files_util import load_json
from unsigned_bot.config import GUILD_IDS
from unsigned_bot.constants import MAX_AMOUNT
from unsigned_bot.fetch import get_metadata_from_asset_name
from unsigned_bot.parsing import (
    get_asset_name_from_idx,
    get_certificate_data_by_number,
    unsig_exists
)
from unsigned_bot.urls import POOL_PM_URL
from unsigned_bot.embedding import add_last_update
from .embeds import embed_metadata, embed_certificate


class Data(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # @cog_ext.cog_slash(

    # )    

    @cog_ext.cog_slash(
        name="metadata", 
        description="show metadata of your unsig", 
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
    async def _metadata(self, ctx: SlashContext, number: str):
        """show metadata of your unsig"""

        if ctx.channel.name == "general":
            await ctx.send(content=f"I'm not allowed to post here.\n Please go to #bot channel.")
            return

        asset_name = get_asset_name_from_idx(number)

        if not unsig_exists(number):
            await ctx.send(content=f"{asset_name} does not exist!\nPlease enter number between 0 and {MAX_AMOUNT}.")
        else:
            try:
                metadata = get_metadata_from_asset_name(asset_name)
                embed = await embed_metadata(metadata)

                embed.set_footer(text=f"\nData comes from {POOL_PM_URL}")
            except:
                await ctx.send(content=f"I can't find the metadata of your unsig!")
                return
            else:
                await ctx.send(embed=embed)
        
    @cog_ext.cog_slash(
        name="cert", 
        description="show certificate of your unsig", 
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
    async def _cert(self, ctx: SlashContext, number: str):
        """show certificate of your unsig"""

        if ctx.channel.name == "general":
            await ctx.send(content=f"I'm not allowed to post here.\n Please go to #bot channel.")
            return

        asset_name = get_asset_name_from_idx(number)

        if not unsig_exists(number):
            await ctx.send(content=f"{asset_name} does not exist!\nPlease enter number between 0 and {MAX_AMOUNT}.")
        else:
            number = str(int(number))

            certificates = load_json(f"{ROOT_DIR}/data/json/certificates.json")
            num_certificates = len(certificates)
            data = get_certificate_data_by_number(number, certificates)

            try:
                embed = embed_certificate(number, data, num_certificates)
                add_last_update(embed, self.bot.certs_updated)
            except:
                await ctx.send(content=f"I can't embed certificate for your unsig.")
                return
            else:
                await ctx.send(embed=embed)


def setup(bot: commands.Bot):
    bot.add_cog(Data(bot))
    print("data cog loaded")