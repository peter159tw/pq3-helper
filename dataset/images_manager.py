import os
import pathlib
import time
import cv2
from configparser import ConfigParser
from typing import List


class ImageMetadata:
    categorized_as: str

    def get_dict(self):
        return {
            "categorized_as": self.categorized_as
        }

    def from_dict(self, d):
        self.categorized_as = d["categorized_as"]


class ImagesManager:
    __folder: str

    __config: ConfigParser = ConfigParser()
    __config_path: str

    def __init__(self):
        super().__init__()
        self.__folder = os.path.realpath(os.path.join(
            os.getcwd(), os.path.dirname(__file__), "data"))
        pathlib.Path(self.__folder).mkdir(exist_ok=True)
        self.__config_path = os.path.join(self.__folder, "config.ini")

    def add_img(self, img, metadata: ImageMetadata):
        filename = self.__write_img(img)

        self.__config[filename] = metadata.get_dict()
        self.__write_config()

    def __write_img(self, img):
        filename = str(time.time())+".jpg"
        cv2.imwrite(os.path.join(self.__folder, filename), img)
        return filename

    def __write_config(self):
        with open(self.__config_path, "w") as f:
            self.__config.write(f)
