import cv2
import configparser
import numpy

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
    return ret

def find_image(spec_name: str, screenshot, logger: Logger) -> ImageFindResult:
    result = ImageFindResult()
    spec = __parse_spec(spec_name)

    target = cv2.imread(
        "/Users/petershih/Documents/pq3-helper/actions/{0}/target.png".format(spec_name))
    (result.target_w, result.target_h) = cv_size(target)

    if spec.expect_pos_x and spec.expect_pos_y:
        screenshot_roi = cv_roi(
            screenshot, spec.expect_pos_x, spec.expect_pos_y, result.target_w, result.target_h)
    else:
        screenshot_roi = screenshot
    res = cv2.matchTemplate(screenshot_roi, target, cv2.TM_SQDIFF_NORMED)
    min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)

    if not spec.expect_pos_x:
        logger.log("Spec '{0}' min_val: {1} min_loc: {2}".format(
            spec.name, min_val, min_loc))

    if spec.expect_pos_x and min_val < spec.threshold:
        result.found = True
        result.pos_x = spec.expect_pos_x
        result.pos_y = spec.expect_pos_y
        #logger.log("Found spec '{0}'! val: {1} Writing pos: {2},{3}".format(
        #    spec_name, min_val, result.pos_x, result.pos_y))
    else:
        result.found = False
        # context.logger.log(
        #   "Did not find spec '{0}'. min_val: {1}".format(spec.target, min_val))

    return result


def img_diff_score(img1, img2, x1, y1, x2, y2):
    img1_roi = cv_roi(img1, x1, y1, x2-x1, y2-y1)
    img2_roi = cv_roi(img2, x1, y1, x2-x1, y2-y1)
    diff = cv2.absdiff(img1_roi, img2_roi)
    return numpy.mean(diff)