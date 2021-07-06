import threading
import copy
import time
import device_controller
import numpy
import cv2
import random
from .find_images import ImageFindingSpec, find_image
from .base_action import BaseAction, ActionRunningContext, ImageFindResult
from collections import deque
from logger import Logger
from abc import ABC, abstractmethod


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


class ActionFindImages(BaseAction):
    specs: list[ImageFindingSpec]

    def __init__(self, specs):
        super().__init__()
        self.specs = specs

    def get_arguments(self) -> list[str]:
        spec_targets = []
        for spec in self.specs:
            spec_targets.append(spec.target)
        return ["specs: {0}".format(','.join(spec_targets))]

    def run(self, context: ActionRunningContext):
        context.image_find_results = dict()
        for spec in self.specs:
            context.image_find_results[spec.target] = find_image(
                spec, context.device.last_captured_screenshot, context.logger)


class ActionClickFoundPosition(BaseAction):
    def run(self, context: ActionRunningContext):
        if not context.image_find_results:
            return

        if context.image_find_results["battle_waiting_action"].pos_x and context.image_find_results["all_skills_inactive"].pos_x:
            context.logger.log("Retreating")
            context.device.tap(200, 54)
            time.sleep(5)
            context.device.tap(1950, 54)
            time.sleep(5)
            context.device.tap(1418, 778)
            time.sleep(5)
            return

        for (spec_name, spec_result) in context.image_find_results.items():
            if not spec_result.pos_x:
                continue

            if spec_name == "enter_open_pvp" or spec_name == "enter_pvp_battle" or spec_name == "exit_battle_result":
                context.logger.log(
                    "Clicking spec '{0}'. pos: {1},{2}".format(spec_name, spec_result.pos_x, spec_result.pos_y))
                context.device.tap(spec_result.pos_x, spec_result.pos_y)
            elif spec_name == "battle_waiting_action":
                context.logger.log("Clicking skills")

                skills = []
                skills.append((818, 976))
                skills.append((984, 976))
                skills.append((1359, 976))
                skills.append((1516, 976))

                # random.shuffle(skills)
                for skill in skills:
                    context.device.tap(skill[0], skill[1])
            else:
                context.logger.log("no action for spec: " + spec_name)


class RootAction(BaseAction):
    def run(self, context: ActionRunningContext) -> list[BaseAction]:
        enter_open_pvp_spec = ImageFindingSpec()
        enter_open_pvp_spec.target = "enter_open_pvp"
        enter_open_pvp_spec.threshold = 0.04
        enter_open_pvp_spec.expect_pos_x = 1279
        enter_open_pvp_spec.expect_pos_y = 141

        enter_pvp_battle = ImageFindingSpec()
        enter_pvp_battle.target = "enter_pvp_battle"
        enter_pvp_battle.threshold = 0.06
        enter_pvp_battle.expect_pos_x = 1881
        enter_pvp_battle.expect_pos_y = 974

        exit_battle_result = ImageFindingSpec()
        exit_battle_result.target = "exit_battle_result"
        exit_battle_result.threshold = 0.1
        exit_battle_result.expect_pos_x = 1880
        exit_battle_result.expect_pos_y = 971

        battle_waiting_action = ImageFindingSpec()
        battle_waiting_action.target = "battle_waiting_action"
        battle_waiting_action.threshold = 0.04
        battle_waiting_action.expect_pos_x = 775
        battle_waiting_action.expect_pos_y = 133

        all_skills_inactive = ImageFindingSpec()
        all_skills_inactive.target = "all_skills_inactive"
        all_skills_inactive.threshold = 0.04
        all_skills_inactive.expect_pos_x = 760
        all_skills_inactive.expect_pos_y = 928

        return [
            ActionCaptureScreenshot(),
            ActionFindImages([enter_open_pvp_spec, enter_pvp_battle,
                             exit_battle_result, battle_waiting_action, all_skills_inactive]),
            ActionClickFoundPosition()
        ]
