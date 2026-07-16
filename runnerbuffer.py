"""
runnerbuffer.py — StateBuffer del juego Runner Chase

Mantiene el snapshot más reciente del estado del entorno
para que el renderer lo consuma sin bloquear al agente.
"""

from statebuffer import IStateBuffer
from environments import SimulatedEnvironment


class RunnerStateBuffer(IStateBuffer):
    """
    Guarda el último snapshot del entorno para un agente específico.
    Compatible con el protocolo IStateBuffer de PRAISE.
    """

    def __init__(self, agent_id: int, env: SimulatedEnvironment):
        super().__init__()
        env.add_statebuffer(agent_id, self)

    def update(self, state: dict) -> None:
        self._state  = state
        self.changed = True

    def get_state(self) -> dict | None:
        if self.changed:
            self.changed = False
            return self._state
        return None