from device import monkey_runner_adaptor
from board.board_image_parser import BoardImageParser
from board.ai import BoardAI
import copy
import time
import cv2
import pathlib
import os
import numpy
import train_board
from enum import Enum

def cv_roi(img, x, y, w, h):
    return img[y:y+h, x:x+w]

img_full = cv2.imread("/Users/petershih/Documents/pq3-helper/hp_full.png")
img_full = cv_roi(img_full, 1756, 976, 2100-1756, 1019-976)
#cv2.imshow("hp_full", img_full)

img = cv2.imread("/Users/petershih/Documents/pq3-helper/board_test.png")
img = cv_roi(img, 1756, 976, 2100-1756, 1019-976)
print(img.shape)
#cv2.imshow("hp bar", img)

img_diff = cv2.absdiff(img_full, img)
img_diff = cv2.cvtColor(img_diff, cv2.COLOR_BGR2GRAY)
#cv2.imshow("hp diff", img_diff)

img_mean = numpy.mean(img_diff, axis=0)
print(img_mean)

img_binary = img_mean > 40
print(img_binary)
print(img_binary.shape)

max_pos = 0
max_score = 0
for x in range(img_binary.shape[0]):
    score = numpy.sum(img_binary[:x] == True) + numpy.sum(img_binary[x:] == False) 
    if score > max_score:
        max_pos = x
        max_score = score
print(max_pos)
print((img_binary.shape[0]-max_pos) / img_binary.shape[0])

#cv2.waitKey()
#cv2.destroyAllWindows()

