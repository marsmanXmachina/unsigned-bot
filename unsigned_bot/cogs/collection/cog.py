"""
Module for collection cog
"""

import math
import discord
from discord.ext import commands
from discord_slash import cog_ext, SlashContext
from discord_slash.utils.manage_commands import create_choice, create_option

from unsigned_bot import IMAGE_PATH
from unsigned_bot.constants import MAX_AMOUNT
from unsigned_bot.config import GUILD_IDS
from unsigned_bot.log import logger
from unsigned_bot.emojis import *
from unsigned_bot.draw import (
    gen_grid,
    delete_image_files
)
from unsigned_bot.matching import get_similar_unsigs
from unsigned_bot.parsing import get_numbers_from_string
from unsigned_bot.embedding import add_disclaimer
from unsigned_bot.cogs.checks import valid_channel, valid_unsig
from .embeds import embed_siblings, embed_collection_grid


class CollectionCog(commands.Cog, name="Collection"):
    """commands for your unsig collection"""

    COG_EMOJI = EMOJI_FRAME

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @cog_ext.cog_slash(
        name="siblings", 
        description="show siblings of your unsig", 
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
    async def _siblings(self, ctx: SlashContext, number: str):
        "show siblings of your unsig"  

        if not await valid_channel(ctx):
            return
        
        if not await valid_unsig(ctx, number):
            return

        collection_numbers = range(0,MAX_AMOUNT)
        similar_unsigs = get_similar_unsigs(number, collection_numbers, structural=False)

        siblings_numbers = list(set().union(*similar_unsigs.values()))
        selected_numbers = [int(number), *siblings_numbers]
        
        embed = embed_siblings(number, siblings_numbers, selected_numbers, self.bot.offers, cols=2)

        if self.bot.offers and siblings_numbers:
            add_disclaimer(embed, self.bot.offers_updated)

        if not siblings_numbers:
            await ctx.send(embed=embed)
            return

        try:
            image_path = await gen_grid(selected_numbers, cols=2)
            image_file = discord.File(image_path, filename="siblings.png")
            embed.set_image(url="attachment://siblings.png")

            delete_image_files(IMAGE_PATH)
        except:
            await ctx.send(content=f"I can't generate the siblings of your unsig.")
            return
        else:
            await ctx.send(file=image_file, embed=embed)    
    
    @cog_ext.cog_slash(
        name="show", 
        description="show collection of your unsigs", 
        guild_ids=GUILD_IDS,
        options=[
            create_option(
                name="numbers",
                description="Numbers of your unsigs",
                required=True,
                option_type=3,
            ),
            create_option(
                name="columns",
                description="no. of unsigs side by side",
                required=False,
                option_type=3,
            ),
        ]
    )
    async def _show(self, ctx: SlashContext, numbers: str, columns: str = None):
        """show collection of your unsigs"""

        if not await valid_channel(ctx):
            return

        unsig_numbers = get_numbers_from_string(numbers)
        if not unsig_numbers:
            await ctx.send(content=f"Please enter numbers of your unsigs")
            return

        numbers_cleaned = list()
        for number in unsig_numbers:
            try:
                number = str(int(number))
            except:
                await ctx.send(content=f"unsig{number} does not exist!\nPlease enter number between 0 and {MAX_AMOUNT-1}.")
                return
            else:
                numbers_cleaned.append(number)

        LIMIT_DISPLAY = 20
        if len(numbers_cleaned) > LIMIT_DISPLAY:
            numbers_cleaned = numbers_cleaned[:LIMIT_DISPLAY]
        
        if not columns:
            columns = math.ceil(math.sqrt(len(numbers_cleaned)))
        else:
            try:
                columns = int(columns)
            except:
                await ctx.send(content=f"Please enter the number of unsigs you want to show")
                return

        embed = embed_collection_grid(numbers_cleaned)

        try:
            image_path = await gen_grid(numbers_cleaned, columns)
            image_file = discord.File(image_path, filename="collection.png")
            embed.set_image(url="attachment://collection.png")

            delete_image_files(IMAGE_PATH)
        except:
            await ctx.send(content=f"I can't generate the collection of your unsigs.")
            return
        else:
            await ctx.send(file=image_file, embed=embed)


def setup(bot: commands.Bot):
    bot.add_cog(CollectionCog(bot))
    logger.debug(f"{CollectionCog.__name__} loaded")

