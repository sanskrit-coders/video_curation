"""A wrapper around Youtube API."""
import itertools
import logging

import http.client as httplib
import random

import httplib2
import more_itertools
import time

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload

from curation_utils.google import api_helper
from curation_utils.google.api_helper import get_api_request_dict

ok_upload_status = ['uploaded', 'processed']


class YtVideo(object):
    """Represents a YouTube video."""
    def __init__(self, id=None, title=None, description=None, tags=None, category_id=1, api_service=None, privacy='public', upload_status='uploaded'):
        self.upload_status = upload_status
        self.category_id = category_id
        self.id = id
        self.title = title
        self.description = description
        self.tags = tags
        self.privacy = privacy
        self.api_service = api_service

    def set_from_yt_metadata(self, yt_metadata):
        """Create and return a YTVideo object"""
        self.id = yt_metadata["id"]
        self.title = yt_metadata['snippet']['title']
        self.description = yt_metadata['snippet'].get('description', None)
        self.tags = yt_metadata['snippet'].get('tags', None)
        self.category_id = yt_metadata['snippet'].get('categoryId', 1)
        if 'status' in yt_metadata:
            self.privacy = yt_metadata['status'].get('privacyStatus', 'public')
            self.upload_status = yt_metadata['status'].get('uploadStatus', 'uploaded')
            if self.upload_status not in ok_upload_status:
                logging.warning("Got a strange video %s", yt_metadata)

    @classmethod
    def from_id(cls, id, api_service):
        self= YtVideo(id=id, api_service=api_service)
        self.sync_from_youtube()
        return self

    @classmethod
    def from_yt_metadata(cls, yt_metadata, api_service):
        self = YtVideo(api_service=api_service)
        self.set_from_yt_metadata(yt_metadata=yt_metadata)
        return self

    def __repr__(self):
        return "id:%s title:%s" % (self.id, self.title)

    def __lt__(self, other):
        """Compare two YtVideo objects"""
        return self.title < other.title

    def initialize_upload(self, filepath):
        """
        Upload a new video to YouTube!
        
        :param filepath: 
        :return: 
        """
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

        logging.info("Uploading %s", self)
        self.id = _resumable_upload(insert_request)
        logging.info("Uploaded %s", self)

    def sync_metadata_to_youtube(self):
        """Set title etc in YouTube.
        
        :return: 
        """
        properties = {'id': self.id,
                      'snippet.title': self.title,
                      'snippet.description': self.description,
                      'snippet.tags[]': self.tags,
                      'snippet.categoryId': self.category_id
                      }
        resource = get_api_request_dict(properties)
        response = self.api_service.videos().update(
            body=resource,
            part='snippet'
        ).execute()
        logging.info(response)

    def set_youtube_privacy(self):
        """Update YouTube privacy setting for this video."""
        properties = {'id': self.id,
                      'status.privacyStatus': self.privacy,
                      }
        resource = get_api_request_dict(properties)
        response = self.api_service.videos().update(
            body=resource,
            part='status'
        ).execute()
        logging.info(response)

    def sync_from_youtube(self, part='snippet,status'):
        response = self.api_service.videos().list(
            part=part,
            id=self.id
        ).execute()
        self.set_from_yt_metadata(yt_metadata=response["items"][0])

    def delete(self):
        response = self.api_service.videos().list(
            id=id
        ).execute()
        logging.info(response)


class PlaylistItem(object):
    def __init__(self, api_service, video_id, playlist_id, title=None, item_id=None, position=0):
        self.api_service = api_service
        self.video_id = video_id
        self.item_id = item_id
        self.position = position
        self.title = title
        self.playlist_id = playlist_id

    def __repr__(self):
        return "video_id:%s position:%s" % (self.video_id, self.position)

    def to_video(self):
        metadata = self.to_metadata()
        id = metadata["id"]
        title = metadata['snippet']['title']
        description = metadata['snippet'].get('description', None)
        tags = metadata['snippet'].get('tags', None)
        category_id = metadata['snippet'].get('categoryId', 1)
        privacy = metadata.get('status', {'privacyStatus': 'public'}).get('privacyStatus', 'public')
        return YtVideo(id=id, title=title, description=description, tags=tags, category_id=category_id, api_service=self.api_service, privacy=privacy)

    @classmethod
    def from_metadata(cls, metadata, api_service):
        video_id = metadata['snippet']['resourceId']['videoId']
        item_id = metadata['id']
        if 'position' not in metadata['snippet']:
            logging.error(metadata)
        # metadata['snippet']['position']
        position = metadata['snippet']['position']
        playlist_id = metadata['snippet']['playlistId']
        title = metadata['snippet']['title']
        self = PlaylistItem(video_id=video_id, playlist_id=playlist_id, item_id=item_id, position=position, title=title, api_service=api_service)
        return self

    def to_metadata(self):
        return {'id': self.item_id,
                'snippet.playlistId': self.playlist_id,
                'snippet.resourceId.kind': 'youtube#video',
                'snippet.resourceId.videoId': self.video_id,
                'snippet.position': self.position}


class Playlist(object):
    """
    Represents a YouTube playlist.
    """
    def __init__(self, api_service, title, id=None, description="", tags=None, privacy='public'):
        if tags is None:
            tags = []
        self.id = id
        self.title = title
        self.description = description
        self.tags = tags.copy()
        self.privacy = privacy
        self.api_service = api_service
        self.items = []
        if id is not None:
            self.sync_items_from_youtube()

    def __repr__(self):
        return "id:%s title:%s" % (self.id, self.title)

    def __lt__(self, other):
        return self.title < other.title

    def _sync_positions_yt(self):
        for index, item in enumerate(self.items):
            if item.position != index:
                item.position = index
                resource = get_api_request_dict(item.to_metadata())
                response = self.api_service.playlistItems().insert(
                    body=resource,
                    part='snippet'
                ).execute()
                logging.info(response)

    def deduplicate(self, key=lambda item:item.video_id):
        sorted_items = sorted(self.items, key=key)
        for key, items_iterator in itertools.groupby(sorted_items, key=key):
            items = list(items_iterator)
            if len(items) > 0:
                logging.info("Found duplicates for key %s : %s", key, items)
                for item in items[1:]:
                    self.delete_item(item)

    def sort(self, key=lambda item: item.title):
        self.items.sort(key=key)
        self._sync_positions_yt()

    # https://developers.google.com/youtube/v3/docs/playlistItems#resource
    def add_video_yt(self, video_id, position=0):
        """Insert a video into this playlist. Update YouTube as well."""
        properties = {'snippet.playlistId': self.id,
                      'snippet.resourceId.kind': 'youtube#video',
                      'snippet.resourceId.videoId': video_id,
                      'snippet.position': position}
        resource = get_api_request_dict(properties)
        response = self.api_service.playlistItems().insert(
            body=resource,
            part='snippet'
        ).execute()
        logging.info(response)
        response['snippet']['position'] = position
        item = PlaylistItem.from_metadata(response, api_service=self.api_service)
        self.items.insert(position, item)
        return item

    def add_videos(self, video_ids):
        """Add multiple videos to this playlist. Update YouTube as well."""
        [self.add_video_yt(video_id=video_id, position=position) for position, video_id in enumerate(video_ids)]
        
    def set_videos(self, video_ids):
        if self.get_video_ids() != video_ids:
            self.clear_items()
            self.add_videos(video_ids=video_ids)

    def delete_item(self, item):
        response = self.api_service.playlistItems().delete(id=item.item_id).execute()
        logging.info(response)
        position = self.items.index(item)
        self.items.remove(item)
        for index, item in enumerate(self.items[position:]):
            item.position = index

    # https://developers.google.com/youtube/v3/docs/playlistItems#resource
    def delete_video(self, video_id):
        """Delete some video from this playlist. Update YouTube as well."""
        items_to_delete = list(filter(lambda item: item.video_id == video_id, self.items))
        for item in items_to_delete:
            self.delete_item(item)

    def sync_items_from_youtube(self):
        """
        
        """
        playlistitems_list_request = self.api_service.playlistItems().list(
            playlistId=self.id,
            part='snippet',
            maxResults=50
        )
        item_metadatas = []
        while playlistitems_list_request:
            playlistitems_list_response = playlistitems_list_request.execute()
            item_metadatas.extend(playlistitems_list_response['items'])
            playlistitems_list_request = self.api_service.playlistItems().list_next(
                playlistitems_list_request, playlistitems_list_response)

        item_metadatas.sort(key=lambda item: item['snippet']['position'])
        self.items = [PlaylistItem.from_metadata(metadata=metadata, api_service=self.api_service) for metadata in item_metadatas]

    def clear_items(self):
        logging.info("Clearing %d items: %s", len(self.items), self.items)
        for item in self.items.copy():
            self.delete_item(item=item)

    def sync_metadata_to_youtube(self):
        """Set metadata info in YouTube."""
        properties = {'id': self.id,
                      'snippet.title': self.title,
                      'snippet.description': self.description,
                      'snippet.tags[]': self.tags
                      }
        resource = get_api_request_dict(properties)
        response = self.api_service.playlists().update(
            body=resource,
            part='snippet'
        ).execute()
        logging.info(response)

    def add_to_youtube(self):
        """Add a new playlist at YouTube."""
        body = dict(
            snippet=dict(
                title=self.title,
                description=self.description,
                tags=self.tags
            ),
            status=dict(
                privacyStatus=self.privacy
            )
        )

        playlists_insert_response = self.api_service.playlists().insert(
            part='snippet,status',
            body=body
        ).execute()
        self.id = playlists_insert_response['id']
        logging.info('New playlist ID: %s' % self.id)

    def get_videos(self, part="snippet,status"):
        videos = []
        if part=="snippet":
            videos = [item.get_video() for item in self.items]
        else:
            video_ids = self.get_video_ids()
            id_chunks = more_itertools.chunked(video_ids, 50)
            for id_chunk in id_chunks:
                response = self.api_service.videos().list(
                    part=part,
                    id=",".join(id_chunk)
                ).execute()
                videos.extend([YtVideo.from_yt_metadata(yt_metadata=yt_metadata, api_service=self.api_service) for yt_metadata in response["items"]])
        return videos

    def get_non_uploaded_private(self):
        return [video for video in self.get_videos() if video.privacy == 'private' or video.upload_status not in ok_upload_status]

    def get_uploaded(self):
        return [video for video in self.get_videos() if video.upload_status in ok_upload_status]

    @classmethod
    def from_metadata(cls, yt_metadata, api_service=None):
        """Construct a :py:class:Playlist object from YouTube metadata."""
        id = yt_metadata['id']
        title = yt_metadata['snippet']['title']
        description = yt_metadata['snippet'].get('description', None)
        tags = yt_metadata['snippet'].get('tags', None)
        category_id = yt_metadata['snippet'].get('categoryId', 1)
        api_service = api_service
        privacy = 'public'
        if 'status' in yt_metadata:
            privacy = yt_metadata['status'].get('privacy', "public")
        self = Playlist(id=id, title=title, description=description, tags=tags, privacy=privacy, api_service=api_service)
        self.yt_metadata = yt_metadata
        return self

    def get_video_ids(self):
        return set([item.video_id for item in self.items])


class Channel(object):
    """Represents a YouTube channel.
    
    """
    def __init__(self, service_account_file=None, token_file_path=None, client_secret_file=None):
        """
        
        Note: Passing service_account_file does not seem to work as intended.
        :param service_account_file:      
        :param token_file_path: 
        :param client_secret_file: 
        """
        self._set_authenticated_service(service_account_file=service_account_file, token_file_path=token_file_path, client_secret_file=client_secret_file)
        self.uploads_playlist = self.get_uploads_playlist()
        self.uploaded_vids = None
        self.playlists = []

    def set_uploaded_videos(self):
        """Set self.uploaded_vids."""
        self.uploaded_vids = self.uploads_playlist.get_uploaded()

    def delete_rejected_videos(self, dry_run=True):
        for video in self.uploads_playlist.get_videos():
            if video.upload_status == "rejected":
                logging.info("Deleting %s", video)
                if not dry_run:
                    video.delete()
        self.set_uploaded_videos()

    def _set_authenticated_service(self, service_account_file=None, token_file_path=None, client_secret_file=None):
        """ Set self.api_service, via which all communication with YouTube happens.
        
        Note: Passing service_account_file does not seem to work as intended.
        :param service_account_file:      
        :param token_file_path: 
        :param client_secret_file: 
        """
        scopes = ['https://www.googleapis.com/auth/youtube']
        api_service_name = 'youtube'
        api_version = 'v3'
        credentials = api_helper.get_credentials(service_account_file=service_account_file, token_file_path=token_file_path, client_secrets_file=client_secret_file, scopes=scopes)
        self.api_service = build(serviceName=api_service_name, version=api_version, credentials=credentials)
        logging.info("Done authenticating.")

    def set_playlists(self):
        """Set self.playlists."""
        request = self.api_service.playlists().list(mine=True,
                                          part='snippet, status',
                                          maxResults=50
                                          )
        self.playlists = []
        while request:
            response = request.execute()

            # Print information about each video.
            self.playlists.extend([
                Playlist.from_metadata(yt_metadata=playlist, api_service=self.api_service)
                for playlist in response['items']
            ])

            request = self.api_service.playlists().list_next(
                request, response)
        

    def get_uploads_playlist(self):
        """Get the uploads playlist for this channel."""

        # Retrieve the contentDetails part of the channel resource for the
        # authenticated user's channel.
        channels_response = self.api_service.channels().list(
            mine=True,
            part='contentDetails'
        ).execute()
    
        for channel in channels_response['items']:
            # From the API response, extract the playlist ID that identifies the list
            # of videos uploaded to the authenticated user's channel.
            return Playlist(id=channel['contentDetails']['relatedPlaylists']['uploads'], api_service=self.api_service, title="Uploads", description="", tags=[])
        return None


def _resumable_upload(insert_request):
    """ This method implements an exponential backoff strategy to resume a failed upload. Called from :py:class:YtVideo.
    
    :param insert_request: 
    :return: 
    """
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
