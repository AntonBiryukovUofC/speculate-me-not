import os
from datetime import datetime
from typing import Dict

import dropbox
import dropboxdrivefs as dbx
import requests_cache
import telegram
from bs4 import BeautifulSoup
from loguru import logger as log
import requests

cached_requests = requests_cache.CachedSession('http_cache', backend='sqlite',
                                               use_temp=True)


class DropboxDriveFS(dbx.DropboxDriveFileSystem):

    def __init__(self, token, refresh_token=None, app_key=None, app_secret=None, *args, **storage_options):
        super(dbx.DropboxDriveFileSystem, self).__init__(token=token, *args, **storage_options)
        self.token = token
        self.refresh_token = refresh_token
        self.app_key = app_key
        self.app_secret = app_secret
        self.connect()

    def connect(self):
        self.dbx = dropbox.Dropbox(self.token, oauth2_refresh_token=self.refresh_token,
                                   app_secret=self.app_secret, app_key=self.app_key)
        self.session = requests.Session()

        self.session.auth = ("Authorization", self.token)


class AdScraper:
    def __init__(self, all_ads: Dict, sent_ads: Dict = None,
                 dropbox_token=None,
                 telegram_token=None, telegram_chat_id=None, ignore_business_ads=True):
        self.ignore_business_ads = ignore_business_ads
        self.telegram_token = telegram_token
        self.telegram_chat_id = telegram_chat_id
        self.all_ads = all_ads.copy()
        self.ads = all_ads.copy()
        # Load sent and all adds, and then calculate the difference
        if sent_ads is None:
            self.sent_ads = {}
        else:
            self.sent_ads = sent_ads

        for k in self.sent_ads.keys():
            if k in self.ads.keys():
                del self.ads[k]
        log.debug(f'Found {len(self.ads)} new ads')
        self.ids = list(self.ads.keys())

        if dropbox_token is None:
            dropbox_token = os.environ['DROPBOX_ACCESS_TOKEN']
        if telegram_token is None:
            telegram_token = os.environ['TELEGRAM_TOKEN']
        if telegram_chat_id is None:
            telegram_chat_id = os.environ['TELEGRAM_CHAT_ID']
        # self.dropbox_fs = dbx.DropboxDriveFileSystem(token=dropbox_token,
        #                                              app_key = os.environ['APP_KEY'],
        #                                              refresh_token = os.environ['REFRESH_TOKEN'])
        self.dropbox_fs = DropboxDriveFS(token=dropbox_token,
                                         app_key=os.environ['APP_KEY'],
                                         refresh_token=os.environ['REFRESH_TOKEN'],
                                         app_secret=os.environ['APP_SECRET'])
        self.telegram_token = telegram_token
        self.telegram_chat_id = telegram_chat_id
        self.bot = telegram.Bot(self.telegram_token)

    def send_telegram_ad(self, ad):
        imgs = self.parse_ad_images(ad)
        imgs = imgs[:4]
        current_ts_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        if imgs is not None and len(imgs) > 0:
            media = [telegram.InputMediaPhoto(img) for img in imgs]
            media[0].caption = f"{ad['Title']} - {ad['Price']} - {ad['Url']}"
        else:
            media = []

        is_business = self.is_posted_by_business(ad)

        if self.ignore_business_ads and is_business:
            log.info(f"Skipping (ignore business = {self.ignore_business_ads}) business ad: {ad['Url']}")
            ad['time_sent'] = current_ts_str
            ad['is_business'] = is_business
            self.sent_ads[ad['Id']] = ad
            return 0

        try:
            if len(media) > 0:
                resp = self.bot.send_media_group(chat_id=self.telegram_chat_id, media=media)
                if resp:
                    ad['time_sent'] = current_ts_str
                    self.sent_ads[ad['Id']] = ad
            else:
                ad['time_sent'] = current_ts_str
                self.sent_ads[ad['Id']] = ad
        except Exception as e:
            log.exception(e)
        return 0

    def parse_ad_images(self, ad):
        url = ad['Url']
        log.debug(f"Getting images URLs from ad: {url}")
        page = cached_requests.get(url)
        soup = BeautifulSoup(page.content, "html.parser")
        images = soup.find_all('img')
        images_url = [im.get('src') for im in images]
        log.debug(f"Found {len(images_url)} images")
        return images_url

    def is_posted_by_business(self, ad):
        url = ad['Url']
        log.debug(f"Getting images URLs from ad: {url}")
        page = cached_requests.get(url)
        soup = BeautifulSoup(page.content, "html.parser")
        ad_type = soup.find_all('div', {'class': lambda x: x
                                                           and 'line' in x.split('-')
                                        })
        ad_types = set([x.text.lower() for x in ad_type])
        if 'business' in ad_types:
            return True
        else:
            return False

    def save_ad_artefacts(self, ad, ad_id, destination_folder, fs):
        imgs = self.parse_ad_images(ad)
        for i, img in enumerate(imgs):

            if img is not None:
                try:
                    final_dest = os.path.join(f'{destination_folder}/{ad_id}/', img.split('/')[-1] + '.jpg')
                    log.debug(f"Saving image {i + 1}/{len(imgs)} to {final_dest}")
                    img_resp = cached_requests.get(img)
                    with fs.open(final_dest, mode='wb') as f:
                        f.write(img_resp.content)
                    log.info(f"Uploaded {img} to {final_dest}")
                except Exception as e:
                    log.error('Failed to deliver image!')
                    log.exception(e)
        return 0
