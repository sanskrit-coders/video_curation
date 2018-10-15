import glob
import logging


import pprint

import audio_curation.archive_utility
from video_curation import youtube_client

# Remove all handlers associated with the root logger object.
for handler in logging.root.handlers[:]:
    logging.root.removeHandler(handler)
logging.basicConfig(
    level=logging.DEBUG,
    format="%(levelname)s:%(asctime)s:%(module)s:%(lineno)d %(message)s")

def add_RIGSS_videos_to_playlist(mandala_id, vids):
    mandala_videos = sorted(list(filter(lambda vid: "RIGSS %02d" % (mandala_id) in vid.title, vids)))
    logging.info("Got %d vids: %s ", len(mandala_videos), mandala_videos)


archive_item = audio_curation.archive_utility.ArchiveItem(archive_id="shAkhala-rig-veda-kerala")


if __name__ == "__main__":
    # Passing service_account_file does not seem to work as intended.
    channel = youtube_client.Channel(token_file_path='/home/vvasuki/sysconf/kunchikA/google/kashcit/yt_access_token.json', client_secret_file='/home/vvasuki/sysconf/kunchikA/google/kashcit/native_client_id.json')
    logging.info("Retrieving uploaded videos.")
    uploaded_vids = channel.uploads_playlist.get_playlist_videos()
    for mandala_id in range(1, 11):
        add_RIGSS_videos_to_playlist(mandala_id=mandala_id, vids=uploaded_vids)
    logging.info(pprint.pformat(uploaded_vids))

    # archive_item.update_archive_item(file_paths=glob.glob("/home/vvasuki/Videos/Rgveda/*"))

