import json
import os.path

import yaml
import requests_cache
from loguru import logger as log
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


@app.command()
def main(
        config: str = typer.Option("", callback=conf_callback, is_eager=True),
        dropbox_token: str = typer.Option("", envvar="DROPBOX_ACCESS_TOKEN"),
        telegram_token: str = typer.Option("", envvar="TELEGRAM_TOKEN"),
        telegram_chat_id: str = typer.Option("", envvar="TELEGRAM_CHAT_ID"),
        all_ads_json_loc: str = typer.Option("/home/anton/.kijiji_scraper/config_ads.json"),
        sent_ads_json_loc: str = typer.Option("/home/anton/.kijiji_scraper/sent_ads.json"),
        sync_dropbox_locations: bool = typer.Option(True,flag_value=True)):

    dropbox_fs = DropboxDriveFS(token=dropbox_token,
                                app_key=os.environ['APP_KEY'],
                                refresh_token=os.environ['REFRESH_TOKEN'],
                                app_secret=os.environ['APP_SECRET'])
    if sync_dropbox_locations:
        # We need to download the json files from dropbox and save into json_loc:
        log.info(f'Syncing dropbox locations with local passed locations {sent_ads_json_loc}')
        try:
            #dropbox_fs.download(ALL_ADS_JSON_LOC_DROPBOX, all_ads_json_loc)
            dropbox_fs.download(SENT_ADS_JSON_LOC_DROPBOX, sent_ads_json_loc)
        except Exception as ex:
            log.error(f'Could not download json files {SENT_ADS_JSON_LOC_DROPBOX}'
                      f' from dropbox')
            log.exception(ex)


    log.info(f'Running scraping with config: {config}')
    with open(all_ads_json_loc, "r") as f:
        all_ads = json.load(f)
    # Addd key as an ID field to the dict
    for k, v in all_ads.items():
        v['Id'] = k
    if os.path.exists(sent_ads_json_loc):
        with open(sent_ads_json_loc, "r") as f:
            sent_ads = json.load(f)
    else:
        log.debug(f"Sent_ads file {sent_ads_json_loc} does not exist, will create it")
        sent_ads = {}
    # Addd key as an ID field to the dict
    for k, v in sent_ads.items():
        v['Id'] = k
    # initiate Ad scraper

    scraper = AdScraper(all_ads=all_ads, sent_ads=sent_ads, dropbox_token=dropbox_token, telegram_token=telegram_token,
                        telegram_chat_id=telegram_chat_id)

    for k, ad in scraper.ads.items():
        scraper.send_telegram_ad(ad)
        scraper.save_ad_artefacts(ad=ad,
                                  ad_id=k,
                                  destination_folder='/Data/kijiji_ads',
                                  fs=scraper.dropbox_fs)

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
