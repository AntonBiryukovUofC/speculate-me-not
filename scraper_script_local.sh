#!/usr/bin/zsh
export PATH=/usr/local/bin
python src/kijiji_scraper/main.py --conf scraper_config.yaml --skipmail --ads config_ads.json
python src/main.py --all-ads-json-loc config_ads.json --sent-ads-json-loc sent_ads.json --sync-dropbox-locations --ignore-business-ads
