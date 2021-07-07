from abc import ABC, abstractmethod
import threading
import copy
import time
from typing import Tuple
import numpy
import cv2
import random
from enum import Enum

from flow.game_state import GameState, MainState, SkillsState
from device import device_controller
from .find_images import ImageFindingSpec, find_image
from .base_action import BaseAction, ActionRunningContext, ImageFindResult
from collections import deque
from log.logger import Logger


class ActionGenerateActionsUntil(BaseAction):
    __action_to_generate: BaseAction = None

    def __init__(self, action_to_generate):
        self.__action_to_generate = action_to_generate

    def get_arguments(self):
        return ["action_to_generate: {0}".format(self.__action_to_generate.get_description())]

    def run(self, context):
        self_action = copy.deepcopy(self)
        self.__action_to_generate.update_caller(self)

        return [self.__action_to_generate, self_action]


class ActionCaptureScreenshot(BaseAction):
    def run(self, context: ActionRunningContext):
        context.device.capture_screenshot()
        context.image_find_results.clear()


class ActionClickPosition(BaseAction):
    pos_x: int
    pos_y: int

    def run(self, context: ActionRunningContext):
        context.device.tap(self.pos_x, self.pos_y)


class ActionRetreat(BaseAction):
    def run(self, context: ActionRunningContext):
        context.logger.log("Retreating")
        context.device.tap(200, 54)
        time.sleep(5)
        context.device.tap(1950, 54)
        time.sleep(5)
        context.device.tap(1418, 778)
        time.sleep(5)


class ActionClickSpells(BaseAction):
    def run(self, context: ActionRunningContext):
        context.logger.log("Clicking skills")

        skills = []
        skills.append((818, 976))
        skills.append((984, 976))
        skills.append((1359, 976))
        skills.append((1516, 976))

        # random.shuffle(skills)
        for skill in skills:
            context.device.tap(skill[0], skill[1])


class ActionDecideAction(BaseAction):
    __always_check_specs: list[str]

    __actions: list[BaseAction] = None

    def __init__(self):
        super().__init__()
        self.__always_check_specs = ["enter_open_pvp",
                                     "enter_pvp_battle",
                                     "exit_battle_result",
                                     "battle_waiting_action",
                                     "all_skills_inactive",
                                     ]

    def run(self, context: ActionRunningContext):
        context.image_find_results = dict()
        for spec in self.__always_check_specs:
            context.image_find_results[spec] = find_image(
                spec, context.device.last_captured_screenshot, context.logger)

        self.__decide(context)
        self.__log_state(context)
        self.__update_ui(context)
        return self.__actions

    def __update_ui(self, context: ActionRunningContext):
        context.update_state.emit(str(context.game_state))

    def __decide(self, context: ActionRunningContext):
        specs = ["enter_open_pvp",
                 "enter_pvp_battle",
                 "exit_battle_result",
                 "battle_waiting_action"
                 ]

        context.game_state.main_state = MainState.UNKNOWN
        context.game_state.skills_state = SkillsState.UNKNOWN
        self.__find_specs(specs, context)

        found_spec = None
        for spec in specs:
            result = context.image_find_results[spec]
            if result.found:
                if found_spec is not None:
                    context.logger.log(
                        "WARNING: cannot determine game state strongly. should be one-of")
                found_spec = spec

        if found_spec is None:
            return

        result = context.image_find_results[found_spec]
        if found_spec == "enter_open_pvp" and result.found:
            context.game_state.main_state = MainState.CHOOSE_PVP
            self.__generate_action_to_click_center_target(result)

        if found_spec == "enter_pvp_battle" and result.found:
            context.game_state.main_state = MainState.ENTER_PVP
            self.__generate_action_to_click_center_target(result)

        if found_spec == "battle_waiting_action" and result.found:
            context.game_state.main_state = MainState.IN_BATTLE
            self.__decide_in_battle_action(context)

        if found_spec == "exit_battle_result" and result.found:
            context.game_state.main_state = MainState.BATTLE_RESULT
            self.__generate_action_to_click_center_target(result)

    def __decide_in_battle_action(self, context: ActionRunningContext):
        spec = "all_skills_inactive"
        self.__find_specs([spec], context)
        if context.image_find_results[spec].found:
            context.game_state.skills_state = SkillsState.ALL_INACTIVE
            self.__actions = [ActionRetreat()]
        else:
            context.game_state.skills_state = SkillsState.OTHERWISE
            self.__actions = [ActionClickSpells()]

    def __find_specs(self, specs, context: ActionRunningContext):
        for spec in specs:
            context.image_find_results[spec] = find_image(
                spec, context.device.last_captured_screenshot, context.logger)

    def __generate_action_to_click_center_target(self, find_result: ImageFindResult):
        action = ActionClickPosition()
        action.pos_x = find_result.pos_x + find_result.target_w/2
        action.pos_y = find_result.pos_y + find_result.target_h/2
        self.__actions = [action]

    def __log_state(self, context: ActionRunningContext):
        context.logger.log(str(context.game_state))


class RootAction(BaseAction):
    def run(self, context: ActionRunningContext) -> list[BaseAction]:
        return [
            ActionCaptureScreenshot(),
            ActionDecideAction()
        ]
