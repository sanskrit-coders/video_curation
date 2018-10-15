import logging


import pprint

from video_curation import youtube_client

# Remove all handlers associated with the root logger object.
for handler in logging.root.handlers[:]:
    logging.root.removeHandler(handler)
logging.basicConfig(
    level=logging.DEBUG,
    format="%(levelname)s:%(asctime)s:%(module)s:%(lineno)d %(message)s")

if __name__ == "__main__":
    channel = youtube_client.Channel(token_file_path='/home/vvasuki/sysconf/kunchikA/google/kashcit/yt_access_token.json', client_secret_file='/home/vvasuki/sysconf/kunchikA/google/kashcit/native_client_id.json')
    logging.info("Retrieving uploaded videos.")
    uploaded_vids = channel.uploads_playlist.get_playlist_videos()
    logging.info(pprint.pformat(uploaded_vids))