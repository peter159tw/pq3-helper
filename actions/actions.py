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

from flow.game_state import GameState, MainState, Skill, SkillState, SkillsState
from device import device_controller
from actions.base_action import BaseAction, ActionRunningContext, ImageFindResult
from collections import deque
from log.logger import Logger
from dataset import images_manager
from actions import find_images
from board.ai import BoardAI
from board import board_image_parser
from board.board import Board
from actions import strategy

class ActionCaptureScreenshot(BaseAction):
    def __init__(self):
        super().__init__()
        self.log_elapsed_time = True

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

    def __init__(self, x, y):
        super().__init__()
        self.pos_x = x
        self.pos_y = y

    def run(self, context: ActionRunningContext) -> Iterable[BaseAction]:
        print("tapping {},{}".format(self.pos_x, self.pos_y))
        context.device.tap(self.pos_x, self.pos_y)
        yield from ()


class ActionRetreat(BaseAction):
    def run(self, context: ActionRunningContext) -> Iterable[BaseAction]:
        context.device.tap(200, 54)
        time.sleep(1)  # allow game to switch window
        yield from ()



class ActionClickSpells(BaseAction):
    # click all spells until they're all inactive

    def __init__(self, skill: strategy.Skill):
        self._skill = skill

    def run(self, context: ActionRunningContext) -> Iterable[BaseAction]:
        context.device.tap(*self._skill._get_pos())
        yield from ()


class ActionMoveGrids(BaseAction):
    def __init__(self, steps):
        self.__steps = steps

    def run(self, context: ActionRunningContext) -> Iterable[BaseAction]:
        for (x1, y1, x2, y2) in self.__steps:
            context.device.drag(
                *board_image_parser.get_grid_center(x1,y1),
                *board_image_parser.get_grid_center(x2,y2)
            )
            time.sleep(0.3)

        yield from ()



class ActionParseGameState(BaseAction):
    def run(self, context: ActionRunningContext) -> Iterable[BaseAction]:
        yield ActionCaptureScreenshot()
        yield from self.__parse(context)
        self.__update_ui(context)

    def __update_ui(self, context: ActionRunningContext):
        context.update_state.emit(str(context.game_state))

    def __parse(self, context: ActionRunningContext) -> Iterable[BaseAction]:
        oneofs = dict()
        oneofs["enter_open_pvp"] = lambda : self.__set_game_main_state(context, MainState.CHOOSE_PVP)
        oneofs["enter_pvp_battle"] = lambda: self.__set_game_main_state(context, MainState.ENTER_PVP)
        oneofs["enter_pvp_battle_with_token"] = lambda: self.__set_game_main_state(context, MainState.ENTER_PVP_WITH_TOKEN)
        oneofs["battle_waiting_action"] = lambda: self.__parse_in_battle(context)
        oneofs["exit_battle_result"] = lambda: self.__parse_battle_result(context)
        oneofs["retreat_in_battle_detail_view"] = lambda: self.__set_game_main_state(context, MainState.BATTLE_DETAIL_VIEW)
        oneofs["retreat_confirm"] = lambda: self.__set_game_main_state(context, MainState.RETREAT_CONFIRM)
        oneofs["find_opponent"] = lambda: self.__set_game_main_state(context, MainState.PVP_FIND_OPPONENT)
        oneofs["choose_altar"] = lambda: self.__set_game_main_state(context, MainState.CHOOSE_ALTAR)
        oneofs["rest_and_recover"] = lambda: self.__set_game_main_state(context, MainState.REST_AND_RECOVER)
        oneofs["dungeon_marks_confirm"] = lambda: self.__set_game_main_state(context, MainState.DUNGEON_MARKS_CONFIRM)
        oneofs["battle_result_chest_full"] = lambda: self.__set_game_main_state(context, MainState.BATTLE_RESULT_CHEST_FULL)
        oneofs["revive_window"] = lambda: self.__set_game_main_state(context, MainState.REVIVE_WINDOW)
        oneofs["dungeon_battle"] = lambda: self.__set_game_main_state(context, MainState.QUEST_BATTLE)
        oneofs["quest_battle"] = lambda: self.__set_game_main_state(context, MainState.QUEST_BATTLE)
        oneofs["quest_begin"] = lambda: self.__set_game_main_state(context, MainState.QUEST_BEGIN)
        oneofs["quest_collect"] = lambda: self.__set_game_main_state(context, MainState.QUEST_COLLECT)
        oneofs["quest_skip"] = lambda: self.__set_game_main_state(context, MainState.QUEST_SKIP)
        oneofs["quest_talk"] = lambda: self.__set_game_main_state(context, MainState.QUEST_TALK)
        oneofs["side_quest_battle"] = lambda: self.__set_game_main_state(context, MainState.SIDE_QUEST_BATTLE)
        oneofs["side_quest_begin"] = lambda: self.__set_game_main_state(context, MainState.SIDE_QUEST_BEGIN)
        oneofs["side_quest_collect"] = lambda: self.__set_game_main_state(context, MainState.SIDE_QUEST_COLLECT)
        oneofs["challenge_start_dungeon"] = lambda: self.__set_game_main_state(context, MainState.CHALLENGE_START_DUNGEON)
        oneofs["challenge_start_skirmish"] = lambda: self.__set_game_main_state(context, MainState.CHALLENGE_START_SKIRMISH)

        start_time = time.time()
        self.__find_specs(oneofs.keys(), context)

        found_spec = None
        for spec in oneofs.keys():
            result = context.image_find_results[spec]
            if result.found:
                if found_spec is not None:
                    context.logger.log(
                        "WARNING: cannot determine game state strongly. should be one-of")
                found_spec = spec
        context.logger.log("find spec takes {:.1f} seconds".format(time.time()-start_time))

        context.game_state.main_state = MainState.UNKNOWN
        context.game_state.skills_state = SkillsState.UNKNOWN
        if found_spec is not None:
            yield from oneofs[found_spec]()

    def __set_game_main_state(self, context: ActionRunningContext, state) -> Iterable[BaseAction]:
        context.game_state.main_state = state
        yield from ()


    def __parse_in_battle(self, context: ActionRunningContext) -> Iterable[BaseAction]:
        context.game_state.main_state = MainState.IN_BATTLE

        context.game_state.board_stabled = context.board_stable_checker.is_stable(context)

        skill_map = {
            "skill_1_inactive": Skill.SKILL_1,
            "skill_2_inactive": Skill.SKILL_2,
            "skill_3_inactive": Skill.SKILL_3,
            "skill_4_inactive": Skill.SKILL_4,
        }
        specs = ["all_skills_inactive"] + list(skill_map.keys())
        specs = specs + ["ultimate_skill_inactive", "ultimate_skill_full"]

        self.__find_specs(specs, context)
        if context.image_find_results["all_skills_inactive"].found:
            context.game_state.skills_state = SkillsState.ALL_INACTIVE
        else:
            context.game_state.skills_state = SkillsState.OTHERWISE

        for spec_name, skill in skill_map.items():
            if context.image_find_results[spec_name].found:
                context.game_state.skill_state[skill] = SkillState.INACTIVE
            else:
                context.game_state.skill_state[skill] = SkillState.OTHERWISE

        if context.image_find_results["ultimate_skill_full"].found:
            context.game_state.skill_state[Skill.SKILL_ULTIMATE] = SkillState.ULTIMATE_FULL
        elif context.image_find_results["ultimate_skill_inactive"].found:
            context.game_state.skill_state[Skill.SKILL_ULTIMATE] = SkillState.INACTIVE
        else:
            context.game_state.skill_state[Skill.SKILL_ULTIMATE] = SkillState.OTHERWISE

        self.__find_specs(["enemy_status_stunned"], context)
        context.game_state.enemy_status.stunned = context.image_find_results["enemy_status_stunned"].found

        yield from ()

    def __parse_battle_result(self, context: ActionRunningContext) -> Iterable[BaseAction]:
        specs = ["battle_result_chest_action","battle_result_chest_action_no_key"]
        self.__find_specs(specs, context)
        if context.image_find_results["battle_result_chest_action_no_key"].found:
            context.game_state.main_state = MainState.BATTLE_RESULT_CHEST_ACTION_NO_KEY
        elif context.image_find_results["battle_result_chest_action"].found:
            context.game_state.main_state = MainState.BATTLE_RESULT_CHEST_ACTION
        else:
            context.game_state.main_state = MainState.BATTLE_RESULT

        yield from ()

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
            context.game_state.skill_click_count = 0
            time.sleep(0.5)  # allow game to switch view
        if context.game_state.main_state == MainState.ENTER_PVP_WITH_TOKEN:
            yield from self.__generate_action_to_click_center_target(context, "enter_pvp_battle_with_token")
            context.game_state.skill_click_count = 0
            time.sleep(0.5)  # allow game to switch view
        
        if context.game_state.main_state == MainState.IN_BATTLE:
            yield from self.__decide_in_battle(context)

        if context.game_state.main_state == MainState.BATTLE_RESULT:
            yield ActionClickPosition(2041,1027)
            time.sleep(0.5)  # allow game to switch view

        if context.game_state.main_state == MainState.BATTLE_RESULT_CHEST_ACTION:
            metadata = images_manager.ImageMetadata()
            metadata.categorized_as = "chest_action"
            #context.images_manager.add_img(context.device.last_captured_screenshot, metadata)

            chest_action = strategy.Strategy(context).chest_action
            if chest_action != None:
                yield ActionClickPosition(*chest_action.value.get_pos())
                time.sleep(0.5)

        if context.game_state.main_state == MainState.BATTLE_RESULT_CHEST_ACTION_NO_KEY:
            chest_action = strategy.Strategy(context).chest_action_no_key
            if chest_action != None:
                yield ActionClickPosition(*chest_action.value.get_pos())
                time.sleep(0.5)

        
        if context.game_state.main_state == MainState.BATTLE_RESULT_CHEST_FULL:
            yield from self.__generate_action_to_click_center_target(context, "battle_result_chest_full")
            time.sleep(0.5)
        
        if context.game_state.main_state == MainState.BATTLE_DETAIL_VIEW:
            yield from self.__generate_action_to_click_center_target(context, "retreat_in_battle_detail_view")
            time.sleep(0.5)  # allow game to switch view
        
        if context.game_state.main_state == MainState.RETREAT_CONFIRM:
            yield from self.__generate_action_to_click_center_target(context, "retreat_confirm")
            time.sleep(0.5)  # allow game to switch view

        if context.game_state.main_state == MainState.PVP_FIND_OPPONENT:
            yield from self.__generate_action_to_click_center_target(context, "find_opponent")
            time.sleep(0.5)  # allow game to switch view

        if context.game_state.main_state == MainState.CHOOSE_ALTAR:
            yield from self.__generate_action_to_click_center_target(context, "choose_altar")
            time.sleep(0.5)

        if context.game_state.main_state == MainState.REST_AND_RECOVER:
            yield ActionClickPosition(1165, 862)
            time.sleep(0.5)

        if context.game_state.main_state == MainState.DUNGEON_MARKS_CONFIRM:
            yield from self.__generate_action_to_click_center_target(context, "dungeon_marks_confirm")
            time.sleep(0.5)

        if context.game_state.main_state == MainState.REVIVE_WINDOW:
            yield ActionClickPosition(1532, 129)
            time.sleep(0.5)

        if context.game_state.main_state == MainState.QUEST_BEGIN:
            yield ActionClickPosition(1992, 1016)
            time.sleep(0.5)

        if context.game_state.main_state == MainState.QUEST_BATTLE:
            yield ActionClickPosition(1996, 1016)
            time.sleep(0.5)

        if context.game_state.main_state == MainState.QUEST_TALK:
            yield ActionClickPosition(1985,1020)
            time.sleep(0.5)

        if context.game_state.main_state == MainState.QUEST_SKIP:
            yield ActionClickPosition(2062,77)
            time.sleep(0.5)

        if context.game_state.main_state == MainState.SIDE_QUEST_BATTLE:
            yield ActionClickPosition(1996, 1016)
            time.sleep(0.5)

        if context.game_state.main_state == MainState.SIDE_QUEST_BEGIN:
            yield ActionClickPosition(1992, 1016)
            time.sleep(0.5)

        if context.game_state.main_state == MainState.SIDE_QUEST_COLLECT:
            yield ActionClickPosition(1996, 1016)
            time.sleep(0.5)

        if context.game_state.main_state == MainState.DUNGEON_BATTLE:
            yield ActionClickPosition(1865, 1011)
            time.sleep(0.5)

        if context.game_state.main_state == MainState.CHALLENGE_START_DUNGEON:
            yield ActionClickPosition(1162,968)
            time.sleep(0.5)

        if context.game_state.main_state == MainState.CHALLENGE_START_SKIRMISH:
            yield ActionClickPosition(1162,968)
            time.sleep(0.5)

    def __decide_in_battle(self, context: ActionRunningContext):
        context.game_state.hp = board_image_parser.HpParser().parse(context.device.last_captured_screenshot)
        context.update_state.emit(str(context.game_state))

        decision = strategy.Strategy(context).make_decision()

        if decision.skill is not None:
            yield ActionClickSpells(decision.skill)
            context.game_state.skill_click_count += 1
            context.board_stable_checker.reset()
            time.sleep(2)
        elif decision.move_grids is not None:
            yield ActionMoveGrids(decision.move_grids)
            context.game_state.skill_click_count = 0
            context.board_stable_checker.reset()
            time.sleep(2)

    def __generate_action_to_click_center_target(self, context: ActionRunningContext, spec_name: str) -> Iterable[BaseAction]:
        find_result = context.image_find_results[spec_name]
        yield ActionClickPosition(find_result.pos_x + find_result.target_w/2,
            find_result.pos_y + find_result.target_h/2)


class ActionOpenPvpForever(BaseAction):
    def run(self, context: ActionRunningContext):
        while True:
            yield ActionOpenPvp()