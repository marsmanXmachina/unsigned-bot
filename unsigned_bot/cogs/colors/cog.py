"""
Module for color cog
"""

import discord
from discord.ext import commands
from discord_slash import cog_ext, SlashContext
from discord_slash.utils.manage_commands import create_choice, create_option

from unsigned_bot import IMAGE_PATH
from unsigned_bot.config import GUILD_IDS
from unsigned_bot.constants import MAX_AMOUNT
from unsigned_bot.colors import get_color_frequencies
from unsigned_bot.draw import gen_color_histogram, delete_image_files
from unsigned_bot.parsing import (
    get_asset_name_from_idx,
    unsig_exists
)

from .embeds import embed_color_ranking, embed_output_colors


class Color(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @cog_ext.cog_slash(
        name="color-ranking", 
        description="show color ranking", 
        guild_ids=GUILD_IDS
    )
    async def _color_ranking(self, ctx: SlashContext):
        """show color ranking"""
            
        if ctx.channel.name == "general":
            await ctx.send(content=f"I'm not allowed to post here.\n Please go to #bot channel.")
            return

        embed = embed_color_ranking()

        try:
            image_path = "img/color_freqs.jpg" 
            image_file = discord.File(image_path, filename="image.jpg")
            if image_file:
                embed.set_image(url="attachment://image.jpg")
        except:
            await ctx.send(content=f"I can't generate color ranking.")
            return
        else:
            await ctx.send(file=image_file, embed=embed)    

    @cog_ext.cog_slash(
        name="colors", 
        description="show output colors of given unsig", 
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
    async def _colors(self, ctx: SlashContext, number: str):
        """show output colors of your unsig"""    

        if ctx.channel.name == "general":
            await ctx.send(content=f"I'm not allowed to post here.\n Please go to #bot channel.")
            return

        asset_name = get_asset_name_from_idx(number)

        if not unsig_exists(number):
            await ctx.send(content=f"{asset_name} does not exist!\nPlease enter number between 0 and {MAX_AMOUNT}.")
        else:
            number = str(int(number))
            color_frequencies = get_color_frequencies(number)

            embed = embed_output_colors(number, color_frequencies)

            embed.set_footer(text=f"\nDiscord Bot by Mar5man")

            try:
                image_path = await gen_color_histogram(number, color_frequencies)
                image_file = discord.File(image_path, filename="image.png")
                if image_file:
                    embed.set_image(url="attachment://image.png")
                    
                delete_image_files(IMAGE_PATH)
            except:
                await ctx.send(content=f"I can't generate color histogram of your unsig.")
                return
            else:
                await ctx.send(file=image_file, embed=embed)    


def setup(bot: commands.Bot):
    bot.add_cog(Color(bot))
    print("color cog loaded")