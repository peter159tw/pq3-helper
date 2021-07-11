from device import monkey_runner_adaptor
import copy
import time
import cv2
import pathlib
import os
import numpy
import train_board
from enum import Enum


class GridType(Enum):
    RED = 1
    YELLOW = 2
    GREEN = 3
    BLUE = 4
    PURLE = 5
    SKULL = 6

    def __str__(self):
        if self == GridType.RED:
            return "R"
        if self == GridType.YELLOW:
            return "Y"
        if self == GridType.GREEN:
            return "G"
        if self == GridType.BLUE:
            return "B"
        if self == GridType.PURLE:
            return "P"
        if self == GridType.SKULL:
            return "S"
        return "?"

    def parse(s):
        if s == "R":
            return GridType.RED
        if s == "Y":
            return GridType.YELLOW
        if s == "G":
            return GridType.GREEN
        if s == "B":
            return GridType.BLUE
        if s == "P":
            return GridType.PURLE
        if s == "S":
            return GridType.SKULL


possible_match3_directions = [
    [[-2, 0], [-1, 0], [0, 0]],
    [[-1, 0], [0, 0], [1, 0]],
    [[0, 0], [1, 0], [2, 0]],
    [[0, -2], [0, -1], [0, 0]],
    [[0, -1], [0, 0], [0, 1]],
    [[0, 0], [0, 1], [0, 2]],
]


class Board:
    grids = numpy.ndarray((7, 5))

    UNLOCKED = 0.0
    LOCKED = 1.0
    locked = numpy.ndarray((7, 5))  # 1 -> locked; 0 -> unlocked

    def parse(self, s):
        for x in range(7):
            for y in range(5):
                self.grids[x, y] = GridType.parse(s[x][y]).value
        self.__update_locks()

    def __str__(self):
        o = ""
        for y in range(5):
            for x in range(7):
                o = o + str(GridType(int(self.grids[x, y]))) + (
                    "*" if self.is_locked_nocheck(x, y) else " ") + " "
            o = o + "\n"
        return o

    def __hash__(self):
        return hash(self.grids.tobytes())

    def __eq__(self, other):
        return numpy.array_equal(self.grids, other.grids)

    def __update_locks(self):
        for x in range(7):
            for y in range(5):
                has_match = False
                for d in possible_match3_directions:
                    if self.__same_grid_type_along_offset(x, y, d):
                        has_match = True
                        break
                self.locked[x, y] = self.LOCKED if has_match else self.UNLOCKED

    def in_range(self, x, y):
        if x < 0 or x >= 7:
            return False
        if y < 0 or y >= 5:
            return False
        return True

    def is_locked_nocheck(self, x, y):
        return self.locked[x, y] == self.LOCKED

    def copy(self):
        ret = Board()
        ret.grids = numpy.ndarray.copy(self.grids)
        ret.locked = numpy.ndarray.copy(self.locked)
        return ret

    # try to swap; return False if cannot swap, and board will be in an invalid state

    def swap(self, x1, y1, x2, y2):
        if not self.in_range(x1, y1) or not self.in_range(x2, y2):
            return False

        if self.is_locked_nocheck(x1, y1) or self.is_locked_nocheck(x2, y2):
            return False

        self.__swap_nocheck(x1, y1, x2, y2)

        if not self.__has_match(x1, y1) and not self.__has_match(x2, y2):
            return False

        self.__update_locks()
        return True

    def __swap_nocheck(self, x1, y1, x2, y2):
        old = self.grids[x1, y1]
        self.grids[x1, y1] = self.grids[x2, y2]
        self.grids[x2, y2] = old

    def __same_grid_type_along_offset(self, x, y, offsets):
        v = None
        for dx, dy in offsets:
            if not self.in_range(x+dx, y+dy):
                return False

            current_v = self.grids[x+dx, y+dy]
            if v is None:
                v = current_v
            if int(v) != int(current_v):
                return False
        return True

    # return boolean indicating if there's a match at (x,y)
    def __has_match(self, x, y):
        for match_check in possible_match3_directions:
            if self.__same_grid_type_along_offset(x, y, match_check):
                return True
        return False

    def total_locks(self):
        locks = 0
        for x in range(7):
            for y in range(5):
                if self.is_locked_nocheck(x, y):
                    locks += 1
        return locks


class BoardImageParser:
    seed_folder = os.path.realpath(os.path.join(
        os.getcwd(), os.path.dirname(__file__), "train"))
    seeds_files = {
        "blue.bmp": GridType.BLUE,
        "red.bmp": GridType.RED,
        "green.bmp": GridType.GREEN,
        "purple.bmp": GridType.PURLE,
        "skull.bmp": GridType.SKULL,
        "yellow.bmp": GridType.YELLOW,
    }

    def parse(self, board_img) -> Board:
        seeds = {}
        for (img_name, grid_type) in self.seeds_files.items():
            path = os.path.join(self.seed_folder, "board", img_name)
            seeds[grid_type] = cv2.imread(path)
            print("seed image: {}".format(seeds[grid_type].shape))

        ret = Board()
        for x_idx in range(7):
            for y_idx in range(5):
                (x, y, w, h) = train_board.get_grid_rect(x_idx, y_idx)
                img_grid = train_board.cv_roi(board_img, x, y, w, h)

                (grid_type, score) = train_board.compare_grid_image(img_grid, seeds)
                if score > 0.1:
                    print("{},{} -> type={} score={:.3f}".format(x_idx,
                          y_idx, grid_type, score))
                    grid_filename = "score_{:.2f}_{}.bmp".format(
                        score, time.time())
                    folder = os.path.realpath(os.path.join(
                        os.getcwd(), os.path.dirname(__file__), "train_tmp"))
                    pathlib.Path(folder).mkdir(exist_ok=True)
                    cv2.imwrite(os.path.join(folder, grid_filename), img_grid)

                ret.grids[x_idx, y_idx] = grid_type.value
        return ret


board_str = [
    "GPRGS",
    "GGPBG",
    "YBRYP",
    "PBRBG",
    "YRYRS",
    "YGBPY",
    "RRSPB",
]

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

#board = Board()
# board.parse(board_str)
# print(str(board))


board_folder = os.path.realpath(os.path.join(
    os.getcwd(), os.path.dirname(__file__)))
board_img_path = os.path.join(board_folder, "_temp_last_screenshot.png")
board_img = cv2.imread(board_img_path)
print("board image: {}".format(board_img.shape))
parser = BoardImageParser()
board = parser.parse(board_img)
print(board)

visited = set()


class Result:
    steps = None
    final_board: Board = None

    def __str__(self):
        return "{} steps; {} locks".format(len(self.steps), self.final_board.total_locks())


results = []


def dfs(board: Board, history: list):
    any_swappable = False

    for x in range(7):
        for y in range(5):
            for (dx, dy) in possible_swap_directions:
                new_board = board.copy()
                if not new_board.swap(x, y, x+dx, y+dy):
                    continue

                if new_board in visited:
                    continue
                visited.add(new_board)

                any_swappable = True

                next_history = copy.deepcopy(history)
                next_history.append([x, y, x+dx, y+dy])
                #print("can swap: {},{} delta={},{}".format(x,y,dx,dy))
                # print(str(new_board))
                dfs(new_board, next_history)

    if not any_swappable:
        r = Result()
        r.steps = history
        r.final_board = board.copy()
        results.append(r)


print("start")
dfs(board, [])
print("done")

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


for (x1, y1, x2, y2) in best_result.steps:
    monkey_runner.drag(*train_board.get_grid_center(x1,y1), *train_board.get_grid_center(x2,y2))
    time.sleep(0.2)
