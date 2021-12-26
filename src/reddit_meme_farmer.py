# -*- coding: utf-8 -*-
"""
MIT License

Copyright (c) 2021 Dinesh Pinto

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

import logging
import os
import re
import sys
from typing import Union
from urllib.parse import urlparse
from urllib.request import urlretrieve

import moviepy.editor as mp
import praw

from config import REDDIT_CLIENT_ID, REDDIT_SECRET, REDDIT_USER_AGENT


class RedditMemeFarmer:
    def __init__(self, folder: str = "memes", subreddit: str = "cryptocurrencymemes"):
        logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                            stream=sys.stdout, level=logging.INFO)
        self.logger = logging.getLogger(__name__)

        self.rbot = praw.Reddit(client_id=REDDIT_CLIENT_ID,
                                client_secret=REDDIT_SECRET,
                                user_agent=REDDIT_USER_AGENT)
        self.meme_folderpath = self.create_data_directory(folder)
        self.meme_subreddit = subreddit
        self.logger.info(f"Memes from r/{self.meme_subreddit} will be saved to {self.meme_folderpath}")

        self.submission_titles = []
        self.limit = 10

    @staticmethod
    def create_data_directory(folder: str) -> str:
        """ Check if given directory exists, if not, create it. """
        data_dir = os.path.join(os.getcwd(), folder)
        if not os.path.exists(data_dir):
            os.makedirs(data_dir)

        return data_dir

    @staticmethod
    def parse_filename_from_url(url: str) -> str:
        """ Extract filename to save file with from URL. """
        filename = url.split("/")

        if len(filename) == 0:
            filename = re.findall("/(.*?)", url)

        filename = filename[-1]

        if "." not in filename:
            filename += ".jpg"
        return filename

    def __video_handler(self, url: str, name: str, ext: str) -> str:
        """
        Handler for video files, download video and audio separately,
        combine them, and then delete the temporary video and audio file.
        """
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
        return filepath

    def get_crypto_meme_path(self) -> Union[str, bool]:
        """
        Query Reddit API to get the hottest memes, save them and return
        the filepath.

        - Text posts are filtered out
        - For image files, download directly with urlretrieve
        - For video files, download video and audio separately and combine
        them with moviepy
        """
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

                # Check if meme already exists, skip if it does
                current_memes = [meme for meme in os.listdir(self.meme_folderpath) if
                                 os.path.isfile(os.path.join(self.meme_folderpath, meme))]
                if name + ext in current_memes:
                    continue

                # Download meme and save to filepath
                if submission.is_video:
                    filepath = self.__video_handler(url, name, ext)
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
