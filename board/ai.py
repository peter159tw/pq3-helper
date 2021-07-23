import subprocess
from typing import Dict, List
from board.board import Board


class Result:
    def __init__(self):
        self.steps : List = list()
        self.final_board : Board = None
        self.final_board_has_stun = False
        self.final_board_lock_count_per_grid_type : Dict[int, int] = dict()
        self.final_board_total_locks : int = 0

    def calculate_final_board_stats(self):
        self.final_board_total_locks = self.final_board.total_locks()
        self.final_board_has_stun = self.has_stun(self.final_board)

        for x in range(7):
            for y in range(5):
                if self.final_board.is_locked_nocheck(x, y):
                    grid_type = int(self.final_board.grids[x,y])
                    self.final_board_lock_count_per_grid_type[grid_type] = self.final_board_lock_count_per_grid_type.get(grid_type, 0) + 1

    def has_stun(self, board: Board):
        for y in range(5):
            all_same = True
            grid_type = self.final_board.grids[0,y]
            for x in range(7):
                if self.final_board.grids[x,y] != grid_type:
                    all_same = False
                    break
            if all_same:
                return True
        return False

    def __str__(self):
        return "{} steps; {} locks; stun={}".format(len(self.steps), self.final_board.total_locks(), self.final_board_has_stun)

class BoardAI:
    ai_binary_path = "/Users/petershih/Documents/pq3-helper/ai/ai"

    def __init__(self):
        self.last_board : Board = None
        self.last_board_result : Result = None

    def decide_best_result(self, board: Board) -> Result:
        if self.last_board is not None and self.last_board == board:
            print("ai cache hit")
            return self.last_board_result

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

        self._fill_detail_result(board, result)
        self._cache_result(board, result)

        return result

    def _cache_result(self, board: Board, result: Result) :
        self.last_board = board
        self.last_board_result = result

    def _fill_detail_result(self, board: Board, result: Result):
        result.final_board = board
        for (x1,y1,x2,y2) in result.steps:
            result.final_board = result.final_board.swap(x1,y1,x2,y2)
            if result.final_board is None:
                print("CRITICAL ERROR: AI returns wrong step.")
                return

        result.calculate_final_board_stats()
        