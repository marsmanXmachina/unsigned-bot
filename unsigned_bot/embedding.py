"""
Module for customized discord embeds
"""

from datetime import datetime
from discord import Embed

from unsigned_bot import IMAGE_PATH
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
    urls_str = list_marketplace_base_urls()
    embed.set_footer(text=f"The server has no affiliation with the marketplace nor listed prices.\n\nData comes from \n{urls_str}\nLast update: {last_update}")

def add_data_source(embed: Embed, last_update: datetime):
    """Add source and date from last update to discord embed"""
    last_update = last_update.strftime("%Y-%m-%d %H:%M:%S UTC")
    urls_str = list_marketplace_base_urls()
    embed.set_footer(text=f"Data comes from\n{urls_str}\nLast update: {last_update}")

def add_last_update(embed: Embed, last_update: datetime):
    """Add date from last update to discord embed"""
    last_update = last_update.strftime("%Y-%m-%d %H:%M:%S UTC")
    embed.set_footer(text=f"\nLast update: {last_update}")

def add_minting_order(embed: Embed, minting_data: tuple):
    """Add minting order to discord embed"""
    minting_order, minting_time = minting_data
    dt = timestamp_to_datetime(minting_time)
    embed.add_field(name=f"{EMOJI_NUMBERS} Minting order", value=f"`{minting_order}/{MAX_AMOUNT}` ({dt.date()})", inline=False)

def add_num_props(embed: Embed, unsig_data: dict):
    """Add number of properties to discord embed"""
    total_props = unsig_data.get("num_props")
    embed.add_field(name="Total properties", value=f"This unsig has **{total_props}** properties", inline=False)

def add_props(embed: Embed, unsig_data: dict):
    """Add properties to discord embed"""
    properties = unsig_data.get("properties")
    colors = properties.get("colors")
    multipliers = properties.get("multipliers")
    distributions = properties.get("distributions")
    rotations = properties.get("rotations")
    
    colors_str = ", ".join([c for c in colors])
    embed.add_field(name=f"{EMOJI_RAINBOW} Colors {EMOJI_RAINBOW}", value=f"`{colors_str}`", inline=False)

    multipliers_str = ", ".join([str(m) for m in multipliers])
    embed.add_field(name=f"{EMOJI_GEAR} Multipliers {EMOJI_GEAR}", value=f"`{multipliers_str}`", inline=False)

    distributions_str = ", ".join([d for d in distributions])
    embed.add_field(name=f"{EMOJI_BARCHART} Distributions {EMOJI_BARCHART}", value=f"`{distributions_str}`", inline=False)

    rotations_str = ", ".join([str(r) for r in rotations])
    embed.add_field(name=f"{EMOJI_CIRCLE_ARROWS} Rotations {EMOJI_CIRCLE_ARROWS}", value=f"`{rotations_str}`", inline=False)

def list_marketplace_base_urls() -> str:
    return "".join(f"- {url}\n" for url in MARKETPLACES_BASE_URLS.values())