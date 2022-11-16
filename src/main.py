import json
import os.path
from json import JSONDecodeError

import yaml
import requests_cache
from loguru import logger as log
from tqdm import tqdm

from adscraper import AdScraper, DropboxDriveFS
import typer

requests = requests_cache.CachedSession('http_cache', backend='sqlite',
                                        use_temp=True)

app = typer.Typer()
ALL_ADS_JSON_LOC_DROPBOX = '/Data/ads_jsons/all_ads.json'
SENT_ADS_JSON_LOC_DROPBOX = '/Data/ads_jsons/sent_ads.json'


def conf_callback(ctx: typer.Context, param: typer.CallbackParam, value: str):
    if value:
        typer.echo(f"Loading config file: {value}")
        try:
            with open(value, 'r') as f:  # Load config file
                conf = yaml.safe_load(f)
            ctx.default_map = ctx.default_map or {}  # Initialize the default map
            ctx.default_map.update(conf)  # Merge the config dict into default_map
            log.info(f'Running scraping with config: {conf}')

        except Exception as ex:
            raise typer.BadParameter(str(ex))
    return value


def open_json(loc: str):
    """
    Open a json file and return the json object. Attempt to fix invalid json.

    :param loc:
    :return:
    """
    res = {}
    invalid_json = False
    with open(loc, "r") as f:
        txt = f.read()
        try:
            res = json.loads(txt)
        except JSONDecodeError:
            invalid_json = True
            print('Invalid json! Attempting to re-read')

    if invalid_json:
        for i in tqdm(range(len(txt), 0, -1)):
            try:
                res = json.loads(txt[:i] + '}')
                break
            except JSONDecodeError:
                print('Unable to parse json at index', i)

    return res


@app.command()
def main(
        config: str = typer.Option("", callback=conf_callback, is_eager=True),
        dropbox_token: str = typer.Option("", envvar="DROPBOX_ACCESS_TOKEN"),
        telegram_token: str = typer.Option("", envvar="TELEGRAM_TOKEN"),
        telegram_chat_id: str = typer.Option("", envvar="TELEGRAM_CHAT_ID"),
        all_ads_json_loc: str = typer.Option("/home/anton/.kijiji_scraper/config_ads.json"),
        sent_ads_json_loc: str = typer.Option("/home/anton/.kijiji_scraper/sent_ads.json"),
        sync_dropbox_locations: bool = typer.Option(True, flag_value=True),
        ignore_business_ads: bool = typer.Option(True, flag_value=True)):
    dropbox_fs = DropboxDriveFS(token=dropbox_token,
                                app_key=os.environ['APP_KEY'],
                                refresh_token=os.environ['REFRESH_TOKEN'],
                                app_secret=os.environ['APP_SECRET'])
    if sync_dropbox_locations:
        # We need to download the json files from dropbox and save into json_loc:
        log.info(f'Syncing dropbox locations with local passed locations {sent_ads_json_loc}')
        try:
            # dropbox_fs.download(ALL_ADS_JSON_LOC_DROPBOX, all_ads_json_loc)
            dropbox_fs.download(SENT_ADS_JSON_LOC_DROPBOX, sent_ads_json_loc)
        except Exception as ex:
            log.error(f'Could not download json files {SENT_ADS_JSON_LOC_DROPBOX}'
                      f' from dropbox')
            log.exception(ex)

    log.info(f'Running scraping with config: {config}')
    all_ads = open_json(all_ads_json_loc)
    # Addd key as an ID field to the dict
    for k, v in all_ads.items():
        v['Id'] = k
    if os.path.exists(sent_ads_json_loc):
        sent_ads = open_json(sent_ads_json_loc)
    else:
        log.debug(f"Sent_ads file {sent_ads_json_loc} does not exist, will create it")
        sent_ads = {}
    # Addd key as an ID field to the dict
    for k, v in sent_ads.items():
        v['Id'] = k
    # initiate Ad scraper

    scraper = AdScraper(all_ads=all_ads, sent_ads=sent_ads, dropbox_token=dropbox_token, telegram_token=telegram_token,
                        telegram_chat_id=telegram_chat_id, ignore_business_ads=ignore_business_ads)

    for k, ad in scraper.ads.items():
        is_sent = scraper.send_telegram_ad(ad)
        if is_sent:
            # If telegram message was sent , add to sent_ads
            scraper.sent_ads[ad['Id']] = ad
            scraper.save_ad_artefacts(ad=ad,
                                   ad_id=k,
                                   destination_folder='/Data/kijiji_ads',
                                   fs=scraper.dropbox_fs)
        else:
            log.info(f'Ad {ad["Id"]} was not sent, skipping for now')

    # Update sent ads:
    log.info(f'Updating sent ads with {len(scraper.ads)} ads')
    with open(sent_ads_json_loc, "w") as f:
        json.dump(scraper.sent_ads, f)
    log.info(f'Updating Dropbox sent ads file with {len(scraper.ads)} ads')
    scraper.dropbox_fs.put_file(sent_ads_json_loc, SENT_ADS_JSON_LOC_DROPBOX)
    log.info(f'Updating Dropbox all ads file')
    scraper.dropbox_fs.put_file(all_ads_json_loc, ALL_ADS_JSON_LOC_DROPBOX)
    log.info('Done!')


if __name__ == "__main__":
    app()
