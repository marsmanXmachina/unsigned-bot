"""
Module for help cog
"""

from typing import Optional
import discord
from discord import Embed, Colour
from discord.ext import commands
from discord_slash import cog_ext, SlashContext
from discord_slash.utils.manage_commands import create_choice, create_option

from unsigned_bot.config import GUILD_IDS
from unsigned_bot.cogs import BOT_COMMANDS
from unsigned_bot.log import logger
from unsigned_bot.emojis import *


class HelpCog(commands.Cog, name = "Help"):
    """Get overview of my commands"""

    COG_EMOJI = EMOJI_ROBOT

    def __init__(self, bot: commands.Bot):
        self.bot = bot


    @cog_ext.cog_slash(
        name="help", 
        description="Get overview of my commands", 
        guild_ids=GUILD_IDS,
        options=[
            create_option(
                name="category",
                description="Choose category",
                required=False,
                option_type=3,
                choices=[
                    create_choice(
                        name=f"{command.capitalize()}",
                        value=command
                    ) for command, _ in BOT_COMMANDS.items()
                ]
            )
        ]
    )
    async def _help(self, ctx: SlashContext, category: Optional[str] = None):
        """show available bot commands"""
        
        if not category:
            title = f"{EMOJI_ROBOT} My commands {EMOJI_ROBOT}"
            description="How can I help you?"
        else:
            emoji = COMMAND_CATEGORIES.get(category)
            title = f"{emoji} {category.capitalize()} commands {emoji}"
            description = BOT_COMMANDS.get(category).get("description")

        color = Colour.dark_blue()        
        embed = Embed(title=title, description=description, color=color) 

        for command_group, commands in BOT_COMMANDS.items():
            if not category:
                emoji = COMMAND_CATEGORIES.get(command_group)
                description = commands.get("description")

                embed.add_field(name=f"\n{emoji} {command_group.capitalize()}", value=description, inline=False)
            else:
                if category == command_group:
                    for command, values in commands.items():
                        if command == "description":
                            continue

                        syntax = values.get("syntax")
                        hint = values.get("hint")

                        embed.add_field(name=syntax, value=hint, inline=False)
        
        await ctx.send(embed=embed)    


def setup(bot: commands.Bot):
    bot.add_cog(HelpCog(bot))
    logger.debug(f"{HelpCog.__name__} loaded")