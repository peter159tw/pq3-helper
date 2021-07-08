from abc import ABC, abstractmethod
import threading
import copy
import time
from typing import Iterable, Tuple
import numpy
import cv2
import random
from enum import Enum

from flow.game_state import GameState, MainState, SkillsState
from device import device_controller
from actions.find_images import ImageFindingSpec, find_image
from actions.base_action import BaseAction, ActionRunningContext, ImageFindResult
from collections import deque
from log.logger import Logger
from dataset import images_manager


class ActionGenerateActionsUntil(BaseAction):
    __action_to_generate: BaseAction = None

    def __init__(self, action_to_generate):
        self.__action_to_generate = action_to_generate

    def get_arguments(self):
        return ["action_to_generate: {0}".format(self.__action_to_generate.get_description())]

    def run(self, context) -> Iterable[BaseAction]:
        while True:
            yield self.__action_to_generate


class ActionCaptureScreenshot(BaseAction):
    __start_time = None

    def run(self, context: ActionRunningContext) -> Iterable[BaseAction]:
        self.__start_time = time.time()
        while True:
            context.device.capture_screenshot()
            if context.device.last_captured_screenshot is not None:
                break

            yield None  # call me back later

        context.image_find_results.clear()

    def get_status(self) -> str:
        if self.__start_time is None:
            return "not started yet"

        return "elapsed {:.1f} seconds...".format(time.time()-self.__start_time)


class ActionClickPosition(BaseAction):
    pos_x: int
    pos_y: int

    def run(self, context: ActionRunningContext) -> Iterable[BaseAction]:
        context.device.tap(self.pos_x, self.pos_y)

        yield from ()



class ActionRetreat(BaseAction):
    def run(self, context: ActionRunningContext) -> Iterable[BaseAction]:
        context.logger.log("Retreating")
        context.device.tap(200, 54)
        time.sleep(5)
        context.device.tap(1950, 54)
        time.sleep(5)
        context.device.tap(1418, 778)
        time.sleep(5)

        yield from ()


class ActionClickSpells(BaseAction):
    def run(self, context: ActionRunningContext) -> Iterable[BaseAction]:
        context.logger.log("Clicking skills")

        skills = []
        skills.append((818, 976))
        skills.append((984, 976))
        skills.append((1359, 976))
        skills.append((1516, 976))

        # random.shuffle(skills)
        for skill in skills:
            context.device.tap(skill[0], skill[1])

        yield from ()


class ActionOpenPvp(BaseAction):
    def run(self, context: ActionRunningContext) -> Iterable[BaseAction]:
        yield ActionCaptureScreenshot()
        if context.device.last_captured_screenshot is None:
            return

        for action in self.__decide(context):
            self.__update_ui(context)
            yield action

    def __update_ui(self, context: ActionRunningContext):
        context.update_state.emit(str(context.game_state))

    def __decide(self, context: ActionRunningContext) -> Iterable[BaseAction]:
        oneofs = dict()

        def enter_open_pvp(result: ImageFindResult):
            context.game_state.main_state = MainState.CHOOSE_PVP
            return self.__generate_action_to_click_center_target(result)
        oneofs["enter_open_pvp"] = enter_open_pvp

        def enter_pvp_battle(result: ImageFindResult):
            context.game_state.main_state = MainState.ENTER_PVP
            return self.__generate_action_to_click_center_target(result)
        oneofs["enter_pvp_battle"] = enter_pvp_battle

        oneofs["battle_waiting_action"] = lambda result: self.__decide_in_battle_action(context)

        def exit_battle_result(result: ImageFindResult):
            context.game_state.main_state = MainState.BATTLE_RESULT
            return self.__generate_action_to_click_center_target(result)
        oneofs["exit_battle_result"] = exit_battle_result

        context.game_state.main_state = MainState.UNKNOWN
        context.game_state.skills_state = SkillsState.UNKNOWN
        self.__find_specs(oneofs.keys(), context)

        found_spec = None
        for spec in oneofs.keys():
            result = context.image_find_results[spec]
            if result.found:
                if found_spec is not None:
                    context.logger.log(
                        "WARNING: cannot determine game state strongly. should be one-of")
                found_spec = spec

        if found_spec is None:
            yield from ()
            return

        yield from oneofs[found_spec](context.image_find_results[found_spec])

    def __decide_in_battle_action(self, context: ActionRunningContext) -> Iterable[BaseAction]:
        context.game_state.main_state = MainState.IN_BATTLE

        metadata = images_manager.ImageMetadata()
        metadata.categorized_as = "in_battle"
        #context.images_manager.add_img(context.device.last_captured_screenshot, metadata)

        spec = "all_skills_inactive"
        self.__find_specs([spec], context)
        if context.image_find_results[spec].found:
            context.game_state.skills_state = SkillsState.ALL_INACTIVE
            yield ActionRetreat()
        else:
            context.game_state.skills_state = SkillsState.OTHERWISE
            yield ActionClickSpells()

    def __find_specs(self, specs, context: ActionRunningContext):
        for spec in specs:
            context.image_find_results[spec] = find_image(
                spec, context.device.last_captured_screenshot, context.logger)

    def __generate_action_to_click_center_target(self, find_result: ImageFindResult) -> Iterable[BaseAction]:
        action = ActionClickPosition()
        action.pos_x = find_result.pos_x + find_result.target_w/2
        action.pos_y = find_result.pos_y + find_result.target_h/2
        return [action]