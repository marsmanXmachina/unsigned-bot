"""
Module for cog specific discord embeds
"""

import discord

from unsigned_bot.fetch import get_wallet_balance, get_ipfs_url_from_file
from unsigned_bot.constants import POLICY_ID, TREASURY_ADDRESS
from unsigned_bot.emojis import *
from unsigned_bot.urls import *


def embed_marketplaces():
    """Return discord embed for marketplaces and escrows"""
    title = f"{EMOJI_SHOPPINGBAGS} Where to buy? {EMOJI_SHOPPINGBAGS}"
    description="Places to buy your first unsig..."
    color=discord.Colour.dark_blue()

    embed = discord.Embed(title=title, description=description, color=color)

    marketplaces_str = ""
    for marketplace, marketplace_url in MARKETPLACES.items():
        marketplace_str = f"{EMOJI_ARROW_RIGHT} [{marketplace}]({marketplace_url})\n"
        marketplaces_str += marketplace_str

    embed.add_field(name=f"Marketplaces", value=marketplaces_str, inline=False)

    escrows_str = ""
    for escrow, escrow_url in DISCORD_ESCROWS.items():
        escrow_str = f"{EMOJI_ARROW_RIGHT} [{escrow}]({escrow_url})\n"
        escrows_str += escrow_str

    escrow_rules_str = "`=> Don't trust, verify!\n=> Minimize steps where trust is needed.\n=> Minimize potential loss in worst case scenario.`"
    
    embed.add_field(name=f"{EMOJI_WARNING} Be careful when using escrow {EMOJI_WARNING}", value=escrow_rules_str, inline=False)
    embed.add_field(name=f"Escrows on discord server", value=escrows_str, inline=False)

    embed.set_footer(text=f"The server has no affiliation with the marketplace nor listed prices.\n\nAlways check policy id:\n{POLICY_ID}")

    return embed

def embed_policy():
    """Return discord embed for policy id"""
    title = f"{EMOJI_WARNING} Unsigs Policy ID {EMOJI_WARNING}"
    description="The official one and only..."
    color=discord.Colour.orange()

    embed = discord.Embed(title=title, description=description, color=color)
    embed.add_field(name=f"Always check the policy ID", value=f"`{POLICY_ID}`", inline=False)

    return embed

def embed_gen_unsig():
    """Return discord embed for instructions to generate unsig"""
    title = f"{EMOJI_PAINTBRUSH} Generate your unsig {EMOJI_PAINTBRUSH}"
    description="In the footsteps of Sol LeWitt..."
    color=discord.Colour.magenta()

    embed = discord.Embed(title=title, description=description, color=color)

    video_url = "https://www.youtube.com/watch?v=lvTAjcLaQjU"
    embed.add_field(name="Wanna generate your unsig from onchain data?", value=f"{EMOJI_ARROW_RIGHT} Follow the instructions in [this video]({video_url}).\n", inline=False)

    ingredients_str = ""
    ingredients = ["metadata of unsig00000", "metadata of your unsig", "python environment / jupyter notebook"]

    for ingredient in ingredients:
        ingredients_str += f" {EMOJI_ARROW_RIGHT} {ingredient} \n"

    embed.add_field(name=f"What do you need?", value=ingredients_str, inline=False)
    embed.add_field(name=f"{EMOJI_BULB} Bot Tip", value="Use my `/metadata` command to get the data you need", inline=False)

    return embed

def embed_whales():
    """Return discord embed for whales topic"""
    title = f"{EMOJI_WHALE} About 'whales' {EMOJI_WHALE}"
    description="They're NOT an alien species..."
    color=discord.Colour.blue()

    embed = discord.Embed(title=title, description=description, color=color)

    TWEETS = {
        "Brainpicking an early whale": "https://twitter.com/unsigned_algo/status/1445531270302212102?s=21",
        "Skin in the game": "https://twitter.com/unsigned_algo/status/1445204554564268040?s=21",
        "Worries about dumping": "https://twitter.com/unsigned_algo/status/1445205162981683200?s=21"
    }

    tweets_str = ""
    for title, link in TWEETS.items():
        tweets_str += f"=> ['{title}']({link})\n"

    embed.add_field(name=f"Some interesting tweets...", value=tweets_str, inline=False)

    return embed

def embed_rarity():
    """Return discord embed for rarity topic"""
    title = f"{EMOJI_SNOWFLAKE} About rarity {EMOJI_SNOWFLAKE}"
    description="You aren't as unique as you think..."
    color=discord.Colour.blue()

    embed = discord.Embed(title=title, description=description, color=color)

    RARITY_RESOURCES = {
        "Statistics and rare bananas": "https://discord.com/channels/843043397526093885/843043398592233485/873911353381892136",
        "Kelumax Repository": "https://drive.google.com/drive/folders/1z8J1AsrLlEJ6WnLj2-IbgFvfLpjx1H8X?usp=sharing"
    }

    info_str = ""
    for name, link in RARITY_RESOURCES.items():
        info_str += f"{EMOJI_ARROW_RIGHT} [{name}]({link})\n"

    embed.add_field(name=f"{EMOJI_CERT} Resources {EMOJI_CERT}", value=info_str, inline=False)

    RARITY_TOOLS = {
        "NFT RARITY": "https://nftrarity.is/#/unsigned_algorithms"
    }

    tools_str = ""
    for name, link in RARITY_TOOLS.items():
        tools_str += f"{EMOJI_ARROW_RIGHT} [{name}]({link})\n"

    embed.add_field(name=f"{EMOJI_GEAR} Tools {EMOJI_GEAR}", value=tools_str, inline=False)

    return embed

def embed_v2():
    """Return discord embed for v2 topic"""
    title = f"{EMOJI_CROWN} WEN V2??? {EMOJI_CROWN}"
    description="Patience you must have..."
    color=discord.Colour.dark_magenta()  

    embed = discord.Embed(title=title, description=description, color=color)

    quote_str = "WHEN ANNOUNCEMENTS?\nHOW WILL US HOLDERS BENEFIT?\nWHAT IS THE UTILITY?..."
    embed.add_field(name=f"Questions from 'The King'", value=quote_str, inline=False)

    v2_tweet_url = "https://twitter.com/unsigned_algo/status/1445343171496398853?s=21"
    answer_str = f"[What v2 is about?]({v2_tweet_url})"
    embed.add_field(name=f"Answer from 'The Great'", value=answer_str, inline=False)

    return embed

def embed_treasury():
    """Return discord embed for treasury monitoring"""
    title = f"{EMOJI_MONEYBAG} Treasury {EMOJI_MONEYBAG}"
    description="administered by the unsigned_DAO"
    color=discord.Colour.orange()

    embed = discord.Embed(title=title, description=description, color=color)

    pool_link = f"{POOL_PM_URL}/{TREASURY_ADDRESS}"
    cardanoscan_link = f"{CARDANOSCAN_URL}/address/{TREASURY_ADDRESS}"
    wallet_str = f"view on [pool.pm]({pool_link})\nview on [cardanoscan.io]({cardanoscan_link})"
    embed.add_field(name=f"Wallet", value=wallet_str, inline=False)

    balance = get_wallet_balance(TREASURY_ADDRESS)
    embed.add_field(name=f"Current Balance", value=f"`₳{balance/1000000:,.0f}`", inline=False)

    return embed

async def embed_verse():
    """Return discord embed with unsig_verse"""
    title = f"{EMOJI_CERT} Unsig verse {EMOJI_CERT}"
    description="..."
    color=discord.Colour.dark_blue()

    embed = discord.Embed(title=title, description=description, color=color) 

    verse = """Two distributions for the algorithm in numpy
        Three fundamental colours which set the tone
        Four numbers for the values to multiply
        Four rotations as the quarters of a circle have shown
        
        In the unsig land, 
        where all combined layers lie...
        One unsig to rule them all, 
        One unsig to find them
        One unsig to bring them all, 
        and in its darkness bind them
        """
    embed.add_field(name="One unsig to rule them all", value=f"{verse}", inline=False)

    image_url = await get_ipfs_url_from_file("unsig00000")
    embed.set_image(url=image_url)

    return embed