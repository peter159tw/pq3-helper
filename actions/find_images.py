import cv2
from logger import Logger

def cv_size(img):
    return tuple(img.shape[1::-1])


def cv_roi(img, x, y, w, h):
    return img[y:y+h, x:x+w]


class ImageFindingSpec:
    target: str = None

    expect_pos_x: int = None
    expect_pos_y: int = None

    threshold: float = None


class ImageFindResult:
    pos_x: int = None
    pos_y: int = None


def find_image(spec: ImageFindingSpec, screenshot, logger: Logger) -> ImageFindResult:
    target = cv2.imread(
        "/Users/petershih/Documents/pq3-helper/actions/{0}/target.png".format(spec.target))
    (target_w, target_h) = cv_size(target)

    if spec.expect_pos_x and spec.expect_pos_y:
        screenshot_roi = cv_roi(
            screenshot, spec.expect_pos_x, spec.expect_pos_y, target_w, target_h)
    else:
        screenshot_roi = screenshot
    res = cv2.matchTemplate(screenshot_roi, target, cv2.TM_SQDIFF_NORMED)
    min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)

    if not spec.expect_pos_x:
        logger.log("Spec '{0}' min_val: {1} min_loc: {2}".format(
            spec.target, min_val, min_loc))

    result = ImageFindResult()
    if spec.expect_pos_x and min_val < spec.threshold:
        result.pos_x = (int)(spec.expect_pos_x + cv_size(target)[0]/2)
        result.pos_y = (int)(spec.expect_pos_y + cv_size(target)[1]/2)
        logger.log("Found spec '{0}'! val: {1} Writing pos: {2},{3}".format(
            spec.target, min_val, result.pos_x, result.pos_y))
    else:
        # context.logger.log(
        #   "Did not find spec '{0}'. min_val: {1}".format(spec.target, min_val))
        pass

    return result
