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



parser = BoardImageParser()
board = parser.parse(cv2.imread("/Users/petershih/Documents/pq3-helper/board_test.png"))
print(board)

board_ai = BoardAI()
best_result = board_ai.decide_best_result(board)

print("best result: ")
print(best_result.steps)
