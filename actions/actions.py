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
        #self.log_elapsed_time = False

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
        time.sleep(1)  # allow game to switch window
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


class ActionParseGameState(BaseAction):
    def run(self, context: ActionRunningContext) -> Iterable[BaseAction]:
        yield ActionCaptureScreenshot()
        self.__parse(context)
        self.__update_ui(context)

    def __update_ui(self, context: ActionRunningContext):
        context.update_state.emit(str(context.game_state))

    def __parse(self, context: ActionRunningContext):
        oneofs = dict()
        oneofs["enter_open_pvp"] = lambda : self.__set_game_main_state(context, MainState.CHOOSE_PVP)
        oneofs["enter_pvp_battle"] = lambda: self.__set_game_main_state(context, MainState.ENTER_PVP)
        oneofs["battle_waiting_action"] = lambda: self.__parse_in_battle(context)
        oneofs["exit_battle_result"] = lambda: self.__set_game_main_state(context, MainState.BATTLE_RESULT)
        oneofs["retreat_in_battle_detail_view"] = lambda: self.__set_game_main_state(context, MainState.BATTLE_DETAIL_VIEW)
        oneofs["retreat_confirm"] = lambda: self.__set_game_main_state(context, MainState.RETREAT_CONFIRM)

        self.__find_specs(oneofs.keys(), context)

        found_spec = None
        for spec in oneofs.keys():
            result = context.image_find_results[spec]
            if result.found:
                if found_spec is not None:
                    context.logger.log(
                        "WARNING: cannot determine game state strongly. should be one-of")
                found_spec = spec

        context.game_state.main_state = MainState.UNKNOWN
        context.game_state.skills_state = SkillsState.UNKNOWN
        if found_spec is not None:
            oneofs[found_spec]()

    def __set_game_main_state(self, context: ActionRunningContext, state):
        context.game_state.main_state = state


    def __parse_in_battle(self, context: ActionRunningContext):
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
        else:
            context.game_state.skills_state = SkillsState.OTHERWISE

    def __find_specs(self, specs, context: ActionRunningContext):
        for spec in specs:
            context.image_find_results[spec] = find_images.find_image(
                spec, context.device.last_captured_screenshot, context.logger)


class ActionOpenPvp(BaseAction):
    def run(self, context: ActionRunningContext) -> Iterable[BaseAction]:
        while True:  # until we have a valid action, to have a meaninful logging on how long an open-pvp run is finished
            has_action = False

            yield ActionParseGameState()
            for action in self.__decide(context):
                has_action = True
                yield action

            if has_action:
                break

    def __decide(self, context: ActionRunningContext) -> Iterable[BaseAction]:
        if context.game_state.main_state == MainState.CHOOSE_PVP:
            yield from self.__generate_action_to_click_center_target(context, "enter_open_pvp")
            time.sleep(0.5)  # allow game to switch view
        
        if context.game_state.main_state == MainState.ENTER_PVP:
            yield from self.__generate_action_to_click_center_target(context, "enter_pvp_battle")
            time.sleep(0.5)  # allow game to switch view
        
        if context.game_state.main_state == MainState.IN_BATTLE:
            if context.game_state.skills_state == SkillsState.ALL_INACTIVE:
                yield ActionRetreat()
                time.sleep(0.5)  # allow game to switch view
            else:
                yield ActionClickSpells()
                time.sleep(0.5)  # allow game to switch view

        if context.game_state.main_state == MainState.BATTLE_RESULT:
            yield from self.__generate_action_to_click_center_target(context, "exit_battle_result")
            time.sleep(0.5)  # allow game to switch view
        
        if context.game_state.main_state == MainState.BATTLE_DETAIL_VIEW:
            yield from self.__generate_action_to_click_center_target(context, "retreat_in_battle_detail_view")
            time.sleep(0.5)  # allow game to switch view
        
        if context.game_state.main_state == MainState.RETREAT_CONFIRM:
            yield from self.__generate_action_to_click_center_target(context, "retreat_confirm")
            time.sleep(0.5)  # allow game to switch view

    def __generate_action_to_click_center_target(self, context: ActionRunningContext, spec_name: str) -> Iterable[BaseAction]:
        find_result = context.image_find_results[spec_name]
        action = ActionClickPosition()
        action.pos_x = find_result.pos_x + find_result.target_w/2
        action.pos_y = find_result.pos_y + find_result.target_h/2
        yield action


class ActionOpenPvpForever(BaseAction):
    def run(self, context: ActionRunningContext):
        while True:
            yield ActionOpenPvp()