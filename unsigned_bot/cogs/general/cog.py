"""
Module for general cog
"""

import discord
from discord.ext import commands
from discord_slash import cog_ext, SlashContext
from discord_slash.utils.manage_commands import create_choice, create_option

from unsigned_bot.config import GUILD_IDS
from unsigned_bot.fetch import get_ipfs_url_from_file
from .embeds import (
    embed_marketplaces,
    embed_policy,
    embed_gen_unsig,
    embed_whales,
    embed_rarity,
    embed_v2,
    embed_treasury,
    embed_verse
)


class General(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @cog_ext.cog_slash(
        name="faq", 
        description="Everything you should know about unsigs", 
        guild_ids=GUILD_IDS,
        options=[
            create_option(
                name="topics",
                description="Choose topic",
                required=True,
                option_type=3,
                choices=[
                    create_choice(
                        name="Where to buy?",
                        value="buy_unsig"
                    ),
                    create_choice(
                        name="Policy ID",
                        value="policy_id"
                    ),
                    create_choice(
                        name="Generate unsig",
                        value="gen_unsig"
                    ),
                    create_choice(
                        name="About whales",
                        value="whales"
                    ),
                    create_choice(
                        name="About rarity",
                        value="rarity"
                    ),
                    create_choice(
                        name="WEN V2?",
                        value="v2"
                    ),
                    create_choice(
                        name="Treasury unsigned_DAO",
                        value="treasury"
                    )
                ]
            )
        ]        
    )
    async def _faq(self, ctx: SlashContext, topics: str):
        """show important information"""
        if not topics:
            await ctx.send(content=f"Please choose a topic...")
            return
        else:
            EMBED_TOPICS = {
                "buy_unsig": embed_marketplaces,
                "policy_id": embed_policy,
                "gen_unsig": embed_gen_unsig,
                "whales": embed_whales,
                "rarity": embed_rarity,
                "v2": embed_v2,
                "treasury": embed_treasury
            }

            embed_func = EMBED_TOPICS.get(topics)
            embed = embed_func()
            
            await ctx.send(embed=embed)

    @cog_ext.cog_slash(
        name="verse", 
        description="One unsig to rule them all...", 
        guild_ids=GUILD_IDS,
    )
    async def _verse(self, ctx: SlashContext):
        embed = await embed_verse()
        
        await ctx.send(embed=embed)
    
    # @cog_ext.cog_slash()


def setup(bot):
    bot.add_cog(General(bot))
    print(f"general cog loaded")