import json
import logging
import os
# google.oauth2 package is completely different from oauth2client
from google.oauth2 import service_account
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow


def perform_oauth(client_secrets_file, scopes, token_file_path=None):
    flow = InstalledAppFlow.from_client_secrets_file(client_secrets_file, scopes)
    credentials = flow.run_console()
    creds_data = {
        'access_token': credentials.token,
        'refresh_token': credentials.refresh_token,
        'token_uri': credentials.token_uri,
        'client_id': credentials.client_id,
        'client_secret': credentials.client_secret,
        'scopes': credentials.scopes,
    }
    if token_file_path is not None:
        with open(token_file_path, 'w') as outfile:
            json.dump(creds_data, outfile)
        # storage.put(credentials=credentials) fails with 'Credentials' object has no attribute 'to_json'. That's because google.oauth2 package is completely different from oauth2client


def get_service_from_token_file_path(token_file_path):
    credentials = None
    if os.path.exists(token_file_path):
        with open(token_file_path) as f:
            creds_data = json.load(f)
            credentials = Credentials('access_token',
                                      refresh_token=creds_data['refresh_token'],
                                      token_uri=creds_data['token_uri'],
                                      client_id=creds_data['client_id'],
                                      client_secret=creds_data['client_secret'])
    if credentials is None:
        logging.warning("could not retrieve oauth credentials from '%r'", token_file_path)
    return credentials 


def get_credentials(service_account_file=None, token_file_path=None, client_secrets_file=None, scopes=None):
    credentials = None
    if service_account_file is not None and os.path.exists(service_account_file):
        unscoped_credentials = service_account.Credentials.from_service_account_file(service_account_file)
        credentials = unscoped_credentials.with_scopes(scopes)
    else:
        # Access Token file is the result of oauth. If it exists, we might avoid having to do another oauth. 
        if token_file_path is not None:
            credentials = get_service_from_token_file_path(token_file_path)
        if credentials is None:
            assert client_secrets_file is not None and scopes is not None 
            if perform_oauth(scopes=scopes, token_file_path=token_file_path, client_secrets_file=client_secrets_file):
                credentials = get_service_from_token_file_path(token_file_path)
                logging.info("Logged in successfully with oauth.")
            else:
                logging.error("Login failure!")
    return credentials

