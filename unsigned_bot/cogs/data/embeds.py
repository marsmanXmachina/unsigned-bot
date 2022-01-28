"""
Module for data cog specific discord embeds
"""
import pprint
import discord
from discord import Embed, Colour

from unsigned_bot.emojis import *
from unsigned_bot.urls import *
from unsigned_bot.fetch import get_minting_tx_id
from unsigned_bot.parsing import (
    get_asset_id,
    get_idx_from_asset_name
)


def embed_basic_info(number: str) -> Embed:
    """Return discord embed for unsig info"""

    


async def embed_metadata(metadata: dict) -> Embed:
    """Return discord embed with metadata of unsig"""
    asset_name = metadata.get("title").replace("_", "")

    try:
        asset_id = get_asset_id(asset_name)
        tx_id = await get_minting_tx_id(asset_id)
    except:
        metadata_url = None
    else:
        metadata_url = f"{CARDANOSCAN_URL}/transaction/{tx_id}/?tab=metadata"

    title = f"{EMOJI_FILE}  metadata {asset_name}  {EMOJI_FILE}"
    description="Show metadata of your unsig"
    color=discord.Colour.dark_blue()

    embed = discord.Embed(title=title, description=description, color=color, url=metadata_url)

    for k, v in metadata.items():
        if isinstance(v, dict):
            value_str = pprint.pformat(v)
        else:   
            value_str = v
        
        if len(str(value_str)) >= 1024:
            value_str = f"Data too long to display!"
            if metadata_url:
                value_str += f"\nClick **[here]({metadata_url})** to see complete metadata."
        else:
            value_str = f"`{value_str}`"

        embed.add_field(name=f"**'{k}'**", value=f"{value_str}", inline=False)

    return embed

def embed_certificate(number: str, data: dict, num_certificates: int, feed=False) -> Embed:
    """Return discord embed for certificates"""

    if data:
        metadata = data.get("onchain_metadata")
        policy_id = data.get("policy_id")
        certificate_name = metadata.get("name")
        certificate_number = get_idx_from_asset_name(certificate_name)
        
        certificate_link = f"{POOL_PM_URL}/{policy_id}.UNS{str(certificate_number).zfill(5)}x{number.zfill(5)}"

        ipfs_hash = metadata.get("image").rsplit("/",1)[-1]
        image_link = f"{BLOCKFROST_IPFS_URL}/{ipfs_hash}"

        title = f"{EMOJI_CERT} Cert for unsig{number.zfill(5)} {EMOJI_CERT}"
        if feed:
            description=f"minted by CNFT_ART\n"
        else:
            description=f"**{num_certificates}** certificates already minted\n"
        color = Colour.dark_blue()
    
        embed = Embed(title=title, description=description, color=color, url=certificate_link)
    else:
        title = f"{EMOJI_CROSS} No cert found for unsig{number.zfill(5)} {EMOJI_CROSS}"
        description=f"**{num_certificates}** certificates already minted\n"
        color = Colour.dark_blue()
        embed = Embed(title=title, description=description, color=color)
    
    if data:
        mint_date = metadata.get("Unsig mint date")
        embed.add_field(name=f"{EMOJI_PICK} Minted on", value=f"`{mint_date}`", inline=True)

        assessment_date = metadata.get("Assessment date")
        embed.add_field(name=f"{EMOJI_CHECK} Certified on", value=f"`{assessment_date}`", inline=True)

        embed.set_image(url=image_link)

    embed.add_field(name=f"{EMOJI_CART} Order your unsig certificate {EMOJI_CART}", value=f"{EMOJI_ARROW_RIGHT} visit [CNFT_ART's discord]({DISCORD_CNFT_ART})", inline=False)

    return embed