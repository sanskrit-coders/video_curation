"""Functions to help deal with google_api."""
import json
import logging
import os
# google.oauth2 package is completely different from oauth2client
from google.oauth2 import service_account
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow


def perform_oauth(client_secrets_file, scopes, token_file_path=None):
    """Do interactive oauth."""
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
    """Authenticate and get api service object.
    
    :param token_file_path: A json file containing an access token (from a prior successful oauth). 
    :return: 
    """
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
    """
    
    Note: Passing service_account_file does not seem to work as intended.
    :param service_account_file: 
    :param token_file_path:  A json file containing an access token (from a prior successful oauth).
    :param client_secrets_file: 
    :param scopes: 
    :return: 
    """
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


def get_api_request_dict(properties):
    """Build a resource based on a list of properties given as key-value pairs. Leave properties with empty values out of the inserted resource.
    
    :param properties: a dict
    :return: 
    """
    resource = {}
    for p in properties:
        # Given a key like "snippet.title", split into "snippet" and "title", where
        # "snippet" will be an object and "title" will be a property in that object.
        prop_array = p.split('.')
        ref = resource
        for pa in range(0, len(prop_array)):
            is_array = False
            key = prop_array[pa]

            # For properties that have array values, convert a name like
            # "snippet.tags[]" to snippet.tags, and set a flag to handle
            # the value as an array.
            if key[-2:] == '[]':
                key = key[0:len(key)-2:]
                is_array = True

            if pa == (len(prop_array) - 1):
                # Leave properties without values out of inserted resource.
                if properties[p]:
                    if is_array:
                        if isinstance(properties[p], str):
                            ref[key] = properties[p].split(',')
                        else:
                            ref[key] = properties[p]
                    else:
                        ref[key] = properties[p]
            elif key not in ref:
                # For example, the property is "snippet.title", but the resource does
                # not yet have a "snippet" object. Create the snippet object here.
                # Setting "ref = ref[key]" means that in the next time through the
                # "for pa in range ..." loop, we will be setting a property in the
                # resource's "snippet" object.
                ref[key] = {}
                ref = ref[key]
            else:
                # For example, the property is "snippet.description", and the resource
                # already has a "snippet" object.
                ref = ref[key]
    return resource