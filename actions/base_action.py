import copy

from .find_images import ImageFindResult
from device_controller import DeviceController
from logger import Logger
from abc import ABC, abstractmethod



class ActionRunningContext:
    device: DeviceController = None
    logger: Logger = None
    
    image_find_results: dict[str, ImageFindResult] = dict()


class BaseAction(ABC):
    __separator = "  "

    callers = []

    def get_status(self) -> str:
        out = self.get_description()

        for arg in self.get_arguments():
            out = out + "\n" + self.__separator + arg

        out = out + "\n" + self.__separator + \
            "call path: " + '->'.join(self.callers)

        return out

    def get_description(self) -> str:
        return self.__class__.__name__

    def get_arguments(self) -> list[str]:
        return []

    # Return a list of actions which will be pushed to the front of the action list
    @abstractmethod
    def run(self, context: ActionRunningContext):
        pass

    def update_caller(self, parent):
        self.callers = []
        if parent.callers:
            self.callers = copy.deepcopy(parent.callers)
        self.callers.append(parent.__class__.__name__)
