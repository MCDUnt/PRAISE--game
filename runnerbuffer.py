"""
runnerbuffer.py — StateBuffer del juego Runner Chase
Solo guarda lo necesario para rendering. El entorno decide qué mandar.
"""

from statebuffer import IStateBuffer
from environments import SimulatedEnvironment


class RunnerStateBuffer(IStateBuffer):
    """
    Guarda el último snapshot del entorno para un agente específico.
    Compatible con el protocolo IStateBuffer de PRAISE.
    Solo almacena el estado de display (grid/distance/game_over/winner).
    """

    def __init__(self, agent_id: int, env: SimulatedEnvironment):
        super().__init__()
        env.add_statebuffer(agent_id, self)

    def update(self, state: dict) -> None:
        # state ya viene filtrado del entorno: solo lo visible
        self._state = state

    def get_state(self) -> dict | None:
        # Siempre devolver lo último — el renderer dibuja a 60 FPS
        # aunque el estado no haya cambiado (fix pantalla gris)
        return self._state
