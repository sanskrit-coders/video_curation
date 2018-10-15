import logging

from googleapiclient.discovery import build

from video_curation import google_api_helper


class YtVideo(object):
    def __init__(self, _id, title):
        self._id = id
        self.title = title
        
    def __repr__(self):
        return "id:%s title:%s" % (self._id, self.title)


class Playlist(object):
    def __init__(self, api_service, playlist_id):
        self._id = playlist_id
        self.api_service = api_service

        # https://developers.google.com/youtube/v3/docs/playlistItems#resource
    def add_video(self, video_id, position=0):
        properties = {'snippet.playlistId': self._id,
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
            playlistId=self._id,
            part='snippet',
            maxResults=5
        )

        playlist_items = []
        while playlistitems_list_request:
            playlistitems_list_response = playlistitems_list_request.execute()

            # Print information about each video.
            playlist_items.append([
                YtVideo(title = playlist_item['snippet']['title'], _id = playlist_item['snippet']['resourceId']['videoId'])
                for playlist_item in playlistitems_list_response['items']
            ])

            playlistitems_list_request = self.api_service.playlistItems().list_next(
                playlistitems_list_request, playlistitems_list_response)
        return playlist_items

class Channel(object):
    def __init__(self, token_file_path, client_secret_file=None):
        self.set_authenticated_service(token_file_path=token_file_path, client_secret_file=client_secret_file)
        self.uploads_playlist = self.get_uploads_playlist()

    def set_authenticated_service(self, token_file_path, client_secret_file=None):
        scopes = ['https://www.googleapis.com/auth/youtube']
        api_service_name = 'youtube'
        api_version = 'v3'
        credentials = google_api_helper.get_credentials(token_file_path=token_file_path, client_secrets_file=client_secret_file, scopes=scopes)
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

