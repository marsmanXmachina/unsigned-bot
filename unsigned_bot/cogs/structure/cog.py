"""
Module for structure cog
"""

import discord
from discord import Embed, Colour
from discord.ext import commands
from discord_slash import cog_ext, SlashContext
from discord_slash.utils.manage_commands import create_choice, create_option

from unsigned_bot import IMAGE_PATH
from unsigned_bot.config import GUILD_IDS
from unsigned_bot.constants import MAX_AMOUNT
from unsigned_bot.log import logger
from unsigned_bot.emojis import *
from unsigned_bot.deconstruct import (
    get_prop_layers,
    get_subpattern,
    get_subpattern_names
)
from unsigned_bot.draw import (
    gen_evolution,
    gen_subpattern,
    delete_image_files
)
from unsigned_bot.fetch import get_unsig_data
from unsigned_bot.parsing import (
    get_asset_name_from_idx,
    unsig_exists
)
from .embeds import embed_composition, embed_subs

class StructureCog(commands.Cog, name = "Structure"):
    """commands to deconstruct your unsig"""

    COG_EMOJI = EMOJI_CONSTRUCTION

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @cog_ext.cog_slash(
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
    async def _evo(self, ctx: SlashContext, number: str, extended=False):
        """show composition of your unsig"""  

        if ctx.channel.name == "general":
            await ctx.send(content=f"I'm not allowed to post here.\n Please go to #bot channel.")
            return

        asset_name = get_asset_name_from_idx(number)

        if not unsig_exists(number):
            await ctx.send(content=f"{asset_name} does not exist!\nPlease enter number between 0 and {MAX_AMOUNT-1}.")
        else:
            number = str(int(number))

            embed = embed_composition(number, asset_name)

            try:
                extended = True if extended == "extended" else False

                image_path = await gen_evolution(number, show_single_layers=False, extended=extended)

                image_file = discord.File(image_path, filename="image.png")
                if image_file:
                    embed.set_image(url="attachment://image.png")

                delete_image_files(IMAGE_PATH)
            except:
                await ctx.send(content=f"I can't generate the composition of your unsig.")
                return
            else:
                await ctx.send(file=image_file, embed=embed)

    @cog_ext.cog_slash(
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
    async def _invo(self, ctx: SlashContext, number: str):
        """show ingredients of your unsig"""  

        if ctx.channel.name == "general":
            await ctx.send(content=f"I'm not allowed to post here.\n Please go to #bot channel.")
            return

        asset_name = get_asset_name_from_idx(number)

        if not unsig_exists(number):
            await ctx.send(content=f"{asset_name} does not exist!\nPlease enter number between 0 and {MAX_AMOUNT-1}.")
        else:
            number = str(int(number))

            title = f"{EMOJI_PALETTE} {asset_name} {EMOJI_PALETTE}"
            description="Explore the ingredients of your unsig..."
            color = discord.Colour.dark_blue()

            embed = discord.Embed(title=title, description=description, color=color)

            try:
                image_path = await gen_evolution(number, show_single_layers=True)

                image_file = discord.File(image_path, filename="image.png")
                if image_file:
                    embed.set_image(url="attachment://image.png")

                delete_image_files(IMAGE_PATH)
            except:
                await ctx.send(content=f"I can't generate the ingredients of your unsig.")
                return
            else:
                await ctx.send(file=image_file, embed=embed)
    
    @cog_ext.cog_slash(
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
    async def _subs(self, ctx: SlashContext, number: str):
        """show subpattern of your unsig"""

        if ctx.channel.name == "general":
            await ctx.send(content=f"I'm not allowed to post here.\n Please go to #bot channel.")
            return

        asset_name = get_asset_name_from_idx(number)

        if not unsig_exists(number):
            await ctx.send(content=f"{asset_name} does not exist!\nPlease enter number between 0 and {MAX_AMOUNT-1}.")
        else:
            number = str(int(number))

            unsig_data = get_unsig_data(number)

            layers = get_prop_layers(unsig_data)
            subpattern = get_subpattern(layers)
            subpattern_names = get_subpattern_names(subpattern)

            embed = embed_subs(number, asset_name, layers, subpattern_names)

            try:
                image_path = await gen_subpattern(number)

                image_file = discord.File(image_path, filename="image.png")
                if image_file:
                    embed.set_image(url="attachment://image.png")

                delete_image_files(IMAGE_PATH)
            except:
                await ctx.send(content=f"I can't generate the subpattern of your unsig.")
                return
            else:
                await ctx.send(file=image_file, embed=embed)    


def setup(bot: commands.Bot):
    bot.add_cog(StructureCog(bot))
    logger.debug(f"{StructureCog.__name__} loaded")