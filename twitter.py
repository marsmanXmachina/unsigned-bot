import os
import time

import tweepy
import requests

import asyncio

from emojis import *


from parsing import parse_sale, get_unsig_url, get_idx_from_asset_name

from draw import gen_image_for_tweet, gen_animation, delete_image_files

from dotenv import load_dotenv
load_dotenv() 

FILE_DIR = os.path.dirname(os.path.abspath(__file__))
IMAGE_PATH = f"{FILE_DIR}/img"

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

        tweet_string = f"\n...\n{EMOJI_CART} unsig{str(unsig_number).zfill(5)} SOLD {EMOJI_CART}\n\n{EMOJI_MONEYBACK} {price:,.0f} $ADA\n\n{EMOJI_CALENDAR} {date}\n\n{EMOJI_GEAR} {num_props} properties\n\n#unsigsold #unsig{str(unsig_number).zfill(5)}"
    
        try:
            # await gen_image_for_tweet(str(unsig_number))
            # filepath = f"img/tweet_{unsig_number}.png"

            await gen_animation(str(unsig_number))
            filepath = f"img/animation_{unsig_number}.gif"
            media = api.media_upload(filename=filepath, chunked=True)
            api.update_status(status=tweet_string, media_ids=[media.media_id])

            delete_image_files(IMAGE_PATH, suffix="gif")
            
        except:
            tweet_string += f"\n{unsig_url}"
            api.update_status(status=tweet_string)

            delete_image_files(IMAGE_PATH, suffix="gif")


def download_image(num, url) -> str:
    filename = f'temp_{num}.png'
    response = requests.get(url, stream=True)
    if response.status_code == 200:
        with open(filename, 'wb') as image:
            for chunk in response:
                image.write(chunk)
    
    return filename

# if __name__ == "__main__":

#     twitter_api = create_twitter_api()

#     sales = [
# {"assetid": "unsig_13751", "unit": "0e14267a8020229adc0184dd25fa3174c3f7d6caadcb4425c70e7c04756e7369673133373531", "price": 992000000, "sold": True, "id": "614bdecc57294040c06ff657", "date": 1634348080120, "num_props": 5},
# {"assetid": "unsig_24346", "unit": "0e14267a8020229adc0184dd25fa3174c3f7d6caadcb4425c70e7c04756e7369673234333436", "price": 1000000000, "sold": True, "id": "616a1758ddc02787669337ca", "date": 1634363294132, "num_props": 5}, 
# {"assetid": "unsig_30189", "unit": "0e14267a8020229adc0184dd25fa3174c3f7d6caadcb4425c70e7c04756e7369673330313839", "price": 1000000000, "sold": True, "id": "616a17531c651312b0f4f153", "date": 1634363094784, "num_props": 6},
# {"assetid": "unsig_30167", "unit": "0e14267a8020229adc0184dd25fa3174c3f7d6caadcb4425c70e7c04756e7369673330313637", "price": 1400000000, "sold": True, "id": "616654418cd55f4d2a745c1a", "date": 1634364508534, "num_props": 6}
#     ]

#     asyncio.run(tweet_sales(twitter_api, sales))