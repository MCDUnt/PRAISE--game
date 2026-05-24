from statebuffer import IStateBuffer, StateBuffer
from vacuumworld import VacuumEnvironment
import Pyro4


class VacuumWorldPyroAdapter:
    def __init__(self, daemon, ns):
        self._vacuumenv = None
        self._daemon = daemon
        self._ns = ns
        self._buffers = {}

    @Pyro4.expose
    def build_env(self, length: int, dirty_locations: int):
        self._vacuumenv = VacuumEnvironment(length, random_dirt=False)
        self._vacuumenv.random_dirt(number_dirty_locations=dirty_locations)

    @Pyro4.expose
    def create_statebuffer(self, agent_id: int) -> str:
        if self._vacuumenv is None:
            raise RuntimeError("Environment not built yet")

        buffer = StateBuffer(agent_id, self._vacuumenv)
        buffer_adapter = StateBufferPyroAdapter(buffer)

        uri = self._daemon.register(buffer_adapter)
        name = f"statebuffer.agent_{agent_id}"
        self._ns.register(name, uri)

        self._vacuumenv.add_statebuffer(agent_id, buffer)

        self._buffers[agent_id] = buffer

        return name

    @Pyro4.expose
    def add(self, agent_id: int) -> None:
        if self._vacuumenv is not None:
            self._vacuumenv.add(agent_id)

    @Pyro4.expose
    def remove(self, agent_id: int) -> None:
        if self._vacuumenv is not None:
            self._vacuumenv.remove(agent_id)

    @Pyro4.expose
    def add_statebuffer(self, agent_id: int, statebuffer: IStateBuffer) -> None:
        if self._vacuumenv is not None:
            self._vacuumenv.add_statebuffer(agent_id, statebuffer)

    @Pyro4.expose
    def remove_statebuffer(self, agent_id: int, statebuffer_id: int) -> None:
        if self._vacuumenv is not None:
            self._vacuumenv.remove(agent_id, statebuffer_id)

    @Pyro4.expose
    def get_property(self, agent_id: int, property_name: str) -> dict:
        response = {}
        if self._vacuumenv is not None:
            response = self._vacuumenv.get_property(agent_id, property_name)
        return response

    @Pyro4.expose
    def take_action(self, agent_id: int, action_name: str, params: dict = {}) -> None:
        if self._vacuumenv is not None:
            self._vacuumenv.take_action(agent_id, action_name, params)


@Pyro4.expose
class StateBufferPyroAdapter:
    def __init__(self, buffer: StateBuffer):
        self._buffer = buffer

    def update(self, state):
        return self._buffer.update(state)

    def get_state(self):
        return self._buffer.get_state()


if __name__ == '__main__':
    daemon = Pyro4.Daemon(host="localhost")
    ns = Pyro4.locateNS()
    env_adapter = VacuumWorldPyroAdapter(daemon, ns)
    env_uri = daemon.register(env_adapter)
    ns.register("vacuumworld", env_uri)
    print(env_uri)
    daemon.requestLoop()