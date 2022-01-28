"""
Module for collection cog
"""

import discord
from discord.ext import commands
from discord_slash import cog_ext, SlashContext
from discord_slash.utils.manage_commands import create_choice, create_option

from unsigned_bot import IMAGE_PATH
from unsigned_bot.constants import MAX_AMOUNT
from unsigned_bot.config import GUILD_IDS
from unsigned_bot.draw import (
    gen_grid,
    delete_image_files
)
from unsigned_bot.matching import get_similar_unsigs
from unsigned_bot.parsing import (
    get_asset_name_from_idx,
    unsig_exists
)
from unsigned_bot.embedding import add_disclaimer
from .embeds import embed_siblings


class Collection(commands.Cog):
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
    async def siblings(self, ctx: SlashContext, number: str):
        "show siblings of your unsig"  
        
        if ctx.channel.name == "general":
            await ctx.send(content=f"I'm not allowed to post here.\n Please go to #bot channel.")
            return

        asset_name = get_asset_name_from_idx(number)

        if not unsig_exists(number):
            await ctx.send(content=f"{asset_name} does not exist!\nPlease enter number between 0 and {MAX_AMOUNT}.")
            return
        else:
            collection_numbers = range(0,31119)

            similar_unsigs = get_similar_unsigs(number, collection_numbers, structural=False)

            siblings_numbers = list(set().union(*similar_unsigs.values()))
            selected_numbers = siblings_numbers[:]
            selected_numbers.insert(0, int(number))

            embed = embed_siblings(number, siblings_numbers, selected_numbers, self.bot.offers, cols=2)

            if self.bot.offers and siblings_numbers:
                add_disclaimer(embed, self.bot.offers_updated)

            if not siblings_numbers:
                await ctx.send(embed=embed)
                return

            try:
                image_path = await gen_grid(selected_numbers, cols=2)

                image_file = discord.File(image_path, filename="siblings.png")
                if image_file:
                    embed.set_image(url="attachment://siblings.png")

                delete_image_files(IMAGE_PATH)
            except:
                await ctx.send(content=f"I can't generate the siblings of your unsig.")
                return
            else:
                await ctx.send(file=image_file, embed=embed)    
    


def setup(bot: commands.Bot):
    bot.add_cog(Collection(bot))
    print("collection cog loaded")