"""
Module for color cog specific discord embeds
"""

import numpy as np
from discord import Embed, Colour

from unsigned_bot.colors import (
    PIXELS_COLORS, COLOR_RANKING, 
    rgb_2_hex,
    link_hex_color, 
    get_total_colors,
    get_top_colors,
    calc_color_rarity
)
from unsigned_bot.parsing import get_asset_name_from_idx, get_unsig_url
from unsigned_bot.emojis import *
from unsigned_bot.urls import *


def embed_color_ranking() -> Embed:
    """Return discord embed for color ranking"""

    title = f"{EMOJI_PALETTE} Color Rarities {EMOJI_PALETTE} "
    description=f"based on cumulative pixel amount in whole collection"
    color = Colour.dark_blue()
    embed = Embed(title=title, description=description, color=color)

    total_pixels = sum(PIXELS_COLORS.values())
    ordered_ranking = sorted(COLOR_RANKING.items(), key=lambda x:x[1], reverse=False)

    color_ranking_list = list()
    for i, (color, rank) in enumerate(ordered_ranking):
        color_hex = rgb_2_hex(color)
        color_link = link_hex_color(color_hex)
        pixels = PIXELS_COLORS.get(color)
        percentage = pixels / total_pixels

        color_ranking_list.append(f" `{rank}.`[{color_hex}]({color_link}), **{percentage:.2%}**\n")

    PARTS = 8
    splitted = np.array_split(color_ranking_list, PARTS)
    for i, part in enumerate(splitted):
        if i == 0:
            title = f"{EMOJI_ARROW_DOWN} Rarity Ranking {EMOJI_ARROW_DOWN}"
        else: 
            title = "..."
        
        part_str = "".join(part)

        embed.add_field(name=title, value=part_str, inline=False)

    return embed


def embed_output_colors(number: str, color_frequencies: dict) -> Embed:
    """Return discord embed for output colors"""

    asset_name = get_asset_name_from_idx(number)
    num_colors = get_total_colors(color_frequencies)
    unsig_url = get_unsig_url(number)

    title = f"{EMOJI_PALETTE} colors {asset_name} {EMOJI_PALETTE} "
    description=f"Your unsig has **{num_colors} / 64** output colors"
    color = Colour.dark_blue()
    embed = Embed(title=title, description=description, color=color, url=unsig_url)

    add_output_colors(embed, color_frequencies)

    return embed

def add_output_colors(embed: Embed, color_frequencies: dict, num_colors: int =10):
    """Add output colors to discord embed"""

    top_colors = get_top_colors(color_frequencies, num_ranks=num_colors)

    top_colors_str = ""
    for i, (color, percentage) in enumerate(top_colors.items()):
        color_rank = COLOR_RANKING.get(color)
        color_hex = rgb_2_hex(color)
        color_link = link_hex_color(color_hex)

        top_colors_str += f" {i+1}. [{color_hex}]({color_link}) to **{percentage:.2%}** `[{color_rank}]`\n"
    
    color_rarity = calc_color_rarity(color_frequencies)

    top_colors_str += f" => weighted color rank: **{color_rarity:.2f}**\n"

    embed.add_field(name=f"{EMOJI_ARROW_DOWN} Top Colors [rarity rank] {EMOJI_ARROW_DOWN}", value=top_colors_str, inline=False)