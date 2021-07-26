from typing import Tuple
import cv2
import math
import os
import time
import numpy
from board.grid_types import GridTypes, GridType
from board.board import Board

x_grids = 7
y_grids = 5

def cv_roi(img, x, y, w, h):
    return img[y:y+h, x:x+w]

def cv_size(img):
    return tuple(img.shape[1::-1])

def cv_roi_center(img, w, h):
    x = int((cv_size(img)[0]-w)/2)
    y = int((cv_size(img)[1]-h)/2)
    return cv_roi(img, x, y, w, h)

def get_grid_rect(idx_x: int, idx_y: int):
    x1 = 738
    y1 = 214
    x2 = 1601
    y2 = 833

    w = (x2-x1)/x_grids
    h = (y2-y1)/y_grids
    x = x1 + w*idx_x
    y = y1 + h*idx_y
    return (int(x), int(y), int(w), int(h))

def get_grid_center(x:int, y:int):
    (x,y,w,h) = get_grid_rect(x,y)
    return (x+w/2, y+h/2)

def grid_diff_score(img, seed):
    seed_roi = cv_roi_center(seed, 80, 80)
    img = cv_roi_center(img, 90, 90)

    res = cv2.matchTemplate(img, seed_roi, cv2.TM_SQDIFF_NORMED)
    min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)

    return min_val

def compare_grid_image(img, grid_types: GridTypes) -> Tuple[GridType, float]:
    scores = []

    min_score = math.inf
    min_grid_type = None
    min_grid_type_str = None
    min_grid_img = None
    for grid_type in grid_types.grid_types:
        for grid_img in grid_type.images:
            score = grid_diff_score(img, grid_img)
            if score < min_score:
                min_score = score
                min_grid_type = grid_type
                min_grid_type_str = grid_type.short_str
                min_grid_img = grid_img
    
    return (min_grid_type, min_score)

class HpParser:
    x1 = 1752
    y1 = 976
    x2 = 2105
    y2 = 982

    img_full_path = os.path.realpath(os.path.join(os.getcwd(), os.path.dirname(__file__), "hp", "full.png"))
    img_full = None

    def __init__(self):
        self.img_full = self._get_roi(cv2.imread(self.img_full_path))

    def _get_roi(self, img):
        return img[self.y1:self.y2,self.x1:self.x2]

    def parse(self, board_img) -> float:
        img = self._get_roi(board_img)
        img_diff = cv2.absdiff(self.img_full, img)
        img_diff = cv2.cvtColor(img_diff, cv2.COLOR_BGR2GRAY)
        img_mean = numpy.mean(img_diff, axis=0)
        img_binary = img_mean > 40

        max_pos = 0
        max_score = 0
        for x in range(img_binary.shape[0]):
            score = numpy.sum(img_binary[:x] == True) + numpy.sum(img_binary[x:] == False) 
            if score > max_score:
                max_pos = x
                max_score = score
        return (img_binary.shape[0]-max_pos) / img_binary.shape[0]


class BoardImageParser:
    grid_types = GridTypes()

    def parse(self, board_img, report=True) -> Board:
        start_time = time.time()

        ret = Board()
        ret.grid_types = self.grid_types

        for x_idx in range(7):
            for y_idx in range(5):
                (x, y, w, h) = get_grid_rect(x_idx, y_idx)
                img_grid = cv_roi(board_img, x, y, w, h)

                (grid_type, score) = compare_grid_image(img_grid, self.grid_types)

                if ret.parse_score is None:
                    ret.parse_score = score
                else:
                    ret.parse_score = max(ret.parse_score, score)

                ret.grids[x_idx, y_idx] = grid_type.value
                if report:
                    self.__report_grid_parse_result(img_grid, grid_type, score)

        print("BoardImageParser.parse() took {:.2f} seconds".format(time.time()-start_time))

        ret.update_locks()
        return ret

    def __report_grid_parse_result(self, img_grid, grid_type: GridType, score):
        if score > 0.05:
            grid_type.record_image(img_grid, score)