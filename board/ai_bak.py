import functools
import copy
import random
from typing import Dict
from board.board import Board
from board.grid_types import GridType


class Result:
    def __init__(self):
        self.steps = None
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
    possible_swap_directions = [
        # [-1,-1],  # symmetric to [1,1]
        # [-1,0],  # symmetric to [1,0]
        # [-1,1],  # symmetric to [1,-1]
        # [0,-1],  # symmetric to [0,1]
        [0, 1],
        [1, -1],
        [1, 0],
        [1, 1]
    ]

    possible_swaps = []

    __visited = None
    __results = None

    def __init__(self):
        for x in range(7):
            for y in range(5):
                for (dx, dy) in self.possible_swap_directions:
                    self.possible_swaps.append((x,y,dx,dy))

    def decide_best_result(self, board: Board) -> Result:
        results = self.dfs(board)

        def compare(lhs: Result, rhs: Result):
            if lhs.final_board_has_stun:
                return -1
            if rhs.final_board_has_stun:
                return 1

            # prefer blue
            blue_grid_type_value = 1
            lhs_blue_count = lhs.final_board_lock_count_per_grid_type.get(blue_grid_type_value, 0)
            rhs_blue_count = rhs.final_board_lock_count_per_grid_type.get(blue_grid_type_value, 0)
            if lhs_blue_count > rhs_blue_count:
                return -1
            if rhs_blue_count > lhs_blue_count:
                return 1

            # total locks
            if lhs.final_board_total_locks > rhs.final_board_total_locks:
                return -1
            if rhs.final_board_total_locks > lhs.final_board_total_locks:
                return 1
            
            return 0

        best_result = min(results, key=functools.cmp_to_key(compare))

        print("best result:")
        print(best_result)
        return best_result

    def dfs(self, board: Board):
        self.__visited = set()
        self.__results = []
        self.__dfs(board, [])
        return self.__results

    def __dfs(self, board: Board, history: list):
        swaps_try_order = copy.deepcopy(self.possible_swaps)
        random.shuffle(swaps_try_order)

        any_swappable = False

        if len(self.__results) > 100:
            return

        for (x,y,dx,dy) in swaps_try_order:
            new_board = board.swap(x, y, x+dx, y+dy)
            if new_board is None:
                continue

            if new_board in self.__visited:
                continue
            self.__visited.add(new_board)

            any_swappable = True

            next_history = copy.deepcopy(history)
            next_history.append([x, y, x+dx, y+dy])
            #print("can swap: {},{} delta={},{}".format(x,y,dx,dy))
            #print(str(new_board))
            self.__dfs(new_board, next_history)

        if not any_swappable:
            r = Result()
            r.steps = history
            r.final_board = board.copy()
            r.calculate_final_board_stats()
            self.__results.append(r)
            print("got one possible path (total={}): {}".format(len(self.__results), str(r)))


