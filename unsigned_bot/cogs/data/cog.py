"""
Module for unsig data cog
"""

import discord
from discord.ext import commands
from discord_slash import cog_ext, SlashContext
from discord_slash.utils.manage_commands import create_choice, create_option

from unsigned_bot import ROOT_DIR, IMAGE_PATH
from unsigned_bot.utility.files_util import load_json
from unsigned_bot.config import GUILD_IDS
from unsigned_bot.constants import MAX_AMOUNT
from unsigned_bot.urls import POOL_PM_URL
from unsigned_bot.emojis import *
from unsigned_bot.log import logger
from unsigned_bot.colors import get_color_frequencies
from unsigned_bot.draw import (
    gen_unsig,
    gen_animation,
    delete_image_files
)
from unsigned_bot.fetch import (
    get_metadata_from_asset_name,
    get_unsig_data,
    get_minting_data,
    get_ipfs_url_from_file
)
from unsigned_bot.parsing import (
    get_idx_from_asset_name,
    get_asset_name_from_idx,
    get_asset_name_from_minting_order,
    get_certificate_data_by_number,
    unsig_exists
)
from unsigned_bot.cogs.checks import valid_channel, valid_unsig
from unsigned_bot.embedding import add_last_update
from .embeds import (
    embed_basic_info,
    embed_metadata,
    embed_certificate,
    add_subpattern,
    add_output_colors
)


class DataCog(commands.Cog, name="Data"):
    """commands to get info about your unsig"""

    COG_EMOJI = EMOJI_FLOPPY

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @cog_ext.cog_slash(
        name="unsig", 
        description="show unsig with given number", 
        guild_ids=GUILD_IDS,
        options=[
            create_option(
                name="number",
                description="Number of your unsig",
                required=True,
                option_type=3,
            ),
            create_option(
                name="animation",
                description="show animated unsig",
                required=False,
                option_type=3,
                choices=[
                    create_choice(
                        name="fading",
                        value="fade"
                    ),
                    create_choice(
                        name="blending",
                        value="blend"
                    )
                ]
            )
        ]
    )
    async def _unsig(self, ctx: SlashContext, number: str, animation: bool = False):
        """show info about your unsig"""   
        
        if not await valid_channel(ctx):
            return

        if not await valid_unsig(ctx, number):
            return

        asset_name = get_asset_name_from_idx(number)

        number = str(int(number))

        unsigs_data = get_unsig_data(number)
        minting_data = get_minting_data(number)

        embed = embed_basic_info(number, asset_name, unsigs_data, minting_data, self.bot.sales)

        color_frequencies = get_color_frequencies(number)
        add_output_colors(embed, color_frequencies, num_colors=6)
        add_subpattern(embed, unsigs_data)

        embed.set_footer(text=f"\nDiscord Bot by Mar5man")

        num_props = unsigs_data.get("num_props")
        if animation and num_props > 1:
            try:
                image_path = await gen_animation(number, mode=animation, backwards=True)
                image_file = discord.File(image_path, filename="image.gif")
                if image_file:
                    embed.set_image(url="attachment://image.gif")

                delete_image_files(IMAGE_PATH, suffix="gif")
            except:
                logger.warning("Animation failed")
            else:
                await ctx.send(file=image_file, embed=embed)
                return 
        
        # load image if animations fails
        try: 
            image_path = await gen_unsig(number, dim=1024)
            image_file = discord.File(image_path, filename="image.png")
            if image_file:
                embed.set_image(url="attachment://image.png")

            delete_image_files(IMAGE_PATH, suffix="png")
        except:
            image_url = await get_ipfs_url_from_file(asset_name)
            try:
                embed.set_image(url=image_url)
            except:
                pass
            finally:
                await ctx.send(embed=embed)
                return
        else:
            await ctx.send(file=image_file, embed=embed)

    @cog_ext.cog_slash(
        name="minted", 
        description="show unsig with given minting order", 
        guild_ids=GUILD_IDS,
        options=[
            create_option(
                name="index",
                description="position of minting order",
                required=True,
                option_type=3,
            )
        ]
    )
    async def _minted(self, ctx: SlashContext, index: str):
        """show unsig with given minting order"""  

        if ctx.channel.name == "general":
            await ctx.send(content=f"I'm not allowed to post here.\n Please go to #bot channel.")
            return
            
        asset_name = get_asset_name_from_minting_order(index)

        if not asset_name:
            await ctx.send(content=f"Unsig with minting order {index} does not exist!\nPlease enter number between 1 and {MAX_AMOUNT}.")
        else:
            number = str(get_idx_from_asset_name(asset_name))

            unsigs_data = get_unsig_data(number)
            minting_data = get_minting_data(number)

            embed = embed_basic_info(number, asset_name, unsigs_data, minting_data, self.bot.sales)

            embed.set_footer(text=f"\nDiscord Bot by Mar5man")

            try:
                image_path = await gen_unsig(number, dim=1024)
                image_file = discord.File(image_path, filename="image.png")
                if image_file:
                    embed.set_image(url="attachment://image.png")

                delete_image_files(IMAGE_PATH, suffix="png")
            except:
                image_url = await get_ipfs_url_from_file(asset_name)
                if image_url:
                    embed.set_image(url=image_url)

                await ctx.send(embed=embed)
            else:
                await ctx.send(file=image_file, embed=embed)

    @cog_ext.cog_slash(
        name="metadata", 
        description="show metadata of your unsig", 
        guild_ids=GUILD_IDS,
        options=[
            create_option(
                name="number",
                description="number of your unsig",
                required=True,
                option_type=3,
            )
        ]
    )
    async def _metadata(self, ctx: SlashContext, number: str):
        """show metadata of your unsig"""

        if ctx.channel.name == "general":
            await ctx.send(content=f"I'm not allowed to post here.\n Please go to #bot channel.")
            return

        asset_name = get_asset_name_from_idx(number)

        if not unsig_exists(number):
            await ctx.send(content=f"{asset_name} does not exist!\nPlease enter number between 0 and {MAX_AMOUNT-1}.")
        else:
            try:
                metadata = get_metadata_from_asset_name(asset_name)
                embed = await embed_metadata(metadata)

                embed.set_footer(text=f"\nData comes from {POOL_PM_URL}")
            except:
                await ctx.send(content=f"I can't find the metadata of your unsig!")
                return
            else:
                await ctx.send(embed=embed)
        
    @cog_ext.cog_slash(
        name="cert", 
        description="show certificate of your unsig", 
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
    async def _cert(self, ctx: SlashContext, number: str):
        """show certificate of your unsig"""

        if ctx.channel.name == "general":
            await ctx.send(content=f"I'm not allowed to post here.\n Please go to #bot channel.")
            return

        asset_name = get_asset_name_from_idx(number)

        if not unsig_exists(number):
            await ctx.send(content=f"{asset_name} does not exist!\nPlease enter number between 0 and {MAX_AMOUNT-1}.")
        else:
            number = str(int(number))

            certificates = load_json(f"{ROOT_DIR}/data/json/certificates.json")
            num_certificates = len(certificates)
            data = get_certificate_data_by_number(number, certificates)

            try:
                embed = embed_certificate(number, data, num_certificates)
                add_last_update(embed, self.bot.certs_updated)
            except:
                await ctx.send(content=f"I can't embed certificate for your unsig.")
                return
            else:
                await ctx.send(embed=embed)


def setup(bot: commands.Bot):
    bot.add_cog(DataCog(bot))
    logger.debug(f"{DataCog.__name__} loaded")