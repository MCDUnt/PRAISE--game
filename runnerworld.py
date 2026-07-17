import random
import time
from enum import Enum, unique
from statebuffer import IStateBuffer
from environments import SimulatedEnvironment

TRACK_LENGTH = 200
MAX_DISTANCE = 12
INITIAL_DISTANCE = 5
DISTANCE_PER_ERROR = 3
OBSTACLE_DENSITY = 0.30
SPEED_INTERVAL = 30
SPEED_INCREMENT = 0.05
SPEED_MIN_DELAY = 0.1
SPEED_INITIAL_DELAY = 0.05
MISTAKE_RATE_INTERVAL = 120
MISTAKE_RATE_INCREMENT = 0.05
MISTAKE_RATE_MAX = 0.60

@unique
class ObstacleType(Enum):
    NONE = "none"
    BLOCK = "block"
    LOW_BAR = "low_bar"
    LEDGE_LEFT = "ledge_left"
    LEDGE_RIGHT = "ledge_right"

CORRECT_ACTIONS: dict[ObstacleType, str] = {
    ObstacleType.NONE: "run",
    ObstacleType.BLOCK: "jump",
    ObstacleType.LOW_BAR: "slide",
    ObstacleType.LEDGE_LEFT: "go_left",
    ObstacleType.LEDGE_RIGHT: "go_right",
}

@unique
class Role(Enum):
    CRIMINAL = "criminal"
    PLAYER = "player"

def _generate_track(length: int) -> list[ObstacleType]:
    obstacle_pool = [
        ObstacleType.BLOCK,
        ObstacleType.LOW_BAR,
        ObstacleType.LEDGE_LEFT,
        ObstacleType.LEDGE_RIGHT,
    ]
    track = []
    for _ in range(length):
        if random.random() < OBSTACLE_DENSITY:
            track.append(random.choice(obstacle_pool))
        else:
            track.append(ObstacleType.NONE)
    return track

class _AgentState:
    def __init__(self, position: int):
        self.position = position  #casilla actual en la pista
        self.errors = 0
        self.alive = True
        self.last_action: str | None = None
        self.last_correct: bool = True

class RunnerChaseEnvironment(SimulatedEnvironment):
    def __init__(self):
        super().__init__()
        self._track : list[ObstacleType] = _generate_track(TRACK_LENGTH)
        self._role_map: dict[int, Role] = {}
        self._states: dict[int, _AgentState] = {}
        self._distance_between: int = INITIAL_DISTANCE
        self._game_over: bool = False
        self._winner: str | None = None

        self.tick: int = 0
        self._start_time: float = time.time()
        self._current_delay: float = SPEED_INITIAL_DELAY
        self._current_mistake_rate: float = 0.0

    def register(self, agent_id: int, role: Role) -> None:
        self._role_map[agent_id] = role
        if role == Role.CRIMINAL:
            self._states[agent_id] = _AgentState(position=INITIAL_DISTANCE)
        else:
            self._states[agent_id] = _AgentState(position=0)
        self.add(agent_id)

    def add(self, agent_id: int) -> None:
        super().add(agent_id)

    def remove(self, agent_id: int) -> None:
        super().remove(agent_id)
        self._states.pop(agent_id, None)
        self._role_map.pop(agent_id, None)

    def add_statebuffer(self, agent_id: int, statebuffer: IStateBuffer) -> None:
        super().add_statebuffer(agent_id, statebuffer)
        statebuffer.update(self._build_state_snapshot(agent_id))

    def get_property(self, agent_id: int, property_name: str) -> dict:
        if agent_id not in self._agents:
            return {}

        state = self._states[agent_id]
        props = {
            "position": lambda: state.position,
            "next_obstacle": lambda: self._next_obstacle(state.position).value,
            "distance": lambda: self._distance(),
            "errors_self": lambda: state.errors,
            "errors_opponent": lambda: self._opponent_errors(agent_id),
            "game_over": lambda: self._game_over,
            "winner": lambda: self._winner,
            "role": lambda: self._role_map[agent_id].value,
            "current_delay": lambda: self._current_delay,
            "mistake_rate": lambda: self._current_mistake_rate,
        }

        fn = props.get(property_name)
        if fn is None:
            print(f"[RunnerWorld] Propiedad invalida: {property_name}")
            return {"agent": agent_id}
        return {"agent": agent_id, property_name: fn()}

    def take_action(self, agent_id: int, action_name: str, params: dict = {}) -> None:
        if agent_id not in self._agents or self._game_over:
            return
        state =self._states.get(agent_id)
        obstacle = self._next_obstacle(state.position)
        correct = CORRECT_ACTIONS[obstacle]

        if action_name == correct:
            state.position = min(state.position + 1, TRACK_LENGTH - 1)
            state.last_correct = True
        else:
            state.errors += 1
            state.last_correct = False
            role = self._role_map[agent_id]
            if role == Role.PLAYER:
                self._distance_between += DISTANCE_PER_ERROR
            else:
                self._distance_between -= DISTANCE_PER_ERROR
        state.last_action = action_name
        self._check_game_over()

        for entry in self._statebuffers:
            entry["statebuffer"].update(self._build_state_snapshot(entry["agent_id"]))


    def _update_difficulty(self) -> None:
        if self.tick % SPEED_INTERVAL == 0:
            self._current_delay = max(self._current_delay - SPEED_DELAY_DECREMENT, SPEED_MIN_DELAY)

    def get_mistake_rate_for_tick(self, base_rate: float) -> float:
        elapsed = time.time() - self._start_time
        intervals = int(elapsed // MISTAKE_RATE_INTERVAL)
        rate = base_rate + intervals * MISTAKE_RATE_INCREMENT
        rate = min(rate, MISTAKE_RATE_MAX)
        self._current_mistake_rate = rate
        return rate
        
    def _next_obstacle(self, position: int) -> ObstacleType:
        if position < len(self._track):
            return self._track[position]
        return ObstacleType.NONE

    def _distance(self) -> int:
        return self._distance_between

    def _criminal_position(self) -> int | None  :
        for aid, role in self._role_map.items():
            if role == Role.CRIMINAL:
                return self._states[aid].position
        return None

    def _player_position(self) -> int | None:
        for aid, role in self._role_map.items():
            if role == Role.PLAYER:
                return self._states[aid].position
        return None 

    def _opponent_errors(self, agent_id: int) -> int:
        my_role = self._role_map.get(agent_id)
        for aid, role in self._role_map.items():
            if role != my_role:
                return self._states[aid].errors
        return 0

    def _check_game_over(self) -> None:
        if self._distance_between <= 0:
            self._game_over = True
            self._winner = "player"
            self._distance_between = 0 # para que no quede > 0
        elif self._distance_between >= MAX_DISTANCE:
            self._game_over = True
            self._winner = "criminal"

    def _build_state_snapshot(self, agent_id: int) -> dict:
        state = self._states.get(agent_id)
        if state is None:
            return {}
        return {
            "agent": agent_id,
            "role": self._role_map[agent_id].value,
            "position": state.position,
            "next_obstacle": self._next_obstacle(state.position).value,
            "errors_self": state.errors,
            "errors_opponent": self._opponent_errors(agent_id),
            "distance": self._distance(),
            "last_action": state.last_action,
            "last_correct": state.last_correct,
            "game_over": self._game_over,
            "winner": self._winner,
            "upcoming_track": [
                self._track[i].value
                for i in range(state.position, min(state.position + 5, len(self._track)))
            ]
        }