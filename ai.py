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
board = parser.parse(cv2.imread("/Users/petershih/Documents/pq3-helper/dataset/data/1626029355.198876.jpg"))

arr = board.grids
print(arr)
arr[0,0]=1
arr[0,1]=1
arr[0,2]=1

arr2 = numpy.ndarray((3))
arr2[0] = True
arr2[1] = True
arr2[2] = True
print(arr2)

print(arr[0,:]==1)
arr3 = numpy.convolve(arr[0,:]==1, arr2, 'valid')==numpy.sum(arr2)
print(arr3)

exit()
board_ai = BoardAI()
results = board_ai.dfs(board)

best_locks = 0
best_result = None
for result in results:
    if result.final_board.total_locks() > best_locks:
        best_locks = result.final_board.total_locks()
        best_result = result

print("best result")
print(best_result)
print(best_result.final_board)
print(best_result.steps)

monkey_runner = monkey_runner_adaptor.MonkeyRunnerAdaptor()
# monkey_runner.touch(818,976)

#monkey_runner.drag(*train_board.get_grid_center(3,3), *train_board.get_grid_center(4,4))


#for (x1, y1, x2, y2) in best_result.steps:
    #monkey_runner.drag(*train_board.get_grid_center(x1,y1), *train_board.get_grid_center(x2,y2))
    #time.sleep(0.2)
