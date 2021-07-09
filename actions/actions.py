from abc import ABC, abstractmethod
from os import wait
import threading
import copy
import time
from typing import Iterable, Tuple
import numpy
import cv2
import random
import enum

from numpy.lib.function_base import diff

from flow.game_state import GameState, MainState, SkillsState
from device import device_controller
from actions.base_action import BaseAction, ActionRunningContext, ImageFindResult
from collections import deque
from log.logger import Logger
from dataset import images_manager
from actions import find_images


class ActionCaptureScreenshot(BaseAction):
    def __init__(self):
        super().__init__()
        self.log_elapsed_time = False

    def run(self, context: ActionRunningContext) -> Iterable[BaseAction]:
        while True:
            context.device.capture_screenshot()
            if context.device.last_captured_screenshot is not None:
                break

            yield None  # call me back later

        context.image_find_results.clear()

    def get_state(self):
        if self.start_time is not None:
            return ["Elapsed {:.1f} seconds...".format(time.time()-self.start_time)]


class ActionClickPosition(BaseAction):
    pos_x: int
    pos_y: int

    def run(self, context: ActionRunningContext) -> Iterable[BaseAction]:
        context.device.tap(self.pos_x, self.pos_y)

        yield from ()


class ActionRetreat(BaseAction):
    def run(self, context: ActionRunningContext) -> Iterable[BaseAction]:
        context.device.tap(200, 54)
        time.sleep(5)
        context.device.tap(1950, 54)
        time.sleep(5)
        context.device.tap(1418, 778)
        time.sleep(5)

        yield from ()


class ActionClickSpells(BaseAction):
    def run(self, context: ActionRunningContext) -> Iterable[BaseAction]:
        skills = []
        skills.append((818, 976))
        skills.append((984, 976))
        skills.append((1359, 976))
        skills.append((1516, 976))

        # random.shuffle(skills)
        for skill in skills:
            context.device.tap(skill[0], skill[1])

        yield from ()


class ActionWaitBoardStable(BaseAction):
    pos_x1 = 730
    pos_y1 = 207
    pos_x2 = 1607
    pos_y2 = 837

    diff_threshold = 10.0
    stable_secs = 2.0

    prev_img = None
    diff_score: float = -1.0
    stable_from_time = None

    class Result(enum.Enum):
        STABLIZED = enum.auto()
        NOT_IN_BATTLE = enum.auto()
    result: Result = None

    def run(self, context: ActionRunningContext):
        while True:
            yield ActionCaptureScreenshot()

            in_battle = find_images.find_image(
                "battle_waiting_action", context.device.last_captured_screenshot, context.logger)
            if not in_battle.found:
                self.result = self.Result.NOT_IN_BATTLE
                return

            img = context.device.last_captured_screenshot
            self.__compute_diff(img)
            if self.diff_score < self.diff_threshold:
                self.stable_from_time = self.stable_from_time or time.time()
            else:
                self.stable_from_time = None

            if self.stable_from_time:
                if time.time()-self.stable_from_time > self.stable_secs:
                    break
            
            self.prev_img = img

        metadata = images_manager.ImageMetadata()
        metadata.categorized_as = "stabled_board"
        context.images_manager.add_img(context.device.last_captured_screenshot, metadata)

        self.result = self.Result.STABLIZED

    def __compute_diff(self, img):
        if self.prev_img is None:
            return
        self.diff_score = find_images.img_diff_score(img, self.prev_img, self.pos_x1, self.pos_y1, self.pos_x2, self.pos_y2)
            

    def get_state(self) -> list[str]:
        state = []
        if self.start_time is not None:
            state.append("Elasped {:.1f} seconds".format(time.time() - self.start_time))
        if self.stable_from_time:
            state.append("Stabled for {:.1f} seconds".format(time.time() - self.stable_from_time))
        if self.diff_score:
            state.append("diff_score: {:.2f}".format(self.diff_score))
        return state


class ActionOpenPvp(BaseAction):
    def run(self, context: ActionRunningContext) -> Iterable[BaseAction]:
        while True:  # until we have a valid action
            has_action = False

            yield ActionCaptureScreenshot()
            for action in self.__decide(context):
                has_action = True
                self.__update_ui(context)
                yield action

            if has_action:
                break

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
            return

        yield from oneofs[found_spec](context.image_find_results[found_spec])

    def __decide_in_battle_action(self, context: ActionRunningContext) -> Iterable[BaseAction]:
        context.game_state.main_state = MainState.IN_BATTLE

        metadata = images_manager.ImageMetadata()
        metadata.categorized_as = "in_battle"
        #context.images_manager.add_img(context.device.last_captured_screenshot, metadata)

        #yield (act := ActionWaitBoardStable())
        #if act.result != ActionWaitBoardStable.Result.STABLIZED:
        #    return

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
            context.image_find_results[spec] = find_images.find_image(
                spec, context.device.last_captured_screenshot, context.logger)

    def __generate_action_to_click_center_target(self, find_result: ImageFindResult) -> Iterable[BaseAction]:
        action = ActionClickPosition()
        action.pos_x = find_result.pos_x + find_result.target_w/2
        action.pos_y = find_result.pos_y + find_result.target_h/2
        return [action]


class ActionOpenPvpForever(BaseAction):
    def run(self, context: ActionRunningContext):
        while True:
            yield ActionOpenPvp()