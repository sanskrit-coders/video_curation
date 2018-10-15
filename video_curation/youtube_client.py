import logging

import http.client as httplib
import random

import httplib2
import time

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload

from video_curation import google_api_helper


class YtVideo(object):
    def __init__(self, id=None, title=None, description=None, tags=None, api_service=None, privacy='public'):
        self.id = id
        self.title = title
        self.description = description
        self.tags = tags
        self.privacy = privacy
        self.api_service = api_service

    @classmethod
    def from_metadata(cls, yt_metadata, api_service=None):
        id = yt_metadata['snippet']['resourceId']['videoId']
        title = yt_metadata['snippet']['title']
        description = yt_metadata['snippet'].get('description', None)
        tags = yt_metadata['snippet'].get('tags', None)
        api_service = api_service
        self = YtVideo(id=id, title=title, description=description, tags=tags, api_service=api_service)
        self.yt_metadata = yt_metadata
        return self

    def initialize_upload(self, filepath):
        body=dict(
            snippet=dict(
                title=self.title,
                description=self.description,
                tags=self.tags
            ),
            status=dict(
                privacyStatus=self.privacy
            )
        )
    
        # Call the API's videos.insert method to create and upload the video.
        insert_request = self.api_service.videos().insert(
            part=",".join(body.keys()),
            body=body,
            # The chunksize parameter specifies the size of each chunk of data, in
            # bytes, that will be uploaded at a time. Set a higher value for
            # reliable connections as fewer chunks lead to faster uploads. Set a lower
            # value for better recovery on less reliable connections.
            #
            # Setting "chunksize" equal to -1 in the code below means that the entire
            # file will be uploaded in a single HTTP request. (If the upload fails,
            # it will still be retried where it left off.) This is usually a best
            # practice, but if you're using Python older than 2.6 or if you're
            # running on App Engine, you should set the chunksize to something like
            # 1024 * 1024 (1 megabyte).
            media_body=MediaFileUpload(filepath, chunksize=-1, resumable=True)
        )
    
        self.id = resumable_upload(insert_request)
    
    def __repr__(self):
        return "id:%s title:%s" % (self.id, self.title)

    def __lt__(self, other):
        return self.title < other.title


class Playlist(object):
    def __init__(self, api_service, playlist_id):
        self.id = playlist_id
        self.api_service = api_service

        # https://developers.google.com/youtube/v3/docs/playlistItems#resource
    def add_video(self, video_id, position=0):
        properties = {'snippet.playlistId': self.id,
                      'snippet.resourceId.kind': 'youtube#video',
                      'snippet.resourceId.videoId': video_id,
                      'snippet.position': position}
        resource = build_resource(properties)
        response = self.api_service.playlistItems().insert(
            body=resource
        ).execute()
        logging.info(response)

    def add_videos(self, video_ids):
        [self.add_video(video_id=video_id, position=position) for position, video_id in video_ids]

    def get_playlist_videos(self):
        # Retrieve the list of videos uploaded to the authenticated user's channel.
        playlistitems_list_request = self.api_service.playlistItems().list(
            playlistId=self.id,
            part='snippet',
            maxResults=5
        )

        playlist_items = []
        while playlistitems_list_request:
            playlistitems_list_response = playlistitems_list_request.execute()

            # Print information about each video.
            playlist_items.extend([
                YtVideo.from_metadata(yt_metadata=playlist_item)
                for playlist_item in playlistitems_list_response['items']
            ])

            playlistitems_list_request = self.api_service.playlistItems().list_next(
                playlistitems_list_request, playlistitems_list_response)
        return playlist_items


class Channel(object):
    def __init__(self, service_account_file=None, token_file_path=None, client_secret_file=None):
        """
        
        Note: Passing service_account_file does not seem to work as intended.
        :param service_account_file:      
        :param token_file_path: 
        :param client_secret_file: 
        """
        self.set_authenticated_service(service_account_file=service_account_file, token_file_path=token_file_path, client_secret_file=client_secret_file)
        self.uploads_playlist = self.get_uploads_playlist()
        self.uploaded_vids = None

    def set_uploaded_videos(self):
        self.uploaded_vids = self.uploads_playlist.get_playlist_videos()

    def set_authenticated_service(self, service_account_file=None, token_file_path=None, client_secret_file=None):
        """
        
        Note: Passing service_account_file does not seem to work as intended.
        :param service_account_file:      
        :param token_file_path: 
        :param client_secret_file: 
        """
        scopes = ['https://www.googleapis.com/auth/youtube']
        api_service_name = 'youtube'
        api_version = 'v3'
        credentials = google_api_helper.get_credentials(service_account_file=service_account_file, token_file_path=token_file_path, client_secrets_file=client_secret_file, scopes=scopes)
        self.api_service = build(serviceName=api_service_name, version=api_version, credentials=credentials)
        logging.info("Done authenticating.")

    def add_playlist(self, title, description="", privacy = "public"):
        body = dict(
            snippet=dict(
                title=title,
                description=description
            ),
            status=dict(
                privacyStatus=privacy
            )
        )
    
        playlists_insert_response = self.api_service.playlists().insert(
            part='snippet,status',
            body=body
        ).execute()
        playlist_id = playlists_insert_response['id']
        logging.info('New playlist ID: %s' % playlist_id)
        return Playlist(playlist_id=playlist_id, api_service=self.api_service)

    def get_uploads_playlist(self):
        # Retrieve the contentDetails part of the channel resource for the
        # authenticated user's channel.
        channels_response = self.api_service.channels().list(
            mine=True,
            part='contentDetails'
        ).execute()
    
        for channel in channels_response['items']:
            # From the API response, extract the playlist ID that identifies the list
            # of videos uploaded to the authenticated user's channel.
            return Playlist(playlist_id=channel['contentDetails']['relatedPlaylists']['uploads'], api_service=self.api_service)
        return None


# Build a resource based on a list of properties given as key-value pairs.
# Leave properties with empty values out of the inserted resource.
def build_resource(properties):
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
                        ref[key] = properties[p].split(',')
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

# This method implements an exponential backoff strategy to resume a
# failed upload.
def resumable_upload(insert_request):
    # Explicitly tell the underlying HTTP transport library not to retry, since
    # we are handling retry logic ourselves.
    httplib2.RETRIES = 1
    
    # Maximum number of times to retry before giving up.
    MAX_RETRIES = 10
    
    # Always retry when these exceptions are raised.
    RETRIABLE_EXCEPTIONS = (httplib2.HttpLib2Error, IOError, httplib.NotConnected,
                            httplib.IncompleteRead, httplib.ImproperConnectionState,
                            httplib.CannotSendRequest, httplib.CannotSendHeader,
                            httplib.ResponseNotReady, httplib.BadStatusLine)

    # Always retry when an apiclient.errors.HttpError with one of these status
    # codes is raised.
    RETRIABLE_STATUS_CODES = [500, 502, 503, 504]
    response = None
    error = None
    retry = 0
    while response is None:
        try:
            logging.info("Uploading file...")
            status, response = insert_request.next_chunk()
            if 'id' in response:
                logging.info("Video id '%s' was successfully uploaded." % response['id'])
                return response['id']
            else:
                exit("The upload failed with an unexpected response: %s" % response)
        except HttpError as e:
            if e.resp.status in RETRIABLE_STATUS_CODES:
                error = "A retriable HTTP error %d occurred:\n%s" % (e.resp.status,
                                                                     e.content)
            else:
                raise
        except RETRIABLE_EXCEPTIONS as e:
            error = "A retriable error occurred: %s" % e

        if error is not None:
            logging.error(error)
            retry += 1
            if retry > MAX_RETRIES:
                exit("No longer attempting to retry.")

            max_sleep = 2 ** retry
            sleep_seconds = random.random() * max_sleep
            logging.info("Sleeping %f seconds and then retrying..." % sleep_seconds)
            time.sleep(sleep_seconds)
