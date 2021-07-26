from flow.game_state import Skill, SkillState, SkillsState
from actions.base_action import ActionRunningContext
import enum
from typing import List
from board import ai


class Decision:
    def __init__(self) -> None:
        self.skill : Skill = None
        self.move_grids : List = None

    def no_action():
        return Decision()

    def move_grids(result: ai.Result):
        ret = Decision()
        ret.move_grids = result.steps
        return ret
    
    def click_skill(skill: Skill):
        ret = Decision()
        ret.skill = skill
        return ret


class ChestAction:
    def __init__(self, x, y):
        self._x = x
        self._y = y
    
    def get_pos(self):
        return (self._x, self._y)


class ChestActions(enum.Enum):
    OPEN_WITH_KEY = ChestAction(1390, 466)
    SALVAGE = ChestAction(751, 251)


class Strategy:
    def __init__(self, context : ActionRunningContext) -> None:
        self._context = context
        self._board_ai_result = None
        self._stun_skill = []
        self.chest_action = ChestActions.OPEN_WITH_KEY
        self.chest_action_no_key = ChestActions.SALVAGE

        # Necro
        #self._non_board_changing_skills = [Skill.SKILL_3]
        #self._board_changing_skills = [Skill.SKILL_1, Skill.SKILL_2, Skill.SKILL_4]

        # Shaman
        #self._non_board_changing_skills = [Skill.SKILL_3]
        #self._board_changing_skills = [Skill.SKILL_1, Skill.SKILL_2]
        #self._stun_skill = [Skill.SKILL_4]

        # Assassin
        self._non_board_changing_skills = [Skill.SKILL_2]
        self._board_changing_skills = [Skill.SKILL_1, Skill.SKILL_3]
        self._no_damage_skills = [Skill.SKILL_1]
        self._stun_skill = [Skill.SKILL_4]

    def _get_active_stun_skill(self) -> Skill:
        for skill in self._stun_skill:
            if self._context.game_state.skill_state[skill] == SkillState.OTHERWISE:
                return skill
        return None

    def _get_active_non_board_changing_skill(self) -> Skill:
        for skill in self._non_board_changing_skills:
            if self._context.game_state.skill_state[skill] == SkillState.OTHERWISE:
                return skill
        return None

    def _get_active_no_damage_skill(self) -> Skill:
        for skill in self._no_damage_skills:
            if self._context.game_state.skill_state[skill] == SkillState.OTHERWISE:
                return skill
        return None

    def _all_boarding_changing_skills_active(self):
        for skill in self._board_changing_skills:
            if self._context.game_state.skill_state[skill] == SkillState.INACTIVE:
                return False
        return True

    def _get_active_board_changing_skill(self) -> Skill:
        for skill in self._board_changing_skills:
            if self._context.game_state.skill_state[skill] == SkillState.OTHERWISE:
                return skill
        return None

    def _click_non_stun_skills(self) -> Decision:
        return None

    def _wait_stable_and_move_board(self) -> Decision:
        if not self._context.game_state.board_stabled:
            return Decision.no_action()
        return Decision.move_grids(self._get_board_ai_result())

    def make_decision(self) -> Decision:
        #return self._make_decision_pvp()
        #return self._make_decision_shaman()
        return self._make_decision_assassin()
        #return Decision.no_action()

    def _make_decision_pvp(self) -> Decision:
        for skill in [Skill.SKILL_1, Skill.SKILL_2, Skill.SKILL_3, Skill.SKILL_4]:
            if self._context.game_state.skill_state[skill] == SkillState.OTHERWISE:
                return Decision.click_skill(skill)
        
        if not self._context.game_state.board_stabled:
            return Decision.no_action()
        return Decision.move_grids(self._get_board_ai_result())


    def _make_decision_shaman(self) -> Decision:
        if stun_skill := self._get_active_stun_skill():
            if skill := self._get_active_board_changing_skill():
                return Decision.click_skill(skill)
            if skill := self._get_active_non_board_changing_skill():
                return Decision.click_skill(skill)

            #if self._context.game_state.hp > 0.12:
            if True:
                return Decision.click_skill(stun_skill)
        
        else:
            if skill := self._get_active_non_board_changing_skill():
                return Decision.click_skill(skill)

            if not self._context.game_state.board_stabled:
                return Decision.no_action()

            if self._get_board_ai_result().final_board_has_stun:
                return Decision.move_grids(self._get_board_ai_result())

            if skill := self._get_active_board_changing_skill():
                return Decision.click_skill(skill)
            
            return Decision.move_grids(self._get_board_ai_result())

    def _make_decision_assassin(self) -> Decision:
        stun_skill = self._get_active_stun_skill()
        if stun_skill is not None:
            if self._context.game_state.hp < 0.2:
                # save stun skill to the next enemy
                if skill := self._get_active_non_board_changing_skill():
                    return Decision.click_skill(skill)
                if skill := self._get_active_board_changing_skill():
                    return Decision.click_skill(skill)
                return self._wait_stable_and_move_board()
            else:
                return Decision.click_skill(stun_skill)

        if self._context.game_state.enemy_status.stunned:
            # enemy is stunned; try kill by moving grids
            if self._context.game_state.hp > 0.6:
                if self._context.game_state.skill_state[Skill.SKILL_ULTIMATE] == SkillState.ULTIMATE_FULL:
                    return Decision.click_skill(Skill.SKILL_ULTIMATE)
            if self._context.game_state.hp > 0.3:
                if skill := self._get_active_non_board_changing_skill():
                    return Decision.click_skill(skill)
                if skill := self._get_active_board_changing_skill():
                    return Decision.click_skill(skill)
            return self._wait_stable_and_move_board()
        
        # no stun skill anymore, and enemy is not stunned.
        if self._context.game_state.hp > 0.6:
            if self._context.game_state.skill_state[Skill.SKILL_ULTIMATE] == SkillState.ULTIMATE_FULL:
                return Decision.click_skill(Skill.SKILL_ULTIMATE)

        if skill := self._get_active_non_board_changing_skill():
            return Decision.click_skill(skill)

        if not self._context.game_state.board_stabled:
            return Decision.no_action()

        if self._get_board_ai_result().final_board_has_stun:
            return Decision.move_grids(self._get_board_ai_result())

        if skill := self._get_active_board_changing_skill():
            return Decision.click_skill(skill)

        if self._context.game_state.skill_state[Skill.SKILL_ULTIMATE] != SkillState.INACTIVE:
            return Decision.click_skill(Skill.SKILL_ULTIMATE)

        return Decision.move_grids(self._get_board_ai_result())

    def _get_skill_count(self):
        return len(self._board_changing_skills) + len(self._non_board_changing_skills)

    def _get_board_ai_result(self):
        if self._board_ai_result is not None:
            return self._board_ai_result

        self._board_ai_result = self._context.board_ai.decide_best_result(self._context.game_state.board)
        return self._board_ai_result

    def _move_grids(self) -> Decision:
        decision = Decision()
        decision.move_grids = self._get_board_ai_result(context).steps
        return decision