import glob

import git
import itertools
import logging
import os

for handler in logging.root.handlers[:]:
    logging.root.removeHandler(handler)
logging.basicConfig(
    level=logging.DEBUG,
    format="%(levelname)s:%(asctime)s:%(module)s:%(lineno)d %(message)s"
)


class VideoRepo(object):
    """ An Video file repository.
    The local repository, by default, is assumed to be a collection of working directories (self.repo_paths) with two subfolders:
        - mp4: Containing mp4-s for every "episode" in the repository. 
    """

    def __init__(self, repo_paths, archive_item=None):
        self.repo_paths = repo_paths

        self.base_mp4_file_paths = [item for sublist in
                                    [sorted(glob.glob(os.path.join(repo_path, "*.mp4"))) for repo_path in
                                     repo_paths] for item in sublist]
        titles = [self.get_title_from_path(filepath=filepath) for filepath in self.base_mp4_file_paths]
        self.title_to_path = dict(zip(titles, self.base_mp4_file_paths))
        logging.info("Got %d files" % (len(self.base_mp4_file_paths)))
        self.archive_item = archive_item

    # noinspection PyMethodMayBeStatic
    def get_title_from_path(self, filepath):
        return os.path.basename(filepath).replace("_", " ")[:-4]