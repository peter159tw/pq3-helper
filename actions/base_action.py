from board.board import Board
import copy
from typing import Iterable

from PyQt5.QtCore import QObject, pyqtSignal
from abc import ABC, abstractmethod

from actions.find_images import ImageFindResult
from flow.game_state import GameState
from device.device_controller import DeviceController
from log.logger import Logger
from dataset.images_manager import ImagesManager
from board.board_image_parser import BoardImageParser
from board.ai import BoardAI


class BoardStableChecker():
    pos_x1 = 730
    pos_y1 = 207
    pos_x2 = 1607
    pos_y2 = 837

    stable_total_count = 2
    max_secs = 10

    prev_board : Board = None
    stable_count = 1

    def __init__(self):
        # don't clear "prev_board" and "stable_from_time" so we can memorize what's the last stable board, and early-exit if nothing happens between
        self.board_score = None
        self.stabled = False

    def is_stable(self, context):
        context.game_state.board = context.board_image_parse.parse(context.device.last_captured_screenshot)
        self.board_score = context.game_state.board.parse_score
        #if self.board_score < 0.05:
            # board is recognizable. have confidence it's already stable
            #return True

        if self.board_score > 0.2:
            self.prev_board = None
            return False

        if self.prev_board is not None and self.prev_board == context.game_state.board:
            self.stable_count += 1
        else:
            self.stable_count = 1

        self.prev_board = context.game_state.board.copy()

        if self.stable_count >= self.stable_total_count:
            return True

        return False

    def reset(self):
        self.prev_board = None
        self.stable_count = 1


class ActionRunningContext(QObject):
    device: DeviceController = None
    logger: Logger = None
    board_image_parse: BoardImageParser = None
    board_stable_checker: BoardStableChecker = None
    images_manager: ImagesManager = None
    board_ai: BoardAI = None

    game_state: GameState = GameState()

    image_find_results: dict[str, ImageFindResult] = dict()

    # signal to update UI
    update_state = pyqtSignal(str)



class BaseAction(ABC):
    __separator = "  "

    start_time = None

    log_elapsed_time = True

    def __str__(self) -> str:
        out = self.get_description()

        for arg in self.get_arguments():
            out = out + "\n" + self.__separator + arg

        for s in self.get_state() or []:
            out = out + "\n" + self.__separator + s

        return out

    def get_description(self) -> str:
        return self.__class__.__name__

    def get_arguments(self) -> list[str]:
        return []

    def get_state(self) -> list[str]:
        pass

    @abstractmethod
    def run(self, context: ActionRunningContext):
        pass
