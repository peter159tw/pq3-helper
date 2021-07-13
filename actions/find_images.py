from typing import List
import cv2
import configparser
import numpy
import glob

from log.logger import Logger


def cv_size(img):
    return tuple(img.shape[1::-1])


def cv_roi(img, x, y, w, h):
    return img[y:y+h, x:x+w]


class ImageFindingSpec:
    name: str = None

    expect_pos_x: int = None
    expect_pos_y: int = None

    threshold: float = None

    record_non_match: bool = None
    match_any_pattern: str = None


class ImageFindResult:
    found: bool = False

    pos_x: int = None
    pos_y: int = None

    target_w: int = None
    target_h: int = None


def __try_float(v):
    if v is None:
        return None
    return float(v)


def __try_int(v):
    if v is None:
        return None
    return int(v)

def __try_bool(v):
    if v is None:
        return None
    return bool(v)


def __parse_spec(spec_name: str) -> ImageFindingSpec:
    config_path = "/Users/petershih/Documents/pq3-helper/actions/{0}/parameters.ini".format(
        spec_name)
    config = configparser.ConfigParser()
    config.read(config_path)

    config_spec = config["find_spec"]
    ret = ImageFindingSpec()
    ret.name = spec_name
    ret.threshold = __try_float(config_spec.get("threshold"))
    ret.expect_pos_x = __try_int(config_spec.get("expect_pos_x"))
    ret.expect_pos_y = __try_int(config_spec.get("expect_pos_y"))
    ret.record_non_match = __try_int(config_spec.get("record_non_match", 0)) == 1
    ret.match_any_pattern = config_spec.get("match_any_pattern", "target.png")
    return ret

def __compare_image(screenshot, target, threshold, verbose_log, logger: Logger) -> bool:
    target_img = cv2.imread(target)
    res = cv2.matchTemplate(screenshot, target_img, cv2.TM_SQDIFF_NORMED)
    min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)

    if verbose_log:
        logger.log("Target {}. min_val: {} min_loc: {}".format(target, min_val, min_loc))

    return min_val < threshold

def find_image(spec_name: str, screenshot, logger: Logger) -> ImageFindResult:
    result = ImageFindResult()
    spec = __parse_spec(spec_name)

    targets = glob.glob("/Users/petershih/Documents/pq3-helper/actions/{}/{}".format(spec_name, spec.match_any_pattern))
    (result.target_w, result.target_h) = cv_size(cv2.imread(targets[0]))

    if spec.expect_pos_x and spec.expect_pos_y:
        screenshot_roi = cv_roi(
            screenshot, spec.expect_pos_x, spec.expect_pos_y, result.target_w, result.target_h)
    else:
        screenshot_roi = screenshot

    matched = False
    for target in targets:
        if __compare_image(screenshot_roi, target, spec.threshold, spec.expect_pos_x is None, logger):
            matched = True
            break

    if spec.expect_pos_x and matched:
        result.found = True
        result.pos_x = spec.expect_pos_x
        result.pos_y = spec.expect_pos_y
        #logger.log("Found spec '{0}'! val: {1} Writing pos: {2},{3}".format(spec_name, min_val, result.pos_x, result.pos_y))
    else:
        result.found = False
        #logger.log("Did not find spec '{0}'. min_val: {1}".format(spec_name, min_val))


    if spec.record_non_match:
        record_path = "/Users/petershih/Documents/pq3-helper/actions/{0}/non_match.png".format(spec_name)
        cv2.imwrite(record_path, screenshot_roi)

    return result


def img_diff_score(img1, img2, x1, y1, x2, y2):
    img1_roi = cv_roi(img1, x1, y1, x2-x1, y2-y1)
    img2_roi = cv_roi(img2, x1, y1, x2-x1, y2-y1)
    diff = cv2.absdiff(img1_roi, img2_roi)
    return numpy.mean(diff)