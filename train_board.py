import os
from typing import Dict
import cv2
import pathlib
import numpy
import matplotlib.pyplot as plt
import math
from numpy import ndarray
from dataset import images_manager

result_folder = os.path.realpath(os.path.join(
            os.getcwd(), os.path.dirname(__file__), "train"))
tmp_folder = os.path.realpath(os.path.join(
            os.getcwd(), os.path.dirname(__file__), "train_tmp"))
pathlib.Path(tmp_folder).mkdir(exist_ok=True)

x_grids = 7
y_grids = 5

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

def cv_roi(img, x, y, w, h):
    return img[y:y+h, x:x+w]

def cv_size(img):
    return tuple(img.shape[1::-1])

def show_img(img):
    simg = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    plt.imshow(simg)
    plt.show()


def grid_diff_score(img, seed):
    seed_effective_w = 80
    seed_effecgive_h = 80

    seed_x = int((cv_size(seed)[0]-seed_effective_w)/2)
    seed_y = int((cv_size(seed)[1]-seed_effecgive_h)/2)
    seed_roi = cv_roi(seed, seed_x, seed_y, seed_effective_w, seed_effecgive_h)

    res = cv2.matchTemplate(img, seed_roi, cv2.TM_SQDIFF_NORMED)
    min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)

    return min_val

    #diff = cv2.absdiff(img, seed)
    #return numpy.mean(diff)

def compare_grid_image(img, seeds: dict):
    scores = []

    min_score = math.inf
    min_seed_name = ""
    for seed_name, seed in seeds.items():
        score = grid_diff_score(img, seed)
        if score < min_score:
            min_score = score
            min_seed_name = seed_name

    return (min_seed_name, min_score)


mgr = images_manager.ImagesManager()

images = mgr.get_matched_image_paths(lambda metadata: metadata.categorized_as == "stabled_board")
print(len(images))

seeds_files = ["blue.bmp","red.bmp","green.bmp","purple.bmp","skull.bmp","yellow.bmp"]

seeds = {}
for img_name in seeds_files:
    path = os.path.join(result_folder, "board", img_name)
    seeds[img_name[:-4]] = cv2.imread(path)


grid_imgs = []
for path in images:
    print(path)
    img = cv2.imread(path)

    for x_idx in range(x_grids):
        for y_idx in range(y_grids):
            (x,y,w,h) = get_grid_rect(x_idx, y_idx)
            img_grid = cv_roi(img, x,y,w,h)

            (grid_type, score) = compare_grid_image(img_grid, seeds)

            folder = os.path.join(tmp_folder, grid_type)
            pathlib.Path(folder).mkdir(exist_ok=True)

            grid_filename = "score_{:.2f}_{}_grid_{}_{}.bmp".format(score, os.path.basename(path), x_idx, y_idx)
            grid_filepath = os.path.join(tmp_folder, grid_filename)
            grid_file_path = os.path.join(folder, grid_filename)
            cv2.imwrite(grid_file_path, img_grid)

