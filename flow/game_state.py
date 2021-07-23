from board.board import Board
from enum import Enum
from typing import Dict, Set


class MainState(Enum):
    # next id: 25

    UNKNOWN = 1
    CHOOSE_PVP = 2
    ENTER_PVP = 3
    ENTER_PVP_WITH_TOKEN = 9
    IN_BATTLE = 4
    BATTLE_RESULT = 5
    BATTLE_RESULT_CHEST_ACTION = 13
    BATTLE_RESULT_CHEST_ACTION_NO_KEY = 24
    BATTLE_RESULT_CHEST_FULL = 12
    BATTLE_DETAIL_VIEW = 6
    RETREAT_CONFIRM = 7
    PVP_FIND_OPPONENT = 8
    CHOOSE_ALTAR = 10
    DUNGEON_MARKS_CONFIRM = 11
    REVIVE_WINDOW = 14
    QUEST_BATTLE = 15
    QUEST_BEGIN = 16
    QUEST_COLLECT = 17
    QUEST_SKIP = 18
    QUEST_TALK = 19
    SIDE_QUEST_BATTLE = 20
    SIDE_QUEST_COLLECT = 21
    SIDE_QUEST_BEGIN = 22
    DUNGEON_BATTLE = 23

class Skill(Enum):
    SKILL_1 = 0
    SKILL_2 = 1
    SKILL_3 = 2
    SKILL_4 = 3
    SKILL_ULTIMATE = 4

    def _get_pos(self):
        pos = [
            (818, 976),
            (984, 976),
            (1359, 976),
            (1516, 976),
            (1171, 962),  # ultimate
        ]
        return pos[self.value]


class SkillsState(Enum):
    UNKNOWN = 1
    ALL_INACTIVE = 2
    OTHERWISE = 3

class SkillState(Enum):
    INACTIVE = 1
    OTHERWISE = 2


class GameState:
    def __init__(self):
        self.main_state = MainState.UNKNOWN
        self.skills_state = SkillsState.UNKNOWN
        self.skill_state : Dict[Skill, SkillState] = dict()
        self.skill_click_count = 0
        self.board : Board = None
        self.board_stabled : bool = False
        self.hp : float = 0.0

    def __str__(self):
        o = "game state: {}"
        
        o = o + "\nskills state: {}".format(
            self.main_state, self.skills_state)

        o = o + "\nskill state: "
        for item in self.skill_state.items():
            o = o + "\n  " + str(item)

        o = o + "\nskill_click_count: {}".format(self.skill_click_count)

        o = o + "\nHP: {:.3f}".format(self.hp)

        if self.board is not None:
            o = o + "\nBoard:\n{}".format(str(self.board))

        o = o + "\nBoard stabled? " + str(self.board_stabled)

        return o
