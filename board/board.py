import numpy
from board.grid_types import GridTypes

class Board:
    grid_types: GridTypes = None

    UNLOCKED = 0.0
    LOCKED = 1.0

    def __init__(self):
        self.grids = numpy.zeros((7,5))
        self.locked = numpy.zeros((7,5))  # zero -> unlocked
        self.parse_score = None

    def __str__(self):
        o = ""
        for y in range(5):
            for x in range(7):
                o = o + self.grid_types.get_str(self.grids[x,y])
                o = o + ("*" if self.is_locked_nocheck(x, y) else " ") + " "
            o = o + "\n"
        return o

    def __hash__(self):
        return hash(self.grids.tobytes())

    def __eq__(self, other):
        return numpy.array_equal(self.grids, other.grids)

    def update_locks(self):
        class MatchThreeFinder:
            board = None
            candidates = []
            candidates_grid_type = None

            def __init__(self, board):
                self.board = board
                self.candidates = []
                self.candidates_grid_type = None

            def __str__(self):
                return "candidates: {}".format(self.candidates)

            def add(self, x, y):
                if self.candidates_grid_type is None:
                    pass
                else:
                    if self.candidates_grid_type != self.board.grids[x,y]:
                        self.__mark_locks()
                        self.candidates.clear()

                self.candidates_grid_type = self.board.grids[x,y]
                self.candidates.append((x,y))

            def finalize(self):
                self.__mark_locks()

            def __mark_locks(self):
                if len(self.candidates) < 3:
                    return
                for x,y in self.candidates:
                    self.board.locked[x,y] = Board.LOCKED

        # scan along x
        for x in range(7):
            finder = MatchThreeFinder(self)
            for y in range(5):
                finder.add(x,y)
            finder.finalize()

        # scan along y
        for y in range(5):
            finder = MatchThreeFinder(self)
            for x in range(7):
                finder.add(x,y)
            finder.finalize()

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
        ret.grid_types = self.grid_types
        ret.grids = numpy.ndarray.copy(self.grids)
        ret.locked = numpy.ndarray.copy(self.locked)
        return ret

    def swap(self, x1, y1, x2, y2):
        # try to swap; return False if cannot swap, and board will be in an invalid state

        if not self.in_range(x1, y1) or not self.in_range(x2, y2):
            return None

        if self.is_locked_nocheck(x1, y1) or self.is_locked_nocheck(x2, y2):
            return None

        ret = self.copy()
        ret.__swap_nocheck(x1, y1, x2, y2)

        ret.update_locks()
        if not ret.is_locked_nocheck(x1,y1) and not ret.is_locked_nocheck(x2,y2):
            return None

        return ret

    def __swap_nocheck(self, x1, y1, x2, y2):
        old = self.grids[x1, y1]
        self.grids[x1, y1] = self.grids[x2, y2]
        self.grids[x2, y2] = old

    def total_locks(self):
        locks = 0
        for x in range(7):
            for y in range(5):
                if self.is_locked_nocheck(x, y):
                    locks += 1
        return locks
