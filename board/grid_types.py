import configparser
import os
import pathlib
from typing import Dict, List
import cv2

class GridType:
    def __init__(self):
        self.name: str = None
        self.short_str: str = None
        self.folder_path: str = None
        self.value: float = None
        self.value_matchable_normalized: float = None
        self.images = list()

    def load_images(self):
        for (dirpath, dirnames, filenames) in os.walk(self.folder_path):
            for filename in filenames:
                if filename[-4:] != ".bmp":
                    continue
                img_path = os.path.join(dirpath, filename)
                img = cv2.imread(img_path)
                self.images.append(img)

    def record_image(self, img, score):
        folder = os.path.realpath(os.path.join(self.folder_path, "../dataset", self.name))
        os.makedirs(folder, exist_ok=True)
        path = os.path.join(folder, "score_{:.3f}.bmp".format(score))
        cv2.imwrite(path, img)

    def __str__(self):
        return "{}: v={:.1f}, matchable_v={:.1f}, folder={}".format(self.short_str, self.value, self.value_matchable_normalized, self.folder_path)
    

class GridTypes:
    grid_types: List[GridType] = list()

    def __init__(self):
        self.config = configparser.ConfigParser()
        config_path = os.path.realpath(os.path.join(
                os.getcwd(), os.path.dirname(__file__), "grid_types", "config.ini"))
        self.config.read(config_path)

        for section in self.config.sections():
            self.grid_types.append(self.__load_grid_type(section, self.config[section]))

    def __load_grid_type(self, name: str, dict: Dict):
        ret = GridType()
        ret.name = name
        ret.short_str = dict.get("grid_str")
        ret.folder_path = os.path.realpath(os.path.join(
                os.getcwd(), os.path.dirname(__file__), "grid_types", name))
        ret.value = float(dict.get("grid_value"))
        ret.value_matchable_normalized = float(dict.get("grid_value_matchable_normalized"))
        ret.load_images()
        print(str(ret))
        print(len(ret.images))
        return ret

    def get_str(self, grid_value: float):
        for grid_type in self.grid_types:
            if grid_type.value == grid_value:
                return grid_type.short_str
        return "?"


if __name__ == "__main__":
    grid_types = GridTypes()