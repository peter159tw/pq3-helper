import threading
import time
import copy

from collections import deque
from actions import actions
from logger import Logger
from abc import ABC, abstractmethod
from PyQt5 import QtCore
from device_controller import DeviceController

from PyQt5.QtCore import QObject, QRunnable, QThread


class ActionList:
  # thread safe

    __actions = deque()

    def push_front(self, actions: list[actions.BaseAction]):
        if actions:
            for action in reversed(actions):
                self.__actions.appendleft(action)

    def pop_front(self) -> actions.BaseAction:
        if (not self.__actions):
            return None

        return self.__actions.popleft()

    def get_actions(self) -> list[actions.BaseAction]:
        return copy.deepcopy(self.__actions)


class FlowController(QObject):
    __enabled = False
    __enabled_lock = threading.Lock()

    __action_context: actions.ActionRunningContext = actions.ActionRunningContext()

    actions = ActionList()
    device: DeviceController
    logger: Logger

    # signal to update UI
    update_actions = QtCore.pyqtSignal(object)

    def is_enabled(self):
        with self.__enabled_lock:
            return self.__enabled

    def enable(self, enabled=True):
        with self.__enabled_lock:
            self.__enabled = enabled

    def tick(self):
        if self.is_enabled():
            next_action = self.actions.pop_front()

            self.__action_context.device = self.device
            self.__action_context.logger = self.logger
            if next_action:
                self.actions.push_front(next_action.run(self.__action_context))

        self.update_ui()

    def update_ui(self):
        readable_actions = []
        for action in self.actions.get_actions():
            readable_actions.append(action.get_status())
            pass

        self.update_actions.emit(readable_actions)


class FlowRunner(QRunnable):
    flow = FlowController()

    def run(self):
        while (True):
            self.flow.tick()
            time.sleep(0.01)  # avoid busy loop
