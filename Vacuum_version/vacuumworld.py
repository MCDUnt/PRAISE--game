import random

from statebuffer import IStateBuffer
from environments import SimulatedEnvironment


class VacuumEnvironment(SimulatedEnvironment):
    def __new__(cls, length: int, random_dirt=False):
        if length <= 0:
            raise ValueError
        else:
            return super().__new__(cls)

    def __init__(self, length: int, random_dirt=False):
        super(VacuumEnvironment, self).__init__()
        self._length = length
        self._agents_locations = {}                     # maps agent id with its location
        self._dirt_locations = set()
        if random_dirt:
            self.random_dirt(length // 2)

    def add(self, agent_id: int) -> None:
        super(VacuumEnvironment, self).add(agent_id)
        self._agents_locations[agent_id] = 0

    def remove(self, agent_id: int) -> None:
        super(VacuumEnvironment, self).remove(agent_id)
        self._agents_locations.pop(agent_id, None)

    def add_statebuffer(self, agent_id: int, statebuffer: IStateBuffer) -> None:
        super(VacuumEnvironment, self).add_statebuffer(agent_id, statebuffer)
        statebuffer.update({"length": self._length, "agent_location": self._location_of(agent_id),
                         "dirt_location": self._dirt_locations})

    def remove_statebuffer(self, agent_id: int,statebuffer: IStateBuffer) -> None:
        super(VacuumEnvironment, self).remove_statebuffer(agent_id, statebuffer)

    def random_dirt(self, number_dirty_locations):
        self._dirt_locations = self._dirt_locations.union(set(random.sample(range(self._length),
                                                                            k=number_dirty_locations)))

    def _is_dirty_in_location(self, x: int) -> bool:
        return x in self._dirt_locations

    def _location_of(self, agent_id: int) -> int:
        return self._agents_locations[agent_id] if agent_id in self._agents_locations else None

    def get_property(self, agent_id: int, property_name: str) -> dict:
        if agent_id in self._agents:
            response = {"agent": agent_id}

            property_methods = {
                "location": self._location_of,
                "dirty": lambda agent_id: self._is_dirty_in_location(self._location_of(agent_id)),
            }

            property_method = property_methods.get(property_name)

            if property_method:
                response[property_name] = property_method(agent_id)
            else:
                print(f"Invalid property: {property_name}")

            return response
        else:
            return {}

    def _handle_move(self, agent_id: int, direction: str) -> None:
        if direction == "left":
            self._move_agent_left(agent_id)
        elif direction == "right":
            self._move_agent_right(agent_id)
        else:
            print(f"Invalid direction: {direction}")

    def _move_agent_left(self, agent_id: int):
        self._agents_locations[agent_id] = max(self._agents_locations[agent_id] - 1, 0)

    def _move_agent_right(self, agent_id: int):
        self._agents_locations[agent_id] = min(self._agents_locations[agent_id] + 1, self._length - 1)

    def _make_clean(self, agent_id: int):
        location = self._location_of(agent_id)
        self._dirt_locations.discard(location)

    def take_action(self, agent_id: int, action_name: str, params: dict = {}) -> None:
        if agent_id in self._agents:
            action_methods = {
                "move": (self._handle_move, ["direction"]),
                "clean": (self._make_clean, []),
            }

            action_method, expected_params = action_methods.get(action_name, (None, None))
            if action_method:
                args = [agent_id] + [params.get(param) for param in expected_params]
                action_method(*args)
                self._update_statebuffers(agent_id)
            else:
                print(f"Invalid action: {action_name}")

    def _update_statebuffers(self, agent_id: int):
        relevant_statebuffers = [entry["statebuffer"] for entry in self._statebuffers if entry["agent_id"] == agent_id]
        for statebuffer in relevant_statebuffers:
            statebuffer.update({"length": self._length, "agent_location": self._location_of(agent_id),
                             "dirt_location": self._dirt_locations})