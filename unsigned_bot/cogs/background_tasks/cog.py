"""
Module for background tasks cog
"""

from datetime import datetime
import asyncio
import discord
from discord.ext import commands
from discord.ext.tasks import loop

from unsigned_bot import ROOT_DIR
from unsigned_bot.log import logger
from unsigned_bot.utility.files_util import load_json, save_json
from unsigned_bot.config import INVERVAL_LOOP, SALES_CHANNEL_ID
from unsigned_bot.cogs.data.embeds import embed_certificate
from unsigned_bot.aggregate import aggregate_data_from_marketplaces
from unsigned_bot.fetch import get_new_certificates
from unsigned_bot.parsing import (
    filter_new_sales,
    filter_by_time_interval,
    filter_certs_by_time_interval
)
from unsigned_bot.twitter import create_twitter_api, tweet_sales
from .embeds import embed_sale


class BackgroundTasks(commands.Cog):
    """handle background tasks"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        """Start task loop"""
        if not self.perform_tasks.is_running():
            self.perform_tasks.start()

    async def post_sales(self, sales: list):
        """Post latest sales in specified channel"""
        try:
            channel = self.bot.get_channel(SALES_CHANNEL_ID)
        except:
            logger.warning("Can not find the sales feed channel")
        else:
            for sale_data in sales:
                embed = await embed_sale(sale_data)

                message = await channel.send(embed=embed)
                await message.publish()

    async def post_certs(self, new_certs: dict, num_certificates: int):
        """Post new certificates in specified channel"""
        try:
            channel = self.bot.get_channel(SALES_CHANNEL_ID)
        except:
            logger.warning("Can not find the sales feed channel")
        else:
            for _ , cert_data in new_certs.items():
                metadata = cert_data.get("onchain_metadata")
                asset_name = metadata.get("Unsig number")
                unsig_number = asset_name.replace("#", "")
                unsig_number = str(int(unsig_number)) #remove leading zeros

                embed = embed_certificate(unsig_number, cert_data, num_certificates, feed=True)
                message = await channel.send(embed=embed)
                try:
                    await message.publish()
                except:
                    logger.warning(f"Can not publish certificate of {asset_name}")

    @loop(seconds=INVERVAL_LOOP)
    async def perform_tasks(self):
        """Loop to repeat tasks after given time interval"""

        # === fetch and update sales data; post and tweet new sales ===
        try:
            sales_data = await aggregate_data_from_marketplaces(sold=True)
        except:
            logger.warning("Fetching sales data failed")
        else:
            if sales_data:
                new_sales = filter_new_sales(self.bot.sales, sales_data)
                self.bot.sales_updated = datetime.utcnow()

                logger.info("Sales updated")

                if new_sales:
                    self.bot.sales.extend(new_sales)
                    save_json(f"{ROOT_DIR}/data/json/sales.json", self.bot.sales)
            
                    new_sales = filter_by_time_interval(new_sales, INVERVAL_LOOP * 1000)

                    if self.bot.guild.name == "unsigned_algorithms":
                        await asyncio.sleep(2)
                        await self.post_sales(new_sales)

                        if not self.bot.twitter_api:
                            self.bot.twitter_api = create_twitter_api()

                        try:
                            await tweet_sales(self.bot.twitter_api, new_sales)
                        except:
                            logger.warning("Tweeting sales failed")      

        # === fetch and update offers data ===
        try:
            offers_data = await aggregate_data_from_marketplaces(sold=False)
        except:
            logger.warning("Fetching offers data failed")
        else:
            if offers_data:
                self.bot.offers = offers_data
                self.bot.offers_updated = datetime.utcnow()

                logger.info("Offers updated")

         # === fetch, update and post new certificates ===
        try:
            certificates = load_json(f"{ROOT_DIR}/data/json/certificates.json")
            new_certificates = get_new_certificates(certificates)
            logger.info(f"{len(new_certificates)} new certificates found")
            
            if new_certificates:
                self.bot.certs.update(new_certificates)
                save_json(f"{ROOT_DIR}/data/json/certificates.json", self.bot.certs)

                if self.bot.guild.name == "unsigned_algorithms":
                    num_certificates = len(self.bot.certs.keys())
                    new_certificates = filter_certs_by_time_interval(new_certificates, INVERVAL_LOOP * 1000)
                    
                    await asyncio.sleep(2)
                    await self.post_certs(new_certificates, num_certificates)
                
            self.bot.certs_updated = datetime.utcnow()
        except:
            logger.warning("Updating certificates failed")

        logger.info("Background tasks finished")


def setup(bot: commands.Bot):
    bot.add_cog(BackgroundTasks(bot))
    logger.debug(f"{BackgroundTasks.__name__} loaded")