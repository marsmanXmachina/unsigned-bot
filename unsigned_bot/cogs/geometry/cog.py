"""
Module for geometry cog
"""

import random
import math
from typing import Optional

import discord
from discord.ext import commands
from discord_slash import cog_ext, SlashContext
from discord_slash.utils.manage_commands import create_choice, create_option

from unsigned_bot import ROOT_DIR, IMAGE_PATH
from unsigned_bot.utility.files_util import load_json
from unsigned_bot.config import GUILD_IDS
from unsigned_bot.log import logger
from unsigned_bot.draw import gen_grid, delete_image_files
from unsigned_bot.deconstruct import SUBPATTERN_NAMES, filter_subs_by_names
from unsigned_bot.emojis import *
from .embeds import embed_pattern_combo, embed_forms


class GeometryCog(commands.Cog, name = "Geometry"):
    """commands for geometry analysis"""

    COG_EMOJI = EMOJI_ORANGE_DIAMOND

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @cog_ext.cog_slash(
        name="forms", 
        description="show unsigs with given form", 
        guild_ids=GUILD_IDS,
        options=[
            create_option(
                name="form",
                description="visible pattern of unsig",
                required=True,
                option_type=3,
                choices=[create_choice(name=name, value=name) for name in SUBPATTERN_NAMES]
            )
        ]
    )
    async def forms(self, ctx: SlashContext, form: str):
        """show unsigs with given form"""
        
        if ctx.channel.name == "general":
            await ctx.send(content=f"I'm not allowed to post here.\n Please go to #bot channel.")
            return
        
        subs_advanced = load_json(f"{ROOT_DIR}/data/json/subs_advanced.json")
        form_selected = subs_advanced.get(form)

        if not form_selected:
            if form == "basketball":
                clean_form = subs_advanced.get("bulb").get("diagonal")
            if form == "butterfly":
                clean_form = subs_advanced.get("window").get("bulb")
        else:
            clean_form = form_selected.get("clean")

        num_found = len(clean_form)

        embed = embed_forms(form, num_found)

        embed.set_footer(text=f"\nDiscord Bot by Mar5man")

        try:
            image_path = f"img/{form}.jpg" 
            image_file = discord.File(image_path, filename="image.jpg")
            if image_file:
                embed.set_image(url="attachment://image.jpg")
        except:
            await ctx.send(content=f"I can't display selected forms.")
            return
        else:
            await ctx.send(file=image_file, embed=embed)
    
    @cog_ext.cog_slash(
        name="pattern-combo", 
        description="count unsigs with given pattern combo", 
        guild_ids=GUILD_IDS,
            options=[
                create_option(
                    name="first_pattern",
                    description=f"1st subpattern",
                    required=True,
                    option_type=3,
                    choices=[create_choice(name=name, value=name) for name in SUBPATTERN_NAMES]
                ),
                create_option(
                    name="second_pattern",
                    description="2nd subpattern",
                    required=False,
                    option_type=3,
                    choices=[create_choice(name=name, value=name) for name in SUBPATTERN_NAMES]
                ),
                create_option(
                    name="third_pattern",
                    description="3rd subpattern",
                    required=False,
                    option_type=3,
                    choices=[create_choice(name=name, value=name) for name in SUBPATTERN_NAMES]
                )
            ]        
    )
    async def _pattern_combo(self, ctx: SlashContext, first_pattern: str, second_pattern: Optional[str] = None, third_pattern: Optional[str] = None):
        """count unsigs with given pattern combo"""    

        if ctx.channel.name == "general":
            await ctx.send(content=f"I'm not allowed to post here.\n Please go to #bot channel.")
            return

        pattern = [first_pattern, second_pattern, third_pattern]
        pattern_for_search = [p for p in pattern if p in SUBPATTERN_NAMES]

        subs_counted = load_json(f"{ROOT_DIR}/data/json/subs_counted.json")
        pattern_found = filter_subs_by_names(subs_counted, pattern_for_search)

        LIMIT_DISPLAY = 9

        if len(pattern_found) <= LIMIT_DISPLAY:
            to_display = pattern_found
            cols = math.ceil(math.sqrt(len(to_display)))
        else:
            to_display = random.sample(pattern_found, LIMIT_DISPLAY)
            cols = math.ceil(math.sqrt(LIMIT_DISPLAY))

        embed = embed_pattern_combo(pattern_found, pattern_for_search, to_display, cols)

        embed.set_footer(text=f"\nDiscord Bot by Mar5man")

        if to_display:
            try:
                image_path = await gen_grid(to_display, cols)

                image_file = discord.File(image_path, filename="grid.png")
                if image_file:
                    embed.set_image(url="attachment://grid.png")

                delete_image_files(IMAGE_PATH)
            except:
                await ctx.send(content=f"I can't display the selection of unsigs.")
                return
            else:
                await ctx.send(file=image_file, embed=embed)
        else:
            await ctx.send(embed=embed)



def setup(bot: commands.Bot):
    bot.add_cog(GeometryCog(bot))
    logger.debug(f"{GeometryCog.__name__} loaded")