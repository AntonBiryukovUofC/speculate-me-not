from pydrive2.auth import GoogleAuth
from pydrive2.drive import GoogleDrive

def login_with_service_account():
    """
    Google Drive service with a service account.
    note: for the service account to work, you need to share the folder or
    files with the service account email.

    :return: google auth
    """
    # Define the settings dict to use a service account
    # We also can use all options available for the settings dict like
    # oauth_scope,save_credentials,etc.
    settings = {
                "client_config_backend": "service",
                "service_config": {
                    "client_json_file_path": "/home/anton/gspread-parse-e366a755d61a.json",
                }
            }
    # Create instance of GoogleAuth
    gauth = GoogleAuth(settings=settings)
    # Authenticate
    gauth.ServiceAuth()
    return gauth

gauth = login_with_service_account()
drive = GoogleDrive(gauth)
file_list = drive.ListFile({'q': "'root' in parents and trashed=false"}).GetList()
for file1 in file_list:
  print('title: %s, id: %s' % (file1['title'], file1['id']))
from pydrive2.fs import GDriveFileSystem

fs = GDriveFileSystem(
    "root",
    use_service_account=True,
    client_json_file_path="/home/anton/gspread-parse-e366a755d61a.json",
)