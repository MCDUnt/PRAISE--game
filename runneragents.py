import random
from agents import Agent
from environment import SimulatedSensor, SimulatedActuator, SimulatedEnvironment
from runnerworld import RunnerChaseEnvironment, Role, ObstacleType, CORRECT_ACTION

class PositionSensor(SimulatedSensor):
    def sense(self):
        r = self._env.get_property(self._agent_id, "position")
        return r.get("position", 0)

class NextObstacleSensor(SimulatedSensor):
    def sense(self):
        r = self._env.get_property(self._agent_id, "next_obstacle")
        return r.get("next_obstacle", ObstacleType.NONE.value)

class DistanceSensor(SimulatedSensor):
    def sense(self):
        r = self._env.get_property(self._agent_id, "distance")
        return r.get("distance", -1)

class ErrorSensor(SimulatedSensor):
    def sense(self):
        own = self._env.get_property(self._agent_id, "errors_self").get("errors_self", 0)
        opp = self._env.get_property(self._agent_id, "errors_opponent").get("errors_opponent", 0)
        return own, opp

class GameOverSensor(SimulatedSensor):
    def sense(self):
        r = self._env.get_property(self._agent_id, "game_over")
        return r.get("game_over", False)

class ActionActuator(SimulatedActuator):
    def act(self, action_name: str):
        self._env.take_action(self._agent_id, action_name)