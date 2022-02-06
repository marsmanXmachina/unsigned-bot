"""
Module for structure cog specific discord embeds
"""

from discord import Embed, Colour

from unsigned_bot import ROOT_DIR
from unsigned_bot.utility.files_util import load_json
from unsigned_bot.log import logger
from unsigned_bot.emojis import *
from unsigned_bot.parsing import get_unsig_url


def embed_composition(number:str, asset_name: str) -> Embed:
    """Return discord embed for unsig composition"""

    title = f"{EMOJI_PALETTE} {asset_name} {EMOJI_PALETTE}"
    description="Explore the composition of your unsig..."
    color = Colour.dark_blue()

    embed = Embed(title=title, description=description, color=color)

    try:
        unsigs_subpattern = load_json(f"{ROOT_DIR}/data/json/subpattern.json")
    except:
        logger.warning("Can not open subpatterns")
    else:
        subpattern = unsigs_subpattern.get(number, None)
        if subpattern:
            subpattern_str = ""
            for i, pattern in enumerate(reversed(subpattern)):
                if not pattern:
                    row = f"{i+1}. ` - `\n"
                else:
                    unsig_url = get_unsig_url(str(pattern))
                    pattern = str(pattern).zfill(5)
                    row = f"{i+1}. [#{pattern}]({unsig_url})\n"

                subpattern_str += row
            
            embed.add_field(name=f"{EMOJI_ARROW_DOWN} Top to Bottom {EMOJI_ARROW_DOWN}", value=subpattern_str, inline=False)
    
    return embed

def embed_subs(number: str, asset_name: str, layers: list, subpattern_names: dict) -> Embed:
    """Return discord embed for subpattern"""

    title = f"{EMOJI_PALETTE} {asset_name} {EMOJI_PALETTE}"
    description="Explore the subpattern of your unsig..."
    color = Colour.dark_blue()

    embed = Embed(title=title, description=description, color=color)

    if len(layers) > 1:
        name_idx = 1
        names_str = f"{name_idx}. #{number.zfill(5)}\n"
    else:
        names_str = ""
        name_idx = 0

    COLORS = ["Red", "Green", "Blue"]
    for color in reversed(COLORS):
        name = subpattern_names.get(color, None)
        if not name:
            continue

        name_idx += 1
        names_str += f"{name_idx}. `{color.lower()} {name}`\n"

    embed.add_field(name=f"{EMOJI_ARROW_DOWN} Top to Bottom {EMOJI_ARROW_DOWN}", value=names_str, inline=False)

    return embed