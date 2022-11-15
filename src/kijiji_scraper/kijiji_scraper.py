import re
from copy import copy

import nltk
from loguru import logger as log
import requests
from bs4 import BeautifulSoup
import json
from kijiji_ad import KijijiAd
from pathlib import Path



def extract_phone_numbers(string):
    r = re.compile(r'(\d{3}[-\.\s]??\d{3}[-\.\s]??\d{4}|\(\d{3}\)\s*\d{3}[-\.\s]??\d{4}|\d{3}[-\.\s]??\d{4})')
    phone_numbers = r.findall(string)
    return [re.sub(r'\D', '', number) for number in phone_numbers]

def extract_email_addresses(string):
    r = re.compile(r'[\w\.-]+@[\w\.-]+')
    return r.findall(string)

class KijijiScraper():

    def __init__(self, filename="ads.json"):
        self.filepath = Path().absolute().joinpath(filename) if filename else None
        self.all_ads = {}
        self.new_ads = {}

        self.third_party_ads = []
        self.exclude_list = []

        self.load_ads()

    # Reads given file and creates a dict of ads in file
    def load_ads(self):
        # If filepath is None, just skip local file
        if self.filepath:
            # If the file doesn't exist create it
            if not self.filepath.exists():
                ads_file = self.filepath.open(mode='w')
                ads_file.write("{}")
                ads_file.close()
                return

            with self.filepath.open(mode="r") as ads_file:
                self.all_ads = json.load(ads_file)

    # Save ads to file
    def save_ads(self):
        # If filepath is None, just skip local file
        if self.filepath:
            with self.filepath.open(mode="w") as ads_file:
                json.dump(self.all_ads, ads_file)

    # Set exclude list
    def set_exclude_list(self, exclude_words):
        self.exclude_list = self.words_to_lower(exclude_words)

    # Pulls page data from a given kijiji url and finds all ads on each page
    def scrape_kijiji_for_ads(self, url,n_pages=3):
        self.new_ads = {}
        # Keep track of originnal url to use for exclude list later
        original_url = copy(url)
        email_title = None
        count_pages = 0
        while url:
            # Get the html data from the URL
            log.debug(f"Getting page {count_pages} for {original_url}")
            page = requests.get(url)
            soup = BeautifulSoup(page.content, "html.parser")

            # If the email title doesnt exist pull it from the html data
            if email_title is None:
                email_title = self.get_email_title(soup)

            # Find ads on the page
            self.find_ads(soup)

            # Set url for next page of ads
            url = soup.find('a', {'title': 'Next'})
            if url:
                url = 'https://www.kijiji.ca' + url['href']
            if count_pages > n_pages:
                log.warning(f"Reached max number of pages for {original_url} - {n_pages}")
                break
            count_pages += 1
        if self.new_ads:
            for k, v in self.new_ads.items():
                v['original_url'] = original_url
        return self.new_ads, email_title

    def find_ads(self, soup):
        # Finds all ad trees in page html.
        kijiji_ads = soup.find_all("div", {"class": "search-item regular-ad"})

        # If no ads use different class name
        if not kijiji_ads:
            kijiji_ads = soup.find_all("div", {"class": "search-item"})

        # Find all third-party ads to skip them
        third_party_ads = soup.find_all("div", {"class": "third-party"})

        # Use different class name if no third party ads found
        if not third_party_ads:
            third_party_ads = soup.find_all(
                "div", {"class": "search-item showcase top-feature"})

        for ad in third_party_ads:
            third_party_ad_id = KijijiAd(ad).id
            self.third_party_ads.append(third_party_ad_id)

        # Create a dictionary of all ads with ad id being the key
        for ad in kijiji_ads:
            kijiji_ad = KijijiAd(ad)

            # If any of the title words match the exclude list then skip
            condition_exclude = False
            full_text = kijiji_ad.title.lower() + " " + kijiji_ad.info["Description"].lower()
            full_text_word_list = set(nltk.word_tokenize(full_text)) | set(extract_phone_numbers(full_text)) \
                                  | set(extract_email_addresses(full_text))

            for word in self.exclude_list:
                # check if two or more words are in the word
                if (word.lower() in full_text_word_list) or ( (len(word.split()) > 1) and word.lower() in full_text):
                    log.info(f"Skipping ad {kijiji_ad.id} because it contains <{word}> ")
                    condition_exclude = True
                    break


            if not condition_exclude:

                # Skip third-party ads and ads already found
                if (kijiji_ad.id not in self.all_ads and
                        kijiji_ad.id not in self.third_party_ads):
                    self.new_ads[kijiji_ad.id] = kijiji_ad.info
                    self.all_ads[kijiji_ad.id] = kijiji_ad.info

    def get_email_title(self, soup):
        email_title_location = soup.find('div', {'class': 'message'})

        if email_title_location:

            if email_title_location.find('strong'):
                email_title = email_title_location.find('strong') \
                    .text.strip('"').strip(" »").strip("« ")
                return self.format_title(email_title)

        content = soup.find_all('div', class_='content')
        for i in content:

            if i.find('strong'):
                email_title = i.find('strong') \
                    .text.strip(' »').strip('« ').strip('"')
                return self.format_title(email_title)

        return ""

    # Makes the first letter of every word upper-case
    def format_title(self, title):
        new_title = []

        title = title.split()
        for word in title:
            new_word = ''
            new_word += word[0].upper()

            if len(word) > 1:
                new_word += word[1:]

            new_title.append(new_word)

        return ' '.join(new_title)

    # Returns a given list of words to lower-case words
    def words_to_lower(self, words):
        return [word.lower() for word in words]
