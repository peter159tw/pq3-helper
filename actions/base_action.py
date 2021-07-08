import copy
from typing import Iterable

from PyQt5.QtCore import QObject, pyqtSignal
from abc import ABC, abstractmethod

from actions.find_images import ImageFindResult
from flow.game_state import GameState
from device.device_controller import DeviceController
from log.logger import Logger
from dataset.images_manager import ImagesManager


class ActionRunningContext(QObject):
    device: DeviceController = None
    logger: Logger = None
    images_manager: ImagesManager = None

    game_state: GameState = GameState()

    image_find_results: dict[str, ImageFindResult] = dict()

    # signal to update UI
    update_state = pyqtSignal(str)


class BaseAction(ABC):
    __separator = "  "

    def __str__(self) -> str:
        out = self.get_description()

        for arg in self.get_arguments():
            out = out + "\n" + self.__separator + arg

        if status := self.get_status():
            out = out + "\n" + self.__separator + "status: " + status

        return out

    def get_description(self) -> str:
        return self.__class__.__name__

    def get_arguments(self) -> list[str]:
        return []

    def get_status(self) -> str:
        pass

    @abstractmethod
    def run(self, context: ActionRunningContext):
        pass
