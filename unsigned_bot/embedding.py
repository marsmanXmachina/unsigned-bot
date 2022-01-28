"""
Module for customized discord embeds
"""

from datetime import datetime
from discord import Embed

from unsigned_bot.utility.time_util import timestamp_to_datetime
from unsigned_bot.constants import POLICY_ID, MAX_AMOUNT
from unsigned_bot.emojis import *
from unsigned_bot.urls import *


def add_policy(embed: Embed):
    """Add policy section to discord embed"""
    embed.add_field(name = f"{EMOJI_WARNING} Watch out for fake items and always check the policy id {EMOJI_WARNING}", value=f"`{POLICY_ID}`", inline=False)

def add_disclaimer(embed: Embed, last_update: datetime):
    """Add disclaimer to discord embed"""
    last_update = last_update.strftime("%Y-%m-%d %H:%M:%S UTC")
    embed.set_footer(text=f"The server has no affiliation with the marketplace nor listed prices.\n\nData comes from \n - {CNFT_URL}\n - {TOKHUN_URL}\n - {JPGSTORE_URL}\nLast update: {last_update}")

def add_data_source(embed: Embed, last_update: datetime):
    """Add source and date from last update to discord embed"""
    last_update = last_update.strftime("%Y-%m-%d %H:%M:%S UTC")
    embed.set_footer(text=f"Data comes from\n - {CNFT_URL}\n - {TOKHUN_URL}\nLast update: {last_update}")

def add_last_update(embed: Embed, last_update: datetime):
    """Add date from last update to discord embed"""
    last_update = last_update.strftime("%Y-%m-%d %H:%M:%S UTC")
    embed.set_footer(text=f"\nLast update: {last_update}")

def add_minting_order(embed, minting_data):
    """Add minting order to discord embed"""
    minting_order, minting_time = minting_data
    dt = timestamp_to_datetime(minting_time)
    embed.add_field(name=f"{EMOJI_NUMBERS} Minting order", value=f"`{minting_order}/{MAX_AMOUNT+1}` ({dt.date()})", inline=False)

def add_num_props(embed, unsig_data):
    """Add number of properties to discord embed"""
    total_props = unsig_data.get("num_props")
    embed.add_field(name="Total properties", value=f"This unsig has **{total_props}** properties", inline=False)





