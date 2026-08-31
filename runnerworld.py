"""
runnerworld.py — Entorno Runner Chase (toda la lógica vive acá)
Feedback profesor: obstáculos, posiciones, movimientos, ganar/perder,
aparición de cosas y avance de tiempo son responsabilidad del entorno.
"""

import random
import time
from enum import Enum, unique
from statebuffer import IStateBuffer
from environments import SimulatedEnvironment

# ---------------------------------------------------------------------------
# Constantes de juego
# ---------------------------------------------------------------------------
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

# Grilla consola 8 filas x 3 columnas (feedback 8x3)
GRID_ROWS = 8
GRID_COLS = 3
F_ROW = 6  # fila del fugitivo (1-indexed, fijo)
C_INIT_ROW = 4  # fila inicial captor
OBSTACLE_SPAWN_ROW = 8
ROWS_PER_SECOND = 2  # 2 filas/s = 0.5s por fila, loop 4s

@unique
class ObstacleType(Enum):
    NONE = "none"
    BLOCK = "block"          # saltar -> O abajo
    LOW_BAR = "low_bar"      # deslizar -> X X X
    LEDGE_LEFT = "ledge_left"   # pared izq+centro -> X X _
    LEDGE_RIGHT = "ledge_right" # pared der+centro -> _ X X

CORRECT_ACTIONS: dict[ObstacleType, str] = {
    ObstacleType.NONE: "run",
    ObstacleType.BLOCK: "jump",
    ObstacleType.LOW_BAR: "slide",
    ObstacleType.LEDGE_LEFT: "go_left",
    ObstacleType.LEDGE_RIGHT: "go_right",
}

# Mapeo visual X/O para la grilla (solo X y O)
OBSTACLE_PATTERNS: dict[ObstacleType, list[str]] = {
    ObstacleType.NONE:       [" ", " ", " "],
    ObstacleType.BLOCK:      [" ", "O", " "],
    ObstacleType.LOW_BAR:    ["X", "X", "X"],
    ObstacleType.LEDGE_LEFT: ["X", "X", " "],
    ObstacleType.LEDGE_RIGHT:[" ", "X", "X"],
}

@unique
class Role(Enum):
    CRIMINAL = "criminal"
    PLAYER = "player"

def _generate_track(length: int) -> list[ObstacleType]:
    pool = [ObstacleType.BLOCK, ObstacleType.LOW_BAR, ObstacleType.LEDGE_LEFT, ObstacleType.LEDGE_RIGHT]
    track = []
    for _ in range(length):
        if random.random() < OBSTACLE_DENSITY:
            track.append(random.choice(pool))
        else:
            track.append(ObstacleType.NONE)
    return track

class _AgentState:
    def __init__(self, position: int):
        self.position = position
        self.col = 1  # 0=izq,1=centro,2=der
        self.errors = 0
        self.last_action: str | None = None
        self.last_correct: bool = True

class RunnerChaseEnvironment(SimulatedEnvironment):
    def __init__(self):
        super().__init__()
        self._track: list[ObstacleType] = _generate_track(TRACK_LENGTH)
        self._role_map: dict[int, Role] = {}
        self._states: dict[int, _AgentState] = {}
        self._distance_between: int = INITIAL_DISTANCE
        self._game_over: bool = False
        self._winner: str | None = None
        self.tick: int = 0
        self._start_time: float = time.time()
        self._current_delay: float = SPEED_INITIAL_DELAY
        self._current_mistake_rate: float = 0.0
        # Obstáculo actual y su fila animada
        self._obstacle_index: int = 0
        self._obstacle_spawn_time: float = time.time()

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
        # Evitar duplicado de super().add_statebuffer que hace append doble
        self._statebuffers.append({"agent_id": agent_id, "statebuffer": statebuffer})
        # No llamar a super().add_statebuffer para no duplicar _agents
        statebuffer.update(self._build_state_snapshot(agent_id))

    def get_property(self, agent_id: int, property_name: str) -> dict:
        if agent_id not in self._agents:
            return {}
        state = self._states.get(agent_id)
        if state is None:
            return {"agent": agent_id}
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
            "col": lambda: state.col,
        }
        fn = props.get(property_name)
        if fn is None:
            print(f"[RunnerWorld] Propiedad invalida: {property_name}")
            return {"agent": agent_id}
        return {"agent": agent_id, property_name: fn()}

    def take_action(self, agent_id: int, action_name: str, params: dict = {}) -> None:
        if agent_id not in self._agents or self._game_over:
            # Igual notificar buffers para que vean game_over
            for entry in self._statebuffers:
                entry["statebuffer"].update(self._build_state_snapshot(entry["agent_id"]))
            return
        state = self._states.get(agent_id)
        if state is None:
            return
        obstacle = self._next_obstacle(state.position)
        correct = CORRECT_ACTIONS[obstacle]

        # Actualizar columna para movimientos laterales
        if action_name == "go_left":
            state.col = max(0, state.col - 1)
        elif action_name == "go_right":
            state.col = min(GRID_COLS - 1, state.col + 1)
        # jump/slide/run no cambian col, pero se evalúan igual

        if action_name == correct:
            state.position = min(state.position + 1, TRACK_LENGTH - 1)
            state.last_correct = True
            # Avanzar índice de obstáculo global si el player acertó
            # (sincroniza grilla visual con progreso)
            if self._states[agent_id].position > self._obstacle_index:
                self._obstacle_index = state.position
                self._obstacle_spawn_time = time.time()
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
        self.tick += 1
        self._update_difficulty()

    def _update_difficulty(self) -> None:
        if self.tick % SPEED_INTERVAL == 0:
            self._current_delay = max(self._current_delay - SPEED_INCREMENT, SPEED_MIN_DELAY)

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
            self._distance_between = 0
        elif self._distance_between >= MAX_DISTANCE:
            self._game_over = True
            self._winner = "criminal"

    # ------------------------------------------------------------------
    # Grilla 8x3 — toda la lógica visual vive acá (feedback profesor)
    # ------------------------------------------------------------------
    def _get_obstacle_row(self) -> int:
        """Fila actual del obstáculo (1..8) según tiempo. Avanza 2 filas/s."""
        elapsed = time.time() - self._obstacle_spawn_time
        row = OBSTACLE_SPAWN_ROW - int(elapsed * ROWS_PER_SECOND)
        if row < 1:
            # Obstáculo salió por abajo -> spawnear siguiente
            self._obstacle_index = min(self._obstacle_index + 1, TRACK_LENGTH - 1)
            self._obstacle_spawn_time = time.time()
            row = OBSTACLE_SPAWN_ROW
        return row

    def _c_row_from_distance(self) -> int:
        """Fila de C según distancia: F fijo en 6, C en 4 inicial, 7 gana C, 1 gana F"""
        import math
        # distance 5 -> fila 4, 0 -> 7, 12 -> 1  (2 filas/s, loop 4s)
        fila = 7 - math.ceil(self._distance_between * 0.5)
        return max(1, min(7, fila))

    def _build_grid(self) -> list[list[str]]:
        grid = [[" " for _ in range(GRID_COLS)] for _ in range(GRID_ROWS)]
        # Obstáculo actual (basado en índice del captor o índice global)
        # Usamos el próximo obstáculo del captor para la visual principal
        # Si no hay captor aún, usar _obstacle_index
        player_pos = None
        for aid, role in self._role_map.items():
            if role == Role.PLAYER and aid in self._states:
                player_pos = self._states[aid].position
                break
        idx = player_pos if player_pos is not None else self._obstacle_index
        obst_type = self._next_obstacle(idx)
        pattern = OBSTACLE_PATTERNS.get(obst_type, [" ", " ", " "])
        obs_row = self._get_obstacle_row()
        # Grid se imprime de arriba (índice 0 = fila 8) a abajo (índice 7 = fila 1)
        # Convertir fila 1..8 a índice 0..7 invertido
        r = GRID_ROWS - obs_row
        if 0 <= r < GRID_ROWS:
            for c in range(GRID_COLS):
                grid[r][c] = pattern[c]

        # F fijo en fila 6 -> índice 2
        f_col = 1
        for aid, role in self._role_map.items():
            if role == Role.CRIMINAL and aid in self._states:
                f_col = self._states[aid].col
                break
        grid[GRID_ROWS - F_ROW][f_col] = "F"

        # C dinámico por distancia (fila 1..7) -> índice invertido
        c_col = 1
        for aid, role in self._role_map.items():
            if role == Role.PLAYER and aid in self._states:
                c_col = self._states[aid].col
                break
        c_row = self._c_row_from_distance()
        grid[GRID_ROWS - c_row][c_col] = "C"

        return grid

    def _build_state_snapshot(self, agent_id: int) -> dict:
        state = self._states.get(agent_id)
        if state is None:
            return {"grid": self._build_grid(), "distance": self._distance(), "game_over": self._game_over, "winner": self._winner}
        # Snapshot mínimo para rendering (feedback: solo lo necesario)
        return {
            "grid": self._build_grid(),
            "distance": self._distance(),
            "game_over": self._game_over,
            "winner": self._winner,
            # Compatibilidad legacy para HUD (opcional)
            "role": self._role_map[agent_id].value,
            "position": state.position,
            "next_obstacle": self._next_obstacle(state.position).value,
            "errors_self": state.errors,
            "errors_opponent": self._opponent_errors(agent_id),
            "last_action": state.last_action,
            "last_correct": state.last_correct,
            "tick": self.tick,
            "mistake_rate": self._current_mistake_rate,
        }
