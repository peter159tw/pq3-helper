from enum import Enum
from typing import Set


class MainState(Enum):
    # next id: 14

    UNKNOWN = 1
    CHOOSE_PVP = 2
    ENTER_PVP = 3
    ENTER_PVP_WITH_TOKEN = 9
    IN_BATTLE = 4
    BATTLE_RESULT = 5
    BATTLE_RESULT_CHEST_ACTION = 13
    BATTLE_RESULT_CHEST_FULL = 12
    BATTLE_DETAIL_VIEW = 6
    RETREAT_CONFIRM = 7
    PVP_FIND_OPPONENT = 8
    CHOOSE_ALTAR = 10
    DUNGEON_MARKS_CONFIRM = 11


class SkillsState(Enum):
    UNKNOWN = 1
    ALL_INACTIVE = 2
    OTHERWISE = 3


class GameState:
    def __init__(self):
        self.main_state = MainState.UNKNOWN
        self.skills_state = SkillsState.UNKNOWN
        self.skill_click_count = 0

    def __str__(self):
        o = "game state: {}\nskill state: {}".format(
            self.main_state, self.skills_state)

        o = o + "\nskill_click_count: {}".format(self.skill_click_count)

        return o
