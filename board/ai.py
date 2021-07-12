import copy
import random
from board.board import Board


class Result:
    steps = None
    final_board: Board = None

    def __str__(self):
        return "{} steps; {} locks".format(len(self.steps), self.final_board.total_locks())


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

    def decide_best_result(self, board: Board):
        results = self.dfs(board)

        best_locks = 0
        best_result = None
        for result in results:
            if result.final_board.total_locks() > best_locks:
                best_locks = result.final_board.total_locks()
                best_result = result

        print("best result:")
        print(best_result.final_board)
        return best_result.steps

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
            self.__results.append(r)
            print(len(self.__results))


