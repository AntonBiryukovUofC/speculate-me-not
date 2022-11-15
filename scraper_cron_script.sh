export PATH=/usr/local/bin
python /opt/app/src/kijiji_scraper/main.py --conf /opt/app/scraper_config.yaml --skipmail --ads /opt/app/config_ads.json
python /opt/app/src/main.py --all-ads-json-loc /opt/app/config_ads.json --sent-ads-json-loc /opt/app/sent_ads.json --sync-dropbox-locations --ignore-business-ads
