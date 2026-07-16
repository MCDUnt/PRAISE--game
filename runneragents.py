import random
from agents import Agent
from environment import SimulatedSensor, SimulatedActuator, SimulatedEnvironment
from runnerworld import RunnerChaseEnvironment, Role, ObstacleType, CORRECT_ACTION, MISTAKE_RATE_INCREMENT, MISTAKE_RATE_MAX

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


#-------------------Actuador compartido-------------------
class RunnerActuator(SimulatedActuator):
    def act(self, action):
        self._env.take_action(self._agent_id, action_name)

class _BaseRunnerAgent(Agent):
    def __init__(self, env: SimulatedEnvironment, role: Role):
        super().__init__()
        env.register(self.id, role)

        for name, cls in [
            ("position", PositionSensor),
            ("next_obstacle", NextObstacleSensor),
            ("distance", DistanceSensor),
            ("errors", ErrorSensor),
            ("game_over", GameOverSensor)
        ]:
            s = cls(env)
            s.agent = self
            self.add_sensor(name, s)

        act = RunnerActuator(env)
        act.agent = self
        self.add_actuator("runner", act)

    def _pos(self): return self.sensors["position"].sense()
    def _obstacle(self): return self.sensors["next_obstacle"].sense()
    def _distance(self): return self.sensors["distance"].sense()
    def _errors(self): return self.sensors["errors"].sense()
    def _done(self): return self.sensors["game_over"].sense()

    def _perceive(self):
        return {
            "position": self._pos(),
            "next_obstacle": self._obstacle(),
            "distance": self._distance(),
            "errors": self._errors(),
            "game_over": self._done()
        }
    def _act(self, percept):
        action= self.function(percept)
        self.actuators["runner"].act(action)
    def behave(self):
        percept = self._perceive()
        self._act(percept)

#-------------------Agente IA-------------------
class CriminalAgent(_BaseRunnerAgent):
    def __init__(self, env: RunnerChaseEnvironment, base_mistake_rate: float = 0.15):
        super().__init__(env, Role.CRIMINAL)
        self._env_runner = env
        self.mistake_rate = max(0.0, min(1.0, base_mistake_rate))

        self._wrong_actions = {
            "run": ["jump", "slide"],
            "jump": ["run", "slide"],
            "slide": ["run", "jump"],
            "go_left": ["run", "go_right"],
            "go_right": ["run", "go_left"],
        }
    def function(self, percept):
        obstacle= ObstacleType(percept["next_obstacle"])
        correct = CORRECT_ACTION[obstacle]
        mistake_rate = self._env_runner.get_mistake_rate_for_tick(self.base_mistake_rate)

        if random.random() < self.mistake_rate:
            wrong_choices = self._wrong_actions.get(correct, ["run"])
            return random.choice(wrong_choices)
        return correct

    def print_state(self):
        pos = self._pos()
        obs = self._obstacle()
        dist = self._distance()
        own, opp = self._errors()
        rate = self._env_runner.get_mistake_rate_for_tick(self.base_mistake_rate)
        print(f"[CRIMINAL] pos={pos:>3} | obs={obs:<12}"
              f"dist={dist:>3} | err_propios={own} | err_jugador={opp} | mistake_rate={rate:.0%}")

#-------------------Agente Jugable-------------------
class PlayerAgent(_BaseRunnerAgent):
    def __init__(self, env: SimulatedEnvironment):
        super().__init__(env, Role.PLAYER)
        self._pending_action :str = "run"
    
    def set_action(self, action_name: str) -> None:
        valid = {"run", "jump", "slide", "go_left", "go_right"}
        if action_name in valid:
            self._pending_action = action_name
    
    def function(self, percept):
        action = self._pending_action
        self._pending_action = "run" # reset a acción neutral
        return action
    
    def print_state(self):
        pos = self._pos()
        obs = self._obstacle()
        dist = self._distance()
        own, opp = self._errors()
        print(f"[PLAYER]   pos={pos:>3} | obs={obs:<12}"
              f"dist={dist:>3} | err_propios={own} | err_criminal={opp})")



