"""
Module for geometry cog specific discord embeds
"""

from collections import Counter
import inflect
from discord import Embed, Colour

from unsigned_bot import ROOT_DIR
from unsigned_bot.utility.files_util import load_json
from unsigned_bot.parsing import link_assets_to_grid
from unsigned_bot.emojis import *


def embed_pattern_combo(pattern_found: list, search_input: list, to_display: list, cols=3) -> Embed:
    """Return discord embed for pattern combo"""

    num_found = len(pattern_found)

    subs_frequencies = load_json(f"{ROOT_DIR}/data/json/subs_frequencies.json")
    search_formatted = dict(Counter(search_input))
   
    pattern_str = " + \n".join([f"{amount} x {pattern}" for pattern, amount in search_formatted.items()])
  
    title = f"{EMOJI_LINK} Pattern combo {EMOJI_LINK}"
    description=f"**{num_found}** unsigs with this pattern combo:\n`{pattern_str}`"
    color = Colour.dark_blue()

    embed = Embed(title=title, description=description, color=color)

    for sub, amount in search_formatted.items():
        frequency = subs_frequencies.get(sub).get(str(amount), 0)
        embed.add_field(name=f"{amount} x {sub}", value=f"**{frequency} / 31119** unsigs contain this subpattern", inline=False)

    if to_display:
        unsigs_str = link_assets_to_grid(to_display, cols)
        embed.add_field(name=f"{EMOJI_ARROW_DOWN} Random selection {EMOJI_ARROW_DOWN}", value=unsigs_str, inline=False)

    return embed

def embed_forms(form: str, num_found: int) -> Embed:
    """Return discord embed for forms"""

    p = inflect.engine()
    form_name = p.plural(form)
    if form == "rivers" or form == "veins":
        form_name = form

    emoji = FORMS_EMOJIS.get(form)
    title = f"{emoji} {form_name} {emoji}"
    description=f"**{num_found}** clean {form_name} in whole collection"
    color = Colour.dark_blue()

    embed = Embed(title=title, description=description, color=color)

    return embed