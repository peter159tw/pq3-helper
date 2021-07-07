from enum import Enum


class MainState(Enum):
    UNKNOWN = 1
    CHOOSE_PVP = 2
    ENTER_PVP = 3
    IN_BATTLE = 4
    BATTLE_RESULT = 5


class SkillsState(Enum):
    UNKNOWN = 1
    ALL_INACTIVE = 2
    OTHERWISE = 3


class GameState:
    main_state: MainState = MainState.UNKNOWN
    skills_state: SkillsState = SkillsState.UNKNOWN

    def __str__(self):
        return "game state: {}\nskill state: {}".format(
            self.main_state, self.skills_state)
