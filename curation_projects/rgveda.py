import glob
import logging
import os

import pprint

import audio_curation.archive_utility
from video_curation import youtube_client, video_repo

# Remove all handlers associated with the root logger object.
for handler in logging.root.handlers[:]:
    logging.root.removeHandler(handler)
logging.basicConfig(
    level=logging.DEBUG,
    format="%(levelname)s:%(asctime)s:%(module)s:%(lineno)d %(message)s")

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
            video = youtube_client.YtVideo(title=title, api_service=yt_channel.api_service, privacy='public')
            if dry_run:
                logging.info("Would have uploaded: %s", video)
            else:
                video.initialize_upload(filepath=local_mandala_videos_map[title])
    
    def add_videos_to_playlist(mandala_id, uploaded_vids):
        pass

if __name__ == "__main__":
    local_repo = RgvedaRepo(repo_paths=["/home/vvasuki/Videos/Rgveda/"]) 
    # Passing service_account_file does not seem to work as intended.
    channel = youtube_client.Channel(token_file_path='/home/vvasuki/sysconf/kunchikA/google/kashcit/yt_access_token.json', client_secret_file='/home/vvasuki/sysconf/kunchikA/google/kashcit/native_client_id.json')
    logging.info("Retrieving uploaded videos.")
    channel.set_uploaded_videos()
    for mandala_id in range(1, 11):
        # local_repo.add_videos_to_playlist(mandala_id=mandala_id, vids=channel.uploaded_vids)
        local_repo.upload_mandala_videos(mandala_id=mandala_id, yt_channel=channel, dry_run=False)
    # logging.info(pprint.pformat(uploaded_vids))

    # archive_item = audio_curation.archive_utility.ArchiveItem(archive_id="shAkhala-rig-veda-kerala")
    # archive_item.update_archive_item(file_paths=glob.glob("/home/vvasuki/Videos/Rgveda/*"))

