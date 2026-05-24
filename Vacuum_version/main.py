from renderers import NullRenderer
from statebuffer import StateBuffer
from vacuumrenderers import ConsoleRenderer, PyGameRenderer
from vacuumworld import VacuumEnvironment
from vacuumagent import VacuumAgent, MoveDirection
import threading

agent_finished_flag = False
event_render_ready = threading.Event()

def agent_thread(agent):
    global agent_finished_flag
    for _ in range(10):
        agent.print_state()
        event_render_ready.wait(timeout=0.1)
        agent.behave()
        event_render_ready.clear()
    agent_finished_flag = True

def render_thread(renderer):
    while not agent_finished_flag:
        renderer.render()
        event_render_ready.set()



if __name__ == '__main__':
    env = VacuumEnvironment(3, True)
    agent = VacuumAgent(env)
    renderer = ConsoleRenderer()

    statebuffer = StateBuffer(agent.id, env)
    renderer.observe(statebuffer=statebuffer)

    print(agent.id)

    thread_agent = threading.Thread(target=agent_thread, args=(agent,))
    thread_renderer = threading.Thread(target=render_thread, args=(renderer,))

    thread_renderer.start()
    thread_agent.start()

    thread_agent.join()
    thread_renderer.join()

    agent.print_state()