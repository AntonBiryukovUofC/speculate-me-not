import os

import dropboxdrivefs as dbx
from dotenv import find_dotenv, load_dotenv

load_dotenv(find_dotenv())
token = os.environ['DROPBOX_ACCESS_TOKEN']
fs = dbx.DropboxDriveFileSystem(token=token)
fs.mkdir("/Data/test_box")
fs.put_file("test_dropbox.py", "/Data/test_box/text1.txt")
