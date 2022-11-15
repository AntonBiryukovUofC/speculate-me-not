import json
import re

import nltk
from dotenv import load_dotenv, find_dotenv
import requests_cache
from bs4 import BeautifulSoup

import streamlit as st

from src.adscraper import AdScraper

@st.cache
def load_ads(json_loc):
    with open(json_loc, "r") as f:
        all_ads = json.load(f)
    return all_ads

def extract_email_addresses(string):
    r = re.compile(r'[\w\.-]+@[\w\.-]+')
    return r.findall(string)

def extract_phone_numbers(string):
    r = re.compile(r'(\d{3}[-\.\s]??\d{3}[-\.\s]??\d{4}|\(\d{3}\)\s*\d{3}[-\.\s]??\d{4}|\d{3}[-\.\s]??\d{4})')
    phone_numbers = r.findall(string)
    return [re.sub(r'\D', '', number) for number in phone_numbers]

requests = requests_cache.CachedSession('http_cache', backend='sqlite',
                                        use_temp=True)
load_dotenv(find_dotenv())

st.title("Kijiji Explore")
st.write("Load ads json file")
json_loc = st.text_input("ads.json file location", value="/home/anton/Downloads/sent_ads.json")

all_ads = load_ads(json_loc)
scraper = AdScraper(all_ads)

ad = all_ads['1638084343']
st.json(ad)
page = requests.get(ad['Url'])
soup = BeautifulSoup(page.content, "html.parser")
ad_type = soup.find_all('div', {'class': lambda x: x
                       and 'line' in x.split('-')
             })
ad_types = set([x.text for x in ad_type])
for adt in ad_types:
    st.write(adt)

full_text= ad['Title'].lower() + " " + ad['Description'].lower()


    # scraper.save_ad_artefacts(ad=ad,ad_id=k,
    #                           destination_folder='/Data/kijiji_ads',
    #                           fs = scraper.dropbox_fs)
    # #imgs = parse_ad(ad["Url"])
    #for img in imgs:
    #    st.image(img, width=300,caption=img)

