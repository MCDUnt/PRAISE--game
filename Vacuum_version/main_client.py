import threading
import Pyro4
from vacuumagent import VacuumAgent
from renderers import NullRenderer
from vacuumrenderers import ConsoleRenderer, PyGameRenderer

agent_finished_flag = False
event_sync_start = threading.Event()
event_render_ready = threading.Event()

def agent_thread(agent):
    global agent_finished_flag
    event_sync_start.wait(timeout=5)
    for _ in range(10):
        agent.print_state()
        event_render_ready.wait(timeout=0.1)
        agent.behave()
        event_render_ready.clear()
    agent_finished_flag = True

def render_thread(renderer):
    while not agent_finished_flag:
        renderer.render()
        event_sync_start.set()
        event_render_ready.set()


uri = "PYRONAME:vacuumworld"
vacuumenv = Pyro4.Proxy(uri)
vacuumenv.build_env(length=5, dirty_locations=3)

agent = VacuumAgent(vacuumenv)

statebuffer_name = vacuumenv.create_statebuffer(agent.id)
statebuffer = Pyro4.Proxy(f"PYRONAME:{statebuffer_name}")

renderer = ConsoleRenderer()
renderer.observe(statebuffer)
print(agent.id)

thread_agent = threading.Thread(target=agent_thread, args=(agent,))
thread_renderer = threading.Thread(target=render_thread, args=(renderer,))

thread_renderer.start()
thread_agent.start()

thread_agent.join()
thread_renderer.join()

agent.print_state()