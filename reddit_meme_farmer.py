import logging
import os
import re
import sys
from typing import Union
from urllib.parse import urlparse
from urllib.request import urlretrieve

import praw

import config


class RedditMemeFarmer:
    def __init__(self, folder="memes", subreddit="cryptocurrencymemes"):
        logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                            stream=sys.stdout, level=logging.INFO)
        self.logger = logging.getLogger(__name__)

        self.rbot = praw.Reddit(client_id=config.REDDIT_CLIENT_ID,
                                client_secret=config.REDDIT_SECRET,
                                user_agent=config.REDDIT_USER_AGENT)
        self.meme_folderpath = self.create_data_directory(folder)
        self.logger.info(f"Memes saved to {self.meme_folderpath}")
        self.meme_subreddit = subreddit
        self.submission_titles = []
        self.limit = 10

    @staticmethod
    def create_data_directory(folder) -> str:
        data_dir = os.path.join(os.getcwd(), folder)
        if not os.path.exists(data_dir):
            os.makedirs(data_dir)

        return data_dir

    @staticmethod
    def parse_filename_from_url(url: str) -> str:
        filename = url.split("/")

        if len(filename) == 0:
            filename = re.findall("/(.*?)", url)

        filename = filename[-1]

        if "." not in filename:
            filename += ".jpg"
        return filename

    def get_crypto_meme_path(self) -> Union[str, bool]:
        try:
            for submission in self.rbot.subreddit(self.meme_subreddit).hot(limit=self.limit):
                if submission.is_self:
                    # Filter out text posts
                    continue
                elif submission.is_video:
                    url = submission.media['reddit_video']['fallback_url'].split("?")[0]
                else:
                    url = submission.url

                # Use post title as filename and retain file extension
                name = submission.title.rstrip().strip("/")
                ext = os.path.splitext(urlparse(url).path)[1]
                filepath = os.path.join(self.meme_folderpath, name + ext)

                current_memes = [meme for meme in os.listdir(self.meme_folderpath) if
                                 os.path.isfile(os.path.join(self.meme_folderpath, meme))]

                if name + ext in current_memes:
                    continue

                urlretrieve(url, filepath)
                self.logger.info(f"Downloaded {url} from r/{self.meme_subreddit} and saved to {filepath}")
                return filepath
        except Exception as exc:
            self.logger.warning(f"Failed to download. {exc}")
            return False
        else:
            self.limit += 5
            self.logger.warning(f"No unique memes found, increasing limit to {self.limit}")
            return self.get_crypto_meme_path()

