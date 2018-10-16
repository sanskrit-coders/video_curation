import logging

from video_curation import youtube_client, video_repo

# Remove all handlers associated with the root logger object.
for handler in logging.root.handlers[:]:
    logging.root.removeHandler(handler)
logging.basicConfig(
    level=logging.DEBUG,
    format="%(levelname)s:%(asctime)s:%(module)s:%(lineno)d %(message)s")

def get_video_title(mandala_sukta_id):
    return "%s Rigveda Shakala Samhita Kerala Style ऋग्वेद-शकल-संहिता-केरल-शैल्या" % mandala_sukta_id

def get_playlist_title(mandala_id):
    return "%s Rigveda Shakala Samhita Kerala Style ऋग्वेद-शकल-संहिता-केरल-शैल्या" % mandala_id

description = "This was produced by an IGNCA project (http://vedicheritage.gov.in/), funded by the Indian taxpayer. This has been reproduced here for convenience. Also see https://archive.org/details/shAkhala-rig-veda-kerala ."

video_tags = ["RIGSSK", "Veda", "वेदाः"]

class RgvedaRepo(video_repo.VideoRepo):
    
    def get_mandala_videos_map(self, mandala_id):
        return dict(filter(lambda item: "RIGSS %02d" % (mandala_id) in item[0], self.title_to_path.items()))

    def upload_mandala_videos(self, mandala_id, yt_channel, dry_run=False):
        yt_mandala_videos = sorted(list(filter(lambda vid: "RIGSS %02d" % (mandala_id) in vid.title, yt_channel.uploaded_vids)))
        yt_mandala_video_titles = list(map(lambda video: video.title, yt_mandala_videos))
        logging.info("Got %d vids: %s ", len(yt_mandala_videos), yt_mandala_videos)
        local_mandala_videos_map = self.get_mandala_videos_map(mandala_id=mandala_id)
        missing_mandala_video_titles = sorted(set(local_mandala_videos_map.keys()) - set(yt_mandala_video_titles))
        logging.info("Missing videos: %s", missing_mandala_video_titles)
        for title in missing_mandala_video_titles:
            video = youtube_client.YtVideo(title=title, api_service=yt_channel.api_service, privacy='public', tags=video_tags)
            if dry_run:
                logging.info("Would have uploaded: %s", video)
            else:
                video.initialize_upload(filepath=local_mandala_videos_map[title])

    def upload_videos(self):
        for mandala_id in range(1, 11):
            self.upload_mandala_videos(mandala_id=mandala_id, yt_channel=channel, dry_run=False)


    def update_video_metadatas(self, yt_channel):
        yt_mandala_videos = sorted(list(filter(lambda vid: "RIGSS " in vid.title, yt_channel.uploaded_vids)))
        for video in yt_mandala_videos:
            video.title = get_video_title(video.title[:len("RIGSS 10 048")])
            video.description = description
            video.tags = video_tags
            video.category_id = 27
            video.sync_metadata_to_youtube()

    def update_video_privacy(self, yt_channel):
        yt_mandala_videos = sorted(list(filter(lambda vid: "RIGSS " in vid.title, yt_channel.uploaded_vids)))
        for video in yt_mandala_videos:
            video.privacy = 'public'
            video.set_youtube_privacy()

    def set_mandala_videos_in_playlist(self, mandala_id, yt_channel):
        mandala_id_str = "RIGSS %02d" % (mandala_id)
        yt_mandala_videos = sorted(list(filter(lambda vid: mandala_id_str in vid.title, yt_channel.uploaded_vids)))
        possible_playlists = list(filter(lambda plist: mandala_id_str in plist.title,  yt_channel.playlists))
        playlist = None
        if len(possible_playlists) > 0:
            playlist = possible_playlists[0]
            logging.info("Found playlist %s!", playlist)
        else:
            playlist = youtube_client.Playlist(title=get_playlist_title(mandala_id=mandala_id_str), description=description, tags=video_tags, api_service=yt_channel.api_service, privacy='public')
            playlist.add_to_youtube()

        for video in playlist.get_playlist_videos():
            playlist.delete_video(video.id)
        for video in yt_mandala_videos:
            playlist.add_video(video_id=video.id, position=yt_mandala_videos.index(video))

if __name__ == "__main__":
    local_repo = RgvedaRepo(repo_paths=["/home/vvasuki/Videos/Rgveda/"]) 
    # Passing service_account_file does not seem to work as intended.
    channel = youtube_client.Channel(token_file_path='/home/vvasuki/sysconf/kunchikA/google/kashcit/yt_access_token.json', client_secret_file='/home/vvasuki/sysconf/kunchikA/google/kashcit/native_client_id.json')
    logging.info("Retrieving uploaded videos.")
    channel.set_uploaded_videos()
    channel.set_playlists()
    # local_repo.update_video_metadatas(channel)
    # local_repo.update_video_privacy(channel)
    # for mandala_id in range(9, 11):
    #     local_repo.set_mandala_videos_in_playlist(mandala_id=mandala_id, yt_channel=channel)
    # logging.info(pprint.pformat(uploaded_vids))

    # archive_item = audio_curation.archive_utility.ArchiveItem(archive_id="shAkhala-rig-veda-kerala")
    # archive_item.update_archive_item(file_paths=glob.glob("/home/vvasuki/Videos/Rgveda/*"))

