import logging
import os
import re
import sys
from typing import Union
from urllib.parse import urlparse
from urllib.request import urlretrieve

import moviepy.editor as mp
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
                # Filter out different types of posts
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

                # Check if meme already exists
                current_memes = [meme for meme in os.listdir(self.meme_folderpath) if
                                 os.path.isfile(os.path.join(self.meme_folderpath, meme))]
                if name + ext in current_memes:
                    continue

                # Download meme and save to filepath
                if submission.is_video:
                    # Handler for video files, download video and audio separately,
                    # combine them, and then delete the temporary video and audio file
                    audio_url = url[:-7] + "audio.mp4"
                    filepath = os.path.join(self.meme_folderpath, name + ext)

                    temp_video_filepath = os.path.join(self.meme_folderpath, "temp_" + name + ext)
                    temp_audio_filepath = os.path.join(self.meme_folderpath, "temp_" + name + "_audio" + ext)
                    urlretrieve(url, temp_video_filepath)
                    urlretrieve(audio_url, temp_audio_filepath)

                    video = mp.VideoFileClip(temp_video_filepath)
                    video.write_videofile(filepath, audio=temp_audio_filepath)

                    os.remove(temp_audio_filepath)
                    os.remove(temp_video_filepath)
                else:
                    filepath = os.path.join(self.meme_folderpath, name + ext)
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
