import subprocess
from typing import List
from board.board import Board


class Result:
    def __init__(self):
        self.steps : List = list()

class BoardAI:
    ai_binary_path = "/Users/petershih/Documents/pq3-helper/ai/ai"

    def decide_best_result(self, board: Board) -> Result:
        proc = subprocess.Popen(self.ai_binary_path, stdin=subprocess.PIPE, stdout=subprocess.PIPE)

        s = ""
        for y in range(5):
            for x in range(7):
                s = s + board.grid_types.get_str(board.grids[x][y])

        result_bytes = proc.communicate(bytearray(s.encode()))[0]
        result_str = result_bytes.decode("utf-8")

        result = Result()
        for step_str in result_str.split("\n"):
            step_list = step_str.split(" ")
            if len(step_list)<4:
                break
            x1 = int(step_list[0])
            y1 = int(step_list[1])
            x2 = int(step_list[2])
            y2 = int(step_list[3])
            result.steps.append((x1,y1,x2,y2))

        return result