import json

from dotenv import load_dotenv, find_dotenv
import requests_cache

import streamlit as st

from src.adscraper import AdScraper

requests = requests_cache.CachedSession('http_cache', backend='sqlite',
                                        use_temp=True)
load_dotenv(find_dotenv())

st.title("Kijiji Explore")
st.write("Load ads json file")
json_loc = st.text_input("ads.json file location", value="/home/anton/.kijiji_scraper/config_ads.json")
scraper = AdScraper(json_loc)


with open(json_loc, "r") as f:
    ads = json.load(f)
for k,ad in ads.items():
    st.write(f' # {k}: {ad["Title"]}')
    scraper.send_telegram_ad(ad)

    # scraper.save_ad_artefacts(ad=ad,ad_id=k,
    #                           destination_folder='/Data/kijiji_ads',
    #                           fs = scraper.dropbox_fs)
    # #imgs = parse_ad(ad["Url"])
    #for img in imgs:
    #    st.image(img, width=300,caption=img)

