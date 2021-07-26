from typing import List
import cv2
import configparser
import time
import numpy
import glob
from dataclasses import dataclass

from log.logger import Logger


def cv_size(img):
    return tuple(img.shape[1::-1])


def cv_roi(img, x1, y1, x2, y2):
    return img[y1:y2, x1:x2]


@dataclass
class ImageFindingSpec:
    name : str
    expect_pos_x1 : int
    expect_pos_x2 : int
    expect_pos_y1 : int
    expect_pos_y2 : int
    record_non_match : bool
    record_all : bool
    match_any_pattern : str

    def __init__(self, spec_name: str):
        config_path = "/Users/petershih/Documents/pq3-helper/actions/{0}/parameters.ini".format(
            spec_name)
        config = configparser.ConfigParser()
        config.read(config_path)

        config_spec = config["find_spec"]
        self.name = spec_name
        self.threshold = ImageFindingSpec._try_float(config_spec.get("threshold"))

        self.expect_pos_x1 = ImageFindingSpec._try_int(config_spec.get("expect_pos_x1"))
        self.expect_pos_y1 = ImageFindingSpec._try_int(config_spec.get("expect_pos_y1"))
        self.expect_pos_x2 = ImageFindingSpec._try_int(config_spec.get("expect_pos_x2"))
        self.expect_pos_y2 = ImageFindingSpec._try_int(config_spec.get("expect_pos_y2"))

        if self.expect_pos_x1 is None:
            self.expect_pos_x1 = ImageFindingSpec._try_int(config_spec.get("expect_pos_x"))
            self.expect_pos_y1 = ImageFindingSpec._try_int(config_spec.get("expect_pos_y"))
            self.expect_pos_x2 = self.expect_pos_x1
            self.expect_pos_y2 = self.expect_pos_y1

        self.record_non_match = ImageFindingSpec._try_int(config_spec.get("record_non_match", 0)) == 1
        self.record_all = ImageFindingSpec._try_int(config_spec.get("record_all", 0)) == 1
        self.match_any_pattern = config_spec.get("match_any_pattern", "target.png")

    def _try_float(v) -> float:
        if v is None:
            return None
        return float(v)


    def _try_int(v) -> int:
        if v is None:
            return None
        return int(v)

    def _try_bool(v) -> bool:
        if v is None:
            return None
        return bool(v)


@dataclass
class ImageFindResult:
    found: bool = False

    pos_x: int = None
    pos_y: int = None

    target_w: int = None
    target_h: int = None

def __compare_image(screenshot, target, verbose_log, logger: Logger) -> bool:
    target_img = cv2.imread(target)
    res = cv2.matchTemplate(screenshot, target_img, cv2.TM_SQDIFF_NORMED)

    min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)

    if verbose_log:
        logger.log("Target {}. min_val: {} min_loc: {}".format(target, min_val, min_loc))
    
    return (min_val, min_loc)

def find_image(spec_name: str, screenshot, logger: Logger) -> ImageFindResult:
    result = ImageFindResult()
    spec = ImageFindingSpec(spec_name)

    targets = glob.glob("/Users/petershih/Documents/pq3-helper/actions/{}/{}".format(spec_name, spec.match_any_pattern))
    (result.target_w, result.target_h) = cv_size(cv2.imread(targets[0]))

    if spec.expect_pos_x1 and spec.expect_pos_y1:
        screenshot_roi = cv_roi(
            screenshot, spec.expect_pos_x1, spec.expect_pos_y1,
            spec.expect_pos_x2+result.target_w,
            spec.expect_pos_y2+result.target_h)
    else:
        screenshot_roi = screenshot

    screenshot_roi = screenshot

    matched = False
    score = -1.0
    loc = None
    for target in targets:
        (score, loc) = __compare_image(screenshot_roi, target, spec.expect_pos_x1 is None, logger)
        if score < spec.threshold:
            matched = True
            break

    if spec.expect_pos_x1 and matched:
        result.found = True
        result.pos_x = spec.expect_pos_x1 + loc[0]
        result.pos_y = spec.expect_pos_y1 + loc[1]
        #logger.log("Found spec '{0}'! val: {1} Writing pos: {2},{3}".format(spec_name, min_val, result.pos_x, result.pos_y))
    else:
        result.found = False
        #logger.log("Did not find spec '{0}'. min_val: {1}".format(spec_name, min_val))


    if spec.record_non_match:
        record_path = "/Users/petershih/Documents/pq3-helper/actions/{}/non_match.png".format(spec_name)
        cv2.imwrite(record_path, screenshot_roi)

    if spec.record_all:
        record_path = "/Users/petershih/Documents/pq3-helper/actions/{}/score_{:.2f}_{}.png".format(spec_name, score, time.time())
        cv2.imwrite(record_path, screenshot_roi)

    return result
