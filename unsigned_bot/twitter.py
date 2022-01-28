"""
Module for communication with Twitter API
"""

import os
import requests
import tweepy

from unsigned_bot import IMAGE_PATH
from unsigned_bot.parsing import parse_sale, get_unsig_url, get_idx_from_asset_name
from unsigned_bot.draw import gen_unsig, delete_image_files
from unsigned_bot.emojis import *

from dotenv import load_dotenv
load_dotenv() 

FILE_DIR = os.path.dirname(os.path.abspath(__file__))



def create_twitter_api():
    consumer_key = os.getenv("CONSUMER_KEY")
    consumer_secret = os.getenv("CONSUMER_SECRET")
    access_token = os.getenv("ACCESS_TOKEN")
    access_token_secret = os.getenv("ACCESS_TOKEN_SECRET")

    auth = tweepy.OAuthHandler(consumer_key, consumer_secret)
    auth.set_access_token(access_token, access_token_secret)
    api = tweepy.API(auth, wait_on_rate_limit=True)

    try:
        api.verify_credentials()
        print("Twitter API verified!")
    except Exception as e:
        print("Creating twitter api failed!")

    return api

async def tweet_sales(api, sales):
    for sale in sales:
        marketplace_name, num_props, price, date = parse_sale(sale)
        unsig_number = get_idx_from_asset_name(marketplace_name)
        unsig_url = get_unsig_url(str(unsig_number))
        
        tweet_string = f"\n...\n{EMOJI_CART} unsig{str(unsig_number).zfill(5)} SOLD {EMOJI_CART}\n\n{EMOJI_MONEYBAG} {price:,.0f} $ADA\n\n{EMOJI_CALENDAR} {date}\n\n{EMOJI_GEAR} {num_props} properties\n\n#unsigsold #unsig{str(unsig_number).zfill(5)}"

        try:
            filepath_image = await gen_unsig(unsig_number, dim=2048)

            media_img = api.media_upload(filename=filepath_image)
            api.update_status(status=tweet_string, media_ids=[media_img.media_id])

        except:
            tweet_string += f"\n{unsig_url}"
            api.update_status(status=tweet_string)
        finally:
            delete_image_files(IMAGE_PATH, suffix="png")

async def download_image(num, url) -> str:
    filename = f'img/temp_{num}.png'
    response = requests.get(url, stream=True)
    if response.status_code == 200:
        with open(filename, 'wb') as image:
            for chunk in response:
                image.write(chunk)
    
    return filename
    