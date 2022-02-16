"""
Main module of the bot.

This bot is designed for the discord of 'unsigned_algorithms'.
Its purpose is to provide users valuable information about their unsig(s)
"""

import os

import discord
from discord.ext import commands
from discord_slash import SlashCommand

from unsigned_bot.utility.files_util import load_json
from unsigned_bot.config import GUILD_NAME
from unsigned_bot.twitter import create_twitter_api
from unsigned_bot.log import logger

from dotenv import load_dotenv
load_dotenv() 

TOKEN = os.getenv('BOT_TOKEN')


# === initialize bot variables ===
bot = commands.Bot(command_prefix='!', help_command=None)
bot.sales = load_json("data/json/sales.json")
bot.sales_updated = None
bot.offers = None
bot.offers_updated = None
bot.certs = load_json("data/json/certificates.json")
bot.certs_updated = None
bot.twitter_api = create_twitter_api()

slash = SlashCommand(bot, sync_commands=True, sync_on_cog_reload=True)

@bot.event
async def on_ready():
    logger.debug(f"bot is present in {[guild.name for guild in bot.guilds]} server")

    bot.guild = discord.utils.find(lambda g: g.name == GUILD_NAME, bot.guilds)
    if bot.guild:
        logger.info(f"{bot.user} is connected to {bot.guild.name}(id: {bot.guild.id})")

    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name='unsigned_algorithms'))

def main():
    "Load cogs and run bot"
    for folder in os.listdir("unsigned_bot/cogs"):
        if os.path.exists(os.path.join("unsigned_bot/cogs", folder, "cog.py")):
            bot.load_extension(f"unsigned_bot.cogs.{folder}.cog")

    bot.run(TOKEN)


if __name__ == "__main__":
    main()