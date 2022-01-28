"""
Module for market cog
"""

from typing import Optional
import discord
from discord.ext import commands
from discord_slash import cog_ext, SlashContext
from discord_slash.utils.manage_commands import create_choice, create_option

from unsigned_bot import IMAGE_PATH
from unsigned_bot.config import GUILD_IDS
from unsigned_bot.constants import MAX_AMOUNT
from unsigned_bot.utility.time_util import get_interval_from_period
from unsigned_bot.draw import (
    gen_grid,
    gen_grid_with_matches,
    delete_image_files
)
from unsigned_bot.matching import (
    match_unsig,
    choose_best_matches,
    get_similar_unsigs
)
from unsigned_bot.fetch import get_unsig_data, get_minting_data
from unsigned_bot.parsing import (
    get_asset_name_from_idx,
    get_numbers_from_assets,
    unsig_exists,
    order_by_num_props,
    filter_by_time_interval,
    filter_assets_by_type,
    sort_sales_by_date
)
from unsigned_bot.embedding import add_data_source, add_disclaimer, add_policy
from .embeds import embed_sales, embed_related, embed_matches, embed_offers, embed_offer


class Market(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @cog_ext.cog_slash(
        name="sales", 
        description="show data of sold unsigs on marketplace", 
        guild_ids=GUILD_IDS,
        options=[
            create_option(
                name="prices",
                description="type of price data",
                required=False,
                option_type=3,
                choices=[
                    create_choice(
                        name="average prices",
                        value="average"
                    ),
                    create_choice(
                        name="top sales",
                        value="highest"
                    )
                ]
            ),
            create_option(
                name="period",
                description="period of sales",
                required=False,
                option_type=3,
                choices=[
                    create_choice(
                        name="last day",
                        value="day"
                    ),
                    create_choice(
                        name="last week",
                        value="week"
                    ),
                    create_choice(
                        name="last month",
                        value="month"
                    )
                ]
            )
        ]        
    )
    async def _sales(self, ctx: SlashContext, prices: Optional[str] = None, period: Optional[str] = None):
        """show sold unsigs on marketplace""" 
    
        if ctx.channel.name == "general":
            await ctx.send(content=f"I'm not allowed to post here.\n Please go to #bot channel.")
            return

        if self.bot.sales:
            if period:
                interval_ms = get_interval_from_period(period)
                if not interval_ms:
                    await ctx.send(content=f"Please enter a valid time period!")
                    return
                else:
                    filtered= filter_by_time_interval(self.bot.sales, interval_ms)
            else: 
                filtered = self.bot.sales

            embed = embed_sales(filtered, prices, period)
            add_data_source(embed, self.bot.sales_updated)

            await ctx.send(embed=embed)
            return
        else:
            await ctx.send(content=f"Currently no sales data available...")
            return

    @cog_ext.cog_slash(
        name="like", 
        description="show related unsigs sold", 
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
    async def _like(self, ctx: SlashContext, number: str):
        """show related unsigs sold"""  

        if ctx.channel.name == "general":
            await ctx.send(content=f"I'm not allowed to post here.\n Please go to #bot channel.")
            return

        asset_name = get_asset_name_from_idx(number)

        if not unsig_exists(number):
            await ctx.send(content=f"{asset_name} does not exist!\nPlease enter number between 0 and {MAX_AMOUNT}.")
            return
        else:
            if self.bot.sales:
                sales_numbers = get_numbers_from_assets(self.bot.sales)
                sales_by_date = sort_sales_by_date(self.bot.sales, descending=True)

                similar_unsigs = get_similar_unsigs(number, sales_numbers, structural=True)

                related_numbers = list(set().union(*similar_unsigs.values()))

                LIMIT_DISPLAY = 8
                related_numbers = related_numbers[:LIMIT_DISPLAY]
                selected_numbers = [int(number), *related_numbers]
    
                embed = embed_related(number, related_numbers, selected_numbers, sales_by_date, cols=3)
                add_disclaimer(embed, self.bot.sales_updated)

                if not related_numbers:
                    await ctx.send(embed=embed)
                    return

                try:
                    image_path = await gen_grid(selected_numbers, cols=3)

                    image_file = discord.File(image_path, filename="related.png")
                    if image_file:
                        embed.set_image(url="attachment://related.png")

                    delete_image_files(IMAGE_PATH)
                except:
                    await ctx.send(content=f"I can't generate the related of your unsig.")
                    return
                else:
                    await ctx.send(file=image_file, embed=embed)
            else:
                await ctx.send(content=f"Currently no sales data available...")
                return    

    @cog_ext.cog_slash(
        name="matches", 
        description="show available matches on marketplace", 
        guild_ids=GUILD_IDS,
        options=[
            create_option(
                name="number",
                description="number of unsig you want to match",
                required=True,
                option_type=3,
            )
        ]       
    )
    async def _matches(self, ctx: SlashContext, number: str):
        "show available matches on marketplace"
        
        if ctx.channel.name == "general":
            await ctx.send(content=f"I'm not allowed to post here.\n Please go to #bot channel.")
            return

        asset_name = get_asset_name_from_idx(number)

        if not unsig_exists(number):
            await ctx.send(content=f"{asset_name} does not exist!\nPlease enter number between 0 and {MAX_AMOUNT}.")
            return
        else:
            if self.bot.offers:
                offers_numbers = get_numbers_from_assets(self.bot.offers)

                matches = match_unsig(number, offers_numbers)
                best_matches = choose_best_matches(number, matches)

                embed = embed_matches(number, matches, best_matches, self.bot.offers)
                add_disclaimer(embed, self.bot.offers_updated)

                try:
                    image_path = await gen_grid_with_matches(best_matches)

                    image_file = discord.File(image_path, filename="matches.png")
                    if image_file:
                        embed.set_image(url="attachment://matches.png")

                    delete_image_files(IMAGE_PATH)
                except:
                    await ctx.send(content=f"I can't generate the matches of your unsig.")
                    return
                else:
                    await ctx.send(file=image_file, embed=embed)

            else:
                await ctx.send(content=f"Currently no marketplace data available...")
                return   

    @cog_ext.cog_slash(
        name="floor", 
        description="show cheapest unsigs on marketplace", 
        guild_ids=GUILD_IDS        
    )
    async def _floor(self, ctx: SlashContext):
        """show cheapest unsigs on marketplace""" 

        if ctx.channel.name != "bot":
            await ctx.send(content=f"I'm not allowed to post here.\n Please go to #bot channel.")
            return
        
        if self.bot.offers:
            filtered = filter_assets_by_type(self.bot.offers, "listing", "offer", "Buy")
            ordered_by_props = order_by_num_props(filtered)

            embed = embed_offers(ordered_by_props)
            add_policy(embed)
            add_disclaimer(embed, self.bot.offers_updated)

            await ctx.send(embed=embed)
        else:
            await ctx.send(content=f"Currently no marketplace data available...")
            return
    
    @cog_ext.cog_slash(
        name="sell", 
        description="offer your unsig for sale", 
        guild_ids=GUILD_IDS,
        options=[
            create_option(
                name="number",
                description="number unsig you want to sell",
                required=True,
                option_type=3,
            ),
            create_option(
                name="price",
                description="price you want to sell",
                required=True,
                option_type=3,
            )
        ]       
    )
    async def _sell(self, ctx: SlashContext, number: str, price: str):
        """offer your unsig for sale"""

        SELLING_CHANNEL = "selling"

        if ctx.channel.name != SELLING_CHANNEL:
            await ctx.send(content=f"Please post your offer in the #{SELLING_CHANNEL} channel.")
            return
            
        asset_name = get_asset_name_from_idx(number)

        if not unsig_exists(number):
            await ctx.send(content=f"{asset_name} does not exist!\nPlease enter number between 0 and {MAX_AMOUNT}.")
        else:
            number = str(int(number))

            unsig_data = get_unsig_data(number)
            minting_data = get_minting_data(number)

            seller = ctx.author.name

            embed = await embed_offer(seller, price, asset_name, unsig_data, minting_data)

            await ctx.send(embed=embed)


def setup(bot: commands.Bot):
    bot.add_cog(Market(bot))
    print("market cog loaded")