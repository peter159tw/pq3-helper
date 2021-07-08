from typing import Deque, Iterable, List
from actions.base_action import ActionRunningContext, BaseAction
import threading
import time
import copy

from collections import deque
from abc import ABC, abstractmethod
from PyQt5 import QtCore
from PyQt5.QtCore import QObject, QRunnable, QThread, QThreadPool

from actions import actions
from log.logger import Logger
from device.device_controller import DeviceController
from dataset.images_manager import ImagesManager


class ActionEntry:
    action: BaseAction = None
    state: Iterable[BaseAction] = None

    def __init__(self, action: BaseAction):
        super().__init__()
        self.action = action

    def step(self, list: deque, context: ActionRunningContext):
        if self.state is None:
            self.state = self.action.run(context)

        try:
            new_action = next(self.state)
        except StopIteration:
            return

        list.appendleft(self)
        if new_action is not None:
            list.appendleft(ActionEntry(new_action))


class FlowController(QObject):
    __enabled = False
    __enabled_lock = threading.Lock()

    __action_context: actions.ActionRunningContext = actions.ActionRunningContext()

    __actions: Deque = deque()

    device: DeviceController = DeviceController()
    logger: Logger = Logger()

    images_manager: ImagesManager = ImagesManager()

    # signal to update UI
    update_actions = QtCore.pyqtSignal(list)

    def __init__(self):
        super().__init__()
        self.__actions.appendleft(ActionEntry(actions.ActionGenerateActionsUntil(
            actions.ActionOpenPvp()
        )))

    def connect_ui(self, update_actions, update_state, update_screenshot, append_log):
        self.update_actions.connect(update_actions)
        self.__action_context.update_state.connect(update_state)
        self.device.update_screenshot.connect(update_screenshot)
        self.logger.append_log.connect(append_log)

    def is_enabled(self):
        with self.__enabled_lock:
            return self.__enabled

    def enable(self, enabled=True):
        with self.__enabled_lock:
            self.__enabled = enabled

    def tick(self):
        if self.is_enabled():
            self.__action_context.device = self.device
            self.__action_context.logger = self.logger
            self.__action_context.images_manager = self.images_manager

            next_action = self.__actions.popleft()
            next_action.step(self.__actions, self.__action_context)

        self.update_ui()

    def update_ui(self):
        readable_actions = []
        for entry in self.__actions:
            readable_actions.append(str(entry.action))
            pass

        self.update_actions.emit(readable_actions)


class FlowRunner(QRunnable):
    flow = FlowController()

    def run(self):
        QThreadPool.globalInstance().start(self.flow.device.minicap_client)

        while (True):
            self.flow.tick()
            time.sleep(0.01)  # avoid busy loop
